import json
import bitflyer_websocket
import datetime
import time
import numpy as np
import traceback
import arrow
from pymongo import MongoClient

client = MongoClient()
db = client.test_database

symbol = 'FX_BTC_JPY'
bf = bitflyer_websocket.BitflyerWebsocket()

lot = 0.01
target_spread = 50
max_special_order = 3
print('lot:', lot)
print('target_spread:', target_spread)
print('max_special_order:', max_special_order)

def now():
    return datetime.datetime.now()

def elapsed_time(prev):
    return (arrow.utcnow() - prev).seconds

print(datetime.datetime.now())

def short(target_price):
    order = bf.send_parent_order({
      "order_method": "IFDOCO",
      "minute_to_expire": 5,
      "time_in_force": "GTC",
      "parameters": [{
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "SELL",
        "price": target_price,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "BUY",
        "price": target_price - target_spread - 1,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "STOP_LIMIT",
        "side": "BUY",
        "price": target_price + target_spread,
        "trigger_price": target_price + target_spread,
        "size": lot
      }]
    })
    print(order)
    return order

def long(target_price):
    order = bf.send_parent_order({
      "order_method": "IFDOCO",
      "minute_to_expire": 5,
      "time_in_force": "GTC",
      "parameters": [{
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "BUY",
        "price": target_price,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "LIMIT",
        "side": "SELL",
        "price": target_price + target_spread + 1,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "STOP_LIMIT",
        "side": "SELL",
        "price": target_price - target_spread,
        "trigger_price": target_price - round(1.0 * target_spread),
        "size": lot
      }]
    })
    print(order)
    return order

while True:
    if bf.get_best_bid():
        break
    time.sleep(1)

parent_orders = []
def exit_position(side, size):
    print('exit {} position, size:{}'.format(side, size))
    # import pdb; pdb.set_trace()
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

def exit_unnecessary_position():
    positions = bf.getpositions()
    best_ask = bf.get_best_ask()
    best_bid = bf.get_best_bid()
    for position in positions:
        open_date = arrow.get(position['open_date'])
        if elapsed_time(open_date) < 1:
            continue
        price = position['price']
        side = position['side']
        if side == 'BUY' and best_bid < price - target_spread * 2.5:
            exit_position(side, position['size'])
        if side == 'SELL' and best_ask > price + target_spread * 2.5:
            exit_position(side, position['size'])

def cancel_missed_order():
    best_bid = bf.get_best_bid()
    best_ask = bf.get_best_ask()
    for parent_order in get_active_parent_orders():
        state = parent_order['parent_order_state']
        if state != 'ACTIVE':
            continue

        parent_order_date = parent_order['parent_order_date']
        order_date = arrow.get(parent_order_date)
        target_price = parent_order['price']

        # cancel order if it is difficult to fufill
        if parent_order['executed_size'] == 0:
            if elapsed_time(order_date) > 10:
                if best_bid > target_price + target_spread:
                    print('cancel order')
                    bf.cancel_parent_order(parent_order)
                if best_ask < target_price - target_spread:
                    print('cancel order')
                    bf.cancel_parent_order(parent_order)

        # if missed stop lost order, cancel parent special order
        if parent_order['executed_size'] > 0:
            if elapsed_time(order_date) > 20:
                if best_ask < target_price - target_spread * 2:
                    print('cancel order')
                    bf.cancel_parent_order(parent_order)
                if best_bid > target_price + target_spread * 2:
                    print('cancel order')
                    bf.cancel_parent_order(parent_order)

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

ticks = []
def sma(n = 5):
    total = 0
    min_n = min(n, len(ticks))
    for i in range(min_n):
        total += ticks[-i]
    return total / min_n

ticks_unit = 60
last_tick_time = arrow.utcnow()
def get_last_tick_time():
    return last_tick_time

def set_last_tick_time(time):
    last_tick_time = time

def get_mean():
    return (bf.get_best_ask() + bf.get_best_bid()) / 2

def add_tick():
    # import pdb; pdb.set_trace()
    mean = get_mean()
    ticks_len = len(ticks)
    if len(ticks) == 0:
        ticks.append(mean)
    elif elapsed_time(get_last_tick_time()) >= 1:
        ticks.append(mean)
    if len(ticks) > ticks_len:
        set_last_tick_time(arrow.utcnow())

def open():
    if len(requested_parent_orders) < max_special_order:
        target_price = bf.get_best_bid_with_depth(0.1)
        mean = get_mean()
        print("mean:{}, sma:{}".format(mean, sma()))
        order = None
        if mean > sma():
            print('long')
            order = long(target_price)
        else:
            print('short')
            order = short(target_price)
        requested_parent_orders.append(order)

while True:
    try:
        add_tick()

        parent_orders = bf.get_parent_orders()
        remove_inactive_requested_parent_orders()

        open()

        time.sleep(0.3)

        cancel_missed_order()
        time.sleep(0.3)
        exit_unnecessary_position()

    except Exception:
        print(traceback.format_exc())
        time.sleep(3)

