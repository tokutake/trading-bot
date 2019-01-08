import json
import ccxt
import datetime
import time
import numpy as np

symbol = 'FX_BTC_JPY'

lot = 0.01

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

def get_target_price():
    orderBook = bf.fetchOrderBook(symbol)
    bids = orderBook['bids']
    bids.sort(reverse = True)
    depth = 1
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
      "minute_to_expire": 1,
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
        "price": target_price + 51,
        "size": lot
      },
      {
        "product_code": symbol,
        "condition_type": "STOP_LIMIT",
        "side": "SELL",
        "price": target_price - 50,
        "trigger_price": target_price - 50,
        "size": lot
      }]
    })

def get_order_status(order):
    orders = bf.request('getparentorders', 'private', params = {'product_code': 'FX_BTC_JPY'})
    for order in orders:
        if request_order['parent_order_acceptance_id'] == order['parent_order_acceptance_id']:
            return order['parent_order_state']
    return None

for i in range(10):
    print(datetime.datetime.now())
    request_order = send_ifdoco(get_target_price())
    print(request_order)
    request_sent_time = now()

    is_active = False
    prev_status = None
    while True:
        status = get_order_status(request_order)
        if prev_status != status:
            print(status)
        if status == 'COMPLETED' or status == 'CANCELED' or status == 'EXPIRED':
            break
        if prev_status != 'ACTIVE' and status == 'ACTIVE':
            print('time untile active:', elapsed_time(request_sent_time))
        if status == 'ACTIVE':
            is_active = True
        if is_active:
            time.sleep(2)
        prev_status = status 

    print(bf.request('getcollateral', 'private'))
    # import pdb; pdb.set_trace()
