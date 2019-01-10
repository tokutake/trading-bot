import json
import bitflyer_websocket
import datetime
import time
import numpy as np
import traceback
import arrow

symbol = 'FX_BTC_JPY'
bf = bitflyer_websocket.BitflyerWebsocket()

lot = 0.01
target_spread = 50
max_special_order = 1
print('lot:', lot)
print('target_spread:', target_spread)
print('max_special_order:', max_special_order)

def now():
    return datetime.datetime.now()

def elapsed_time(prev):
    return (arrow.utcnow() - prev).seconds

print(datetime.datetime.now())

def adjust_target_price(target_price):
    # When using lightning UI, left click on chart price is multiple of 50
    # so, there is a lot of limit order at price of multiple of 50
    # it is hard to cross wall, place order price inside of wall
    pass

def send_buy_ifdoco(target_price):
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
        if elapsed_time(open_date) < 20:
            continue
        price = position['price']
        side = position['side']
        if side == 'BUY' and price < best_bid - target_spread * 2:
            exit_position(side, position['size'])
        if side == 'SELL' and price > best_ask + target_spread * 2:
            exit_position(side, position['size'])

def cancel_missed_order():
    best_bid = bf.get_best_bid()
    best_ask = bf.get_best_ask()
    for parent_order in parent_orders:
        state = parent_order['parent_order_state']
        if state != 'ACTIVE':
            continue

        parent_order_date = parent_order['parent_order_date']
        order_date = arrow.get(parent_order_date)
        target_price = parent_order['price']

        # cancel order if it is difficult to fufill
        if parent_order['executed_size'] == 0:
            if best_bid > target_price + target_spread and elapsed_time(order_date) > 10:
                print('cancel order at ', parent_order['price'])
                bf.cancel_parent_order(parent_order)

        # if missed stop lost order, cancel parent special order
        if parent_order['executed_size'] > 0:
            if best_ask < target_price - target_spread * 2 and elapsed_time(order_date) > 20:
                print('cancel order at ', parent_order['price'])
                bf.cancel_parent_order(parent_order)

print(datetime.datetime.now())
while True:
    try:
        parent_orders = bf.get_active_parent_orders()
        if len(parent_orders) < max_special_order:
            print('collateral:', bf.getcollateral());
            # TODO: adjust target price not to cross 50 wall
            target_price = bf.get_best_bid_with_depth(0.1)
            send_buy_ifdoco(target_price)

        time.sleep(1)

        cancel_missed_order()
        time.sleep(1)
        exit_unnecessary_position()

    except Exception:
        print(traceback.format_exc())
        time.sleep(3)

