import json
import ccxt
import datetime
import time
import numpy as np

symbol = 'FX_BTC_JPY'

lot = 0.01
target_spread = 1 / lot / 2
print('lot:', lot)
print('target_spread:', target_spread)

def now():
    return datetime.datetime.now()

def elapsed_time(prev):
    return np.timedelta64(now() - prev, 'ms') / np.timedelta64(1, 'ms')

key_json = json.load(open('key.json'))
bf = ccxt.bitflyer({
    'apiKey': key_json['bitflyer']['api_key'],
    'secret': key_json['bitflyer']['api_secret']
})

bf.load_markets()

def getcollateral():
    return bf.request('getcollateral', 'private')['collateral']

def get_best_bid():
    orderBook = bf.fetchOrderBook(symbol)
    bids = orderBook['bids']
    bids.sort(reverse = True)
    return bids[0][0]

def get_target_price():
    orderBook = bf.fetchOrderBook(symbol)
    bids = orderBook['bids']
    bids.sort(reverse = True)
    depth = 0.1
    target_price = None
    total_size = 0
    for bid in bids:
        price, size = bid
        total_size += size
        if target_price == None:
            target_price = price
        if total_size >= depth:
            break
        target_price = price
    return target_price

print(datetime.datetime.now())
def send_ifdoco(target_price):
    return bf.request("sendparentorder", "private", "POST", {
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

def get_parent_order(order):
    orders = bf.request('getparentorders', 'private', params = {'product_code': 'FX_BTC_JPY'})
    for order in orders:
        if request_order['parent_order_acceptance_id'] == order['parent_order_acceptance_id']:
            return order
    return None

def get_child_order_since(time):
    child_orders = bf.request('getchildorders', 'private', params = {'product_code': 'FX_BTC_JPY'})

def cancel_parent_order(order):
    return bf.request('cancelparentorder', 'private', 'POST', params = {'product_code': 'FX_BTC_JPY', 'parent_order_id': order['parent_order_id']})

win = 0
lose = 0
draw = 0
pl = 0
for i in range(20):
    print(datetime.datetime.now())
    target_price = get_target_price()
    request_order = send_ifdoco(target_price)
    print(request_order)
    request_sent_time = now()

    is_active = False
    prev_state = None
    state = None
    parent_order = None
    while True:
        parent_order = get_parent_order(request_order)
        if parent_order:
            state = parent_order['parent_order_state']

        # cancel order if it is difficult to fufill
        if state == 'ACTIVE' and parent_order['executed_size'] == 0:
            best_bid = get_best_bid()
            print('best_bid:{}, target_price:{}, target_spread:{}, elapsed_time:{}'.format(best_bid, target_price, target_spread, elapsed_time(request_sent_time)))
            if best_bid > target_price + target_spread and elapsed_time(request_sent_time) > 10 * 1000:
                cancel_parent_order(parent_order)

        if prev_state != state:
            print(state)
        if state == 'COMPLETED' or state == 'CANCELED' or state == 'EXPIRED':
            break
        if prev_state != 'ACTIVE' and state == 'ACTIVE':
            print('time untile active:', elapsed_time(request_sent_time))
        if state == 'ACTIVE':
            is_active = True
        if is_active:
            time.sleep(2)
        prev_state = state 

    child_order = bf.request('getchildorders', 'private', params = {'product_code': 'FX_BTC_JPY', 'count': '1'})[0]
    print(child_order)
    if state != 'COMPLETED' or target_price == child_order['price']:
        draw += 1
    elif target_price < child_order['price']:
        win += 1
        pl += child_order['price'] - target_price
    else:
        lose += 1
        pl += child_order['price'] - target_price

    print('collateral:', getcollateral());
    print('win:{}, lose:{}, draw:{}, pl:{}'.format(win, lose, draw, pl))
    # import pdb; pdb.set_trace()

