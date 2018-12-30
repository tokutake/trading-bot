import websocket
import json
import ccxt

symbol = 'BTC_JPY'
key_json = json.load(open('key.json'))
bitflyer = ccxt.bitflyer({
        'apiKey': key_json['bitflyer']['api_key'],
        'secret': key_json['bitflyer']['api_secret']
        })

bitflyer.load_markets()

open_orders = {}

lot = 0.01

def create_buy_order(price):
    o = bitflyer.create_limit_buy_order('BTC/JPY', lot, price)
    print('create order', o)
    o['amount'] = lot
    o['price'] = price
    o['side'] = 'buy'
    open_orders[o['id']] = o

def create_sell_order(price):
    o = bitflyer.create_limit_sell_order('BTC/JPY', lot, price)
    print('create order', o)
    o['amount'] = lot
    o['price'] = price
    o['side'] = 'sell'
    open_orders[o['id']] = o

def on_message(ws, message):
    message_json = json.loads(message)
    param_json = message_json['params']
    channel = param_json['channel']
    if channel == 'lightning_ticker_BTC_JPY':
        info = param_json['message']
        best_bid = info['best_bid']
        best_ask = info['best_ask']
        if len(open_orders) == 0:
            create_buy_order(best_bid + 1)
            create_sell_order(best_ask - 1)

    if channel == 'lightning_executions_BTC_JPY':
        info = param_json['message']
        print(info)
        items = open_orders.items()
        for id, order in items:
            for execution in info:
                if order['side'] == 'buy':
                    if order['id'] == execution['buy_child_order_acceptance_id']:
                        order['size']  = order['size'] - execution['size']
                        if order['size'] <= 0 :
                            del open_orders[order['id']]
                            print('delete order', order['id'])
                if order['side'] == 'sell':
                    if order['id'] == execution['sell_child_order_acceptance_id']:
                        order['size']  = order['size'] - execution['size']
                        if order['size'] <= 0 :
                            del open_orders[order['id']]
                            print('delete order', order['id'])

def on_open(ws):
    channels = [
            'lightning_executions_BTC_JPY',
            'lightning_ticker_BTC_JPY',
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
