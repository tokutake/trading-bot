import websocket
import json
import ccxt

channel_symbol = 'BTC_JPY'
symbol = 'BTC/JPY'
key_json = json.load(open('key.json'))
bitflyer = ccxt.bitflyer({
        'apiKey': key_json['bitflyer']['api_key'],
        'secret': key_json['bitflyer']['api_secret']
        })

bitflyer.load_markets()

open_orders = {}

lot = 0.001

def create_buy_order(price):
    o = bitflyer.create_limit_buy_order(symbol, lot, price)
    print('create buy order', o)
    o['size'] = lot
    o['price'] = price
    o['side'] = 'buy'
    open_orders[o['id']] = o

def create_sell_order(price):
    o = bitflyer.create_limit_sell_order(symbol, lot, price)
    print('create sell order', o)
    o['size'] = lot
    o['price'] = price
    o['side'] = 'sell'
    open_orders[o['id']] = o

bids = {}
asks = {}
mid_price = None

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
    param_json = json.loads(message)['params']
    channel = param_json['channel']
    message_json = param_json['message']
    if channel == 'lightning_board_snapshot_' + channel_symbol:
        bids = {}
        asks = {}
        update_board(message_json)

    if channel == 'lightning_board_' + channel_symbol:
        update_board(message_json)
        ask = best_ask()
        bid = best_bid()
        if len(open_orders) == 0 and bid != None and ask != None and ask - 1 > bid + 1 and ask - bid < 50:
            create_buy_order(bid + 1)
            create_sell_order(ask - 1)

    if channel == 'lightning_executions_' + channel_symbol:
        info = param_json['message']
        items = open_orders.items()
        print(info)
        for id, order in items:
            for execution in info:
                matched_order = None
                matched_execution = None
                if order['side'] == 'buy':
                    if order['id'] == execution['buy_child_order_acceptance_id']:
                        matched_order = order
                        matched_execution = execution
                if order['side'] == 'sell':
                    if order['id'] == execution['sell_child_order_acceptance_id']:
                        matched_order = order
                        matched_execution = execution
                order['size']  = order['size'] - execution['size']
                print(order)
                if order['size'] <= 0 :
                    del open_orders[order['id']]
                    print('delete order', order['id'])

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

if __name__ == "__main__":
    # note: reconnection handling needed.
    ws = websocket.WebSocketApp("wss://ws.lightstream.bitflyer.com/json-rpc",
                                on_message=on_message, on_open=on_open)
    ws.run_forever()
