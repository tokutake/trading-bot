import json
import bitflyer_websocket
import datetime
import time
import numpy as np
import traceback
import arrow
import threading
import scheduler

symbol = 'FX_BTC_JPY'
bf = bitflyer_websocket.BitflyerWebsocket()

lot = 0.01
target_spread = 50
max_special_order = 1
max_simaltanious_order = 1
print('lot:', lot)
print('target_spread:', target_spread)
print('max_special_order:', max_special_order)

def now():
    return datetime.datetime.now()

def elapsed_time(prev):
    return (arrow.utcnow() - prev).seconds

print(datetime.datetime.now())

def short(target_price):
    price = round(target_price)
    order = bf.send_parent_order({
      "order_method": "IFDOCO",
      "minute_to_expire": 1,
      "time_in_force": "GTC",
      "parameters": [{
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "SELL",
        "price": price,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "BUY",
        "price": price - target_spread - 1,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "STOP_LIMIT",
        "side": "BUY",
        "price": price + target_spread,
        "trigger_price": price + target_spread,
        "size": lot
      }]
    })
    print(order)
    return order

def long(target_price):
    price = round(target_price)
    order = bf.send_parent_order({
      "order_method": "IFDOCO",
      "time_in_force": "GTC",
      "parameters": [{
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "BUY",
        "price": price,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "SELL",
        "price": price + target_spread + 1,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "STOP_LIMIT",
        "side": "SELL",
        "price": price - target_spread,
        "trigger_price": price - round(1.0 * target_spread),
        "size": lot
      }]
    })
    print(order)
    return order

parent_orders = []
def exit_position(side, size):
    print('exit {} position, size:{}'.format(side, size))
    opposite = None
    if side == 'BUY':
        opposite = 'SELL'
    else:
        opposite = 'BUY'

    if size < 0.01:
        bf.create_market_order(opposite, size + 0.01)
        bf.create_market_order(side, 0.01)
    else:
        bf.create_market_order(opposite, size)

def opposite(side):
    if side == 'BUY':
        return 'SELL'
    else:
        return 'BUY'

def exit_unnecessary_position():
    positions = bf.getpositions()
    total_size = 0
    side = None
    for position in bf.getpositions():
        side = position['side']
        total_size += position['size']
    total_executed_size = 0
    orders = bf.get_active_parent_orders()
    for order in orders:
        total_executed_size += order['executed_size']

    if total_size > total_executed_size:
        exit_position(side, total_size - total_executed_size)

def close_all_positions():
    positions = bf.getpositions()
    best_ask = bf.get_best_ask()
    best_bid = bf.get_best_bid()
    for position in positions:
        price = position['price']
        side = position['side']
        if side == 'BUY':
            exit_position(side, position['size'])
        if side == 'SELL':
            exit_position(side, position['size'])

def cancel_parent_order(order):
    print('cancel order')
    bf.cancel_parent_order(order)

def cancel_missed_order():
    canceled = False
    for parent_order in get_active_parent_orders():
        parent_order_date = parent_order['parent_order_date']
        order_date = arrow.get(parent_order_date)

        # cancel order if it is difficult to fufill
        if parent_order['executed_size'] == 0:
            if elapsed_time(order_date) > 2:
                cancel_parent_order(parent_order)
                canceled = True
    if canceled:
        time.sleep(1)

print(datetime.datetime.now())
requested_parent_orders = []
def remove_inactive_requested_parent_orders():
    inactive_request_orders = []
    for requested_order in requested_parent_orders:
        for parent_order in parent_orders:
            # import pdb; pdb.set_trace()
            if parent_order['parent_order_acceptance_id'] == requested_order['parent_order_acceptance_id'] and parent_order['parent_order_state'] != 'ACTIVE':
                   inactive_request_orders.append(requested_order)

    for inactive_request_order in inactive_request_orders:
        requested_parent_orders.remove(inactive_request_order)

def get_active_parent_orders():
    active_parent_orders = []
    for order in parent_orders:
        if order['parent_order_state'] == 'ACTIVE':
            active_parent_orders.append(order)
    return active_parent_orders

def open():
    volatility = bf.get_volatility()
    if volatility > target_spread * 2:
        return
    if len(requested_parent_orders) < max_special_order:
        mid_price = bf.get_mean()
        order = None
        sma = bf.sma()
        print('volatility:', volatility)
        for i in range(1):
            if mid_price > sma:
                order = long(mid_price)
                print('long')
            else:
                order = short(mid_price)
                print('short')
        requested_parent_orders.append(order)

def print_stat():
    print(arrow.utcnow())
    for position in bf.getpositions():
        # print("position side:{}, price:{}, size:{}, open_date:{}".format(position['side'], position['price'], position['size'], position['open_date']))
        print(position)
    for order in bf.get_active_parent_orders():
        # print("order price:{}, executed_size:{}".format(order['price'], order['executed_size']))
        print(order)
    print('volatility:', bf.get_volatility())
    print('pl:', bf.get_pl())
    threading.Timer(30, print_stat).start()

print_stat()
time.sleep(5)

gc_scheduler = scheduler.Scheduler(exit_unnecessary_position, 5)

while True:
    try:
        parent_orders = bf.get_parent_orders()
        remove_inactive_requested_parent_orders()

        open()

        time.sleep(0.3)

        cancel_missed_order()

    except Exception:
        print(traceback.format_exc())
#        close_all_positions()
        time.sleep(10)

