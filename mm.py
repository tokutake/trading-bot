import json
import bitflyer_websocket
import datetime
import time
import numpy as np
import traceback
import arrow
from pymongo import MongoClient
import redis

r = redis.Redis(decode_responses=True)

bf = bitflyer_websocket.BitflyerWebsocket()

lot = 0.01
target_spread = 50
max_order = 2
print('lot:', lot)
print('target_spread:', target_spread)
print('max_order:', max_order)

def now():
    return datetime.datetime.now()

def elapsed_time(prev):
    return (arrow.utcnow() - prev).seconds

print(datetime.datetime.now())

def short(target_price, size):
    order = bf.send_limit_order('SELL', size, target_price)
    print('short', target_price)
    return order

def long(target_price, size):
    order = bf.send_limit_order('BUY', size, target_price)
    print('long:', target_price)
    return order

while True:
    if bf.get_best_bid():
        break
    time.sleep(1)

def exit_position(price, side, size):
    print('exit {} position, size:{}, price:{}'.format(side, size, price))
    opposite = None
    if side == 'BUY':
        opposite = 'SELL'
    else:
        opposite = 'BUY'

    if size < 0.01:
        order = bf.create_market_order(opposite, size + 0.01)
        order = bf.create_market_order(side, 0.01)
    else:
        order = bf.create_market_order(opposite, size)

def exit_unnecessary_position():
    positions = bf.getpositions()
    best_ask = bf.get_best_ask()
    best_bid = bf.get_best_bid()
    for position in positions:
        open_date = arrow.get(position['open_date'])
        if elapsed_time(open_date) < 30:
            continue
        price = position['price']
        side = position['side']
        if side == 'BUY' and best_bid < price - target_spread * 2.5:
            exit_position(best_bid, side, position['size'])
        if side == 'SELL' and best_ask > price + target_spread * 2.5:
            exit_position(best_ask, side, position['size'])

def adjust_missed_order_price():
    best_bid = bf.get_best_bid()
    best_ask = bf.get_best_ask()
    orders = bf.get_child_orders().values()
    order_to_be_canceled = None
    for order in orders:
        if order['order_type'] == 'MARKET':
            continue

        order_date = order['child_order_date']
        target_price = order['price']

        if elapsed_time(order_date) < 10:
            continue

        if best_bid > target_price + target_spread * 2:
            order_to_be_canceled = order
        if best_ask < target_price - target_spread * 2:
            order_to_be_canceled = order

    if order_to_be_canceled:
        print('cancel order:{}, size:{}'.format(order_to_be_canceled['side'], order_to_be_canceled['size']))
        bf.cancel_child_order(order_to_be_canceled)
        size = order_to_be_canceled['size']
        price = order_to_be_canceled['price']
        if order_to_be_canceled['side'] == 'BUY':
            order = bf.send_limit_order('BUY', size, price + target_spread)
            print('send order:', 'BUY', size, price + target_spread)
        if order_to_be_canceled['side'] == 'SELL':
            order = bf.send_limit_order('SELL', size, price - target_spread)
            print('send order:', 'SELL', size, price - target_spread)

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
    mean = get_mean()
    ticks_len = len(ticks)
    if len(ticks) == 0:
        ticks.append(mean)
    elif elapsed_time(get_last_tick_time()) >= 1:
        ticks.append(mean)
    if len(ticks) > ticks_len:
        set_last_tick_time(arrow.utcnow())

def open():
    max_number = max_order
    if r.get('max_orders'):
        max_number = r.get('max_number')
    print()
    print_orders()
    print_position()
    print()
    if len(bf.orders) < max_number and total_position_size() < lot:
        target_price = bf.get_best_bid_with_depth(0.1)
        mean = get_mean()
        size = lot
        if r.get('lot'):
            size = lot
        long(round(mean) - 25, size)
        short(round(mean) + 26, size)

pls = []
raw_pls = []
def print_pl(order, position):
    size = 0
    if position['size'] - order['size'] < 0:
        size = position['size']
    else:
        size = order['size']
    if position['side'] == 'BUY':
        raw_pl = (order['price'] - position['price']) * size
    else:
        raw_pl = (position['price'] - order['price']) * size
    pl = round(raw_pl)
    pls.append(pl)
    raw_pls.append(raw_pl)
    print('pl:{}, raw_pl:{}, total_pl:{}, total_raw_pl:{}'.format(pl, raw_pl, sum(pls), sum(raw_pls)))

positions = []
def add_position(order):
    order['matched_size'] = 0
    sorted(positions, key=lambda position: position['open_date'])
    order['original_size'] = order['size']
    zero_size_positions = []
    for position in positions:
        if position['side'] != order['side'] and abs(order['size']) > 1e-5 and abs(position['size']) > 1e-5:
            print_pl(order, position)
            diff = position['size'] - order['size']
            if diff < 0:
                order['size'] -= position['size']
                position['size'] -= 0
            else:
                position['size'] -= order['size']
                order['size'] = 0
            if position['size'] < 1e-5:
                zero_size_positions.append(position)

    for position in zero_size_positions:
        positions.remove(position)

    if order['size'] > 1e-5:
        order['open_date'] = arrow.utcnow()
        positions.append(order)

def total_position_size():
    total = 0
    for position in positions:
        total += position['size']
    return total

def remove_executed_order():
    while not bf.execution_queue.empty():
        execution = bf.execution_queue.get()
        zero_size_order = None
        for id, order in bf.orders.items():
            matched = False
            if order['side'].upper() == 'BUY' and order['id'] == execution['buy_child_order_acceptance_id']:
                matched = True
            if order['side'].upper() == 'SELL' and order['id'] == execution['sell_child_order_acceptance_id']:
                matched = True
            if matched:
                order['executed_size']  += execution['size']
                print('matched order:id:{}, executed_size:{}, execution size:{}'.format(order['id'], order['executed_size'], execution['size']))
                if abs(order['size'] - order['executed_size']) <= 1e-6:
                    zero_size_order = order
        if zero_size_order:
            del bf.orders[zero_size_order['id']]
            if zero_size_order['order_type'] == 'MARKET':
                zero_size_order['price'] = execution['price']
            add_position(zero_size_order)

def print_orders():
    for key, order in bf.orders.items():
        price = None
        if order.get('price'):
            price = order['price']
        print('order side:{}, price:{}'.format(order['side'], price))

def print_position():
    for position in positions:
        print('position side:{}, price:{}'.format(position['side'], position['price']))

last_clean_up_at = None
while True:
    try:
        add_tick()

        open()

        if last_clean_up_at == None or elapsed_time(last_clean_up_at) > 1:
            adjust_missed_order_price()

            # exit_unnecessary_position()

            last_clean_up_at = arrow.utcnow()

        remove_executed_order()

        time.sleep(3)

    except Exception:
        print(traceback.format_exc())
        import pdb; pdb.set_trace()
        time.sleep(3)

