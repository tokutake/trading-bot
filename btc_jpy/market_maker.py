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

lot = 0.01

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

def on_message(ws, message):
    message_json = json.loads(message)
    param_json = message_json['params']
    channel = param_json['channel']
    if channel == 'lightning_ticker_' + channel_symbol:
        info = param_json['message']
        best_bid = info['best_bid']
        best_ask = info['best_ask']
        if len(open_orders) == 0:
            create_buy_order(best_bid + 1)
            create_sell_order(best_ask - 1)

    if channel == 'lightning_executions_' + channel_symbol:
        info = param_json['message']
        items = open_orders.items()
        print(info)
        for id, order in items:
            for execution in info:
                if order['side'] == 'buy':
                    if order['id'] == execution['buy_child_order_acceptance_id']:
                        order['size']  = order['size'] - execution['size']
                        print(order)
                        if order['size'] <= 0 :
                            del open_orders[order['id']]
                            print('delete order', order['id'])
                if order['side'] == 'sell':
                    if order['id'] == execution['sell_child_order_acceptance_id']:
                        order['size']  = order['size'] - execution['size']
                        print(order)
                        if order['size'] <= 0 :
                            del open_orders[order['id']]
                            print('delete order', order['id'])

def on_open(ws):
    channels = [
            'lightning_executions_' + channel_symbol,
            'lightning_ticker_' + channel_symbol,
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
