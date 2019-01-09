import json
import bitflyer_websocket
import datetime
import time
import numpy as np

symbol = 'FX_BTC_JPY'
bf = bitflyer_websocket.BitflyerWebsocket()

lot = 0.01
target_spread = 50
print('lot:', lot)
print('target_spread:', target_spread)

def now():
    return datetime.datetime.now()

def elapsed_time(prev):
    return np.timedelta64(now() - prev, 'ms') / np.timedelta64(1, 'ms')

print(datetime.datetime.now())

def send_buy_ifdoco(target_price):
    return bf.send_parent_order({
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

while True:
    if bf.get_best_bid():
        break
    time.sleep(1)

win = 0
lose = 0
draw = 0
pl = 0
for i in range(20):
    print(datetime.datetime.now())
    target_price = bf.get_best_bid_with_depth(0.1)
    request_order = send_buy_ifdoco(target_price)
    request_sent_time = now()

    is_active = False
    prev_state = None
    state = None
    parent_order = None
    while True:
        parent_order = bf.get_parent_order(request_order)
        if parent_order:
            state = parent_order['parent_order_state']

        # cancel order if it is difficult to fufill
        if state == 'ACTIVE' and parent_order['executed_size'] == 0:
            best_bid = bf.get_best_bid()
            if best_bid > target_price + target_spread and elapsed_time(request_sent_time) > 10 * 1000:
                bf.cancel_parent_order(parent_order)

        if prev_state != state:
            print(state)
        if state == 'COMPLETED' or state == 'CANCELED' or state == 'EXPIRED' or state == 'REJECTED':
            break
        if prev_state != 'ACTIVE' and state == 'ACTIVE':
            print('time untile active:', elapsed_time(request_sent_time))
        if state == 'ACTIVE':
            is_active = True
        if is_active:
            time.sleep(2)
        prev_state = state 

    child_order = bf.getchildorders()[0]
    if state != 'COMPLETED' or target_price == child_order['price']:
        draw += 1
    elif target_price < child_order['price']:
        win += 1
        pl += child_order['price'] - target_price
    else:
        lose += 1
        pl += child_order['price'] - target_price

    print('collateral:', bf.getcollateral());
    print('win:{}, lose:{}, draw:{}, pl:{}'.format(win, lose, draw, pl))
    # import pdb; pdb.set_trace()

