import websocket
import json
import ccxt

symbol = 'FX_BTC_JPY'
key_json = json.load(open('key.json'))
bitflyer = ccxt.bitflyer({
        'apiKey': key_json['bitflyer']['api_key'],
        'secret': key_json['bitflyer']['api_secret']
        })

bitflyer.load_markets()

open_orders = {}

lot = 0.01

def create_buy_order(price):
    o = bitflyer.create_limit_buy_order(symbol, lot, price)
    print('create order', o)
    o['size'] = lot
    o['price'] = price
    o['side'] = 'buy'
    open_orders[o['id']] = o

def create_sell_order(price):
    o = bitflyer.create_limit_sell_order(symbol, lot, price)
    print('create order', o)
    o['size'] = lot
    o['price'] = price
    o['side'] = 'sell'
    open_orders[o['id']] = o

def on_message(ws, message):
    message_json = json.loads(message)
    param_json = message_json['params']
    channel = param_json['channel']
    if channel == 'lightning_board_snapshot_FX_BTC_JPY':
        print(param_json)

    if channel == 'lightning_board_FX_BTC_JPY':
        print(param_json)

    if channel == 'lightning_executions_BTC_JPY':
        info = param_json['message']
        print(info)
        items = open_orders.items()
        for id, order in items:
            for execution in info:
                matched_order = None
                if order['side'] == 'buy':
                    if order['id'] == execution['buy_child_order_acceptance_id']:
                        matched_order = order
                if order['side'] == 'sell':
                    if order['id'] == execution['sell_child_order_acceptance_id']:
                        matched_order = order
                if matched_order:
                    matched_order['size']  = matched_order['size'] - execution['size']
                    if matched_order['size'] <= 0 :
                        del open_orders[matched_order['id']]
                        print('delete order', matched_order['id'])

def on_open(ws):
    channels = [
            'lightning_executions_FX_BTC_JPY',
            'lightning_board_snapshot_FX_BTC_JPY',
            'lightning_board_FX_BTC_JPY',
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
