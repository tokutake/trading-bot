import websocket
import json
import ccxt
import threading
import time
import queue
import datetime

is_fx = True

channel_symbol = 'BTC_JPY'
symbol = 'BTC/JPY'
if is_fx:
    channel_symbol = 'FX_BTC_JPY'
    symbol = 'FX_BTC_JPY'

key_json = json.load(open('key.json'))
bitflyer = ccxt.bitflyer({
        'apiKey': key_json['bitflyer']['api_key'],
        'secret': key_json['bitflyer']['api_secret']
        })

bitflyer.load_markets()

open_orders = {}
open_interests = {}
fetched_open_orders = []

lot = 0.02

def append_open_order(order, lot, price, side):
    print('create buy order', order['id'])
    order['size'] = lot
    order['price'] = price
    order['side'] = side
    order['timestamp'] = datetime.datetime.now().timestamp()
    open_orders[order['id']] = order

def create_buy_order(price):
    order = bitflyer.create_limit_buy_order(symbol, lot, price)
    append_open_order(order, lot, price, 'buy')

def create_sell_order(price):
    order = bitflyer.create_limit_sell_order(symbol, lot, price)
    append_open_order(order, lot, price, 'sell')

bids = {}
asks = {}
mid_price = None

q = queue.Queue()
max_open_order_pair = 3

def update_board(message_json):
    mid_price = message_json['mid_price']
    for bid in message_json['bids']:
        bids[bid['price']] = bid['size']
    for ask in message_json['asks']:
        asks[ask['price']] = ask['size']

def best_ask():
    ask = None
    for price, size in asks.items():
        if size == 0:
            continue
        if ask == None:
            ask = price
        if price < ask:
            ask = price
    return ask

def best_bid():
    bid = None
    for price, size in bids.items():
        if size == 0:
            continue
        if bid == None:
            bid = price
        if price > bid:
            bid = price
    return bid

def print_board():
    for price, size in asks.items():
        print('price {}, size {}'.format(price, size))
    for price, size in bids.items():
        print('price {}, size {}'.format(price, size))


def on_message(ws, message):
    q.put(message)

def on_open(ws):
    channels = [
            'lightning_executions_' + channel_symbol,
            'lightning_board_snapshot_' + channel_symbol,
            'lightning_board_' + channel_symbol,
            ]
    for channel in channels:
        ws.send(json.dumps({"method": "subscribe",
                            "params": {"channel": channel}}))

def on_close(ws):
    print('## close ##')

def get_max_open_order_side_count():
    buy_order_count = get_open_order_count('buy')
    sell_order_count = get_open_order_count('sell')
    return max(buy_order_count, sell_order_count)

def get_open_order_count(side):
    count = 0
    for id, order in open_orders.items():
        if order['side'] == side:
            count += 1
    return count

class Bot(threading.Thread):
    def run(self):
        while True:
            if q.empty():
                continue

            message = q.get()
            param_json = json.loads(message)['params']
            channel = param_json['channel']
            message_json = param_json['message']
            if channel == 'lightning_board_snapshot_' + channel_symbol:
                bids = {}
                asks = {}
                update_board(message_json)
                expired_order = []
                for id, order in open_orders.items():
                    now = datetime.datetime.now()
                    if now.timestamp() - order['timestamp'] > 30:
                        expired_order.append(order)
                for order in expired_order:
                    print('cancel order:', order['id'])
                    bitflyer.cancel_order(order['id'], symbol)
                    print('delete order:id:{}'.format(order['id']))
                    del open_orders[order['id']]
                    if order['side'] == 'buy':
                        create_buy_order(best_bid() + 1)
                    if order['side'] == 'sell':
                        create_sell_order(best_ask() - 1)

            if channel == 'lightning_board_' + channel_symbol:
                update_board(message_json)
                ask = best_ask()
                bid = best_bid()
                if bid == None or ask == None or ask - 1 <= bid + 1:
                    continue
                # import pdb; pdb.set_trace()

                buy_order_count = get_open_order_count('buy')
                sell_order_count = get_open_order_count('sell')
                if abs(buy_order_count - sell_order_count) > 1:
                    continue
                if get_max_open_order_side_count() < max_open_order_pair:
                    create_buy_order(bid + 1)
                    create_sell_order(ask - 1)
                    print('len(open_orders)', len(open_orders))

            if channel == 'lightning_executions_' + channel_symbol:
                info = param_json['message']
                items = open_orders.items()
                closed_orders = []
                for id, order in items:
                    for execution in info:
                        matched = False
                        if order['side'] == 'buy':
                            if order['id'] == execution['buy_child_order_acceptance_id']:
                                matched = True
                        if order['side'] == 'sell':
                            if order['id'] == execution['sell_child_order_acceptance_id']:
                                matched = True
                        if matched:
                            order['size']  = order['size'] - execution['size']
                            # import pdb; pdb.set_trace()
                            print('matched order:id:{}, size:{}, execution size:{}'.format(order['id'], order['size'], execution['size']))
                            if order['size'] <= 0 :
                                closed_orders.append(open_orders[order['id']])
                for order in closed_orders:
                    print('delete order:id:{}, size:{}'.format(order['id'], order['size']))
                    del open_orders[order['id']]


if __name__ == "__main__":
    # note: reconnection handling needed.
    ws = websocket.WebSocketApp("wss://ws.lightstream.bitflyer.com/json-rpc",
                                on_message=on_message, on_open=on_open)
    bot = Bot()
    bot.start()
    ws.run_forever()
