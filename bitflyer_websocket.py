import websocket
import json
import threading
import queue

class BitflyerWebsocket():
    is_fx = True

    channel_symbol = 'BTC_JPY'
    symbol = 'BTC/JPY'
    if is_fx:
        channel_symbol = 'FX_BTC_JPY'
        symbol = 'FX_BTC_JPY'

    bids = {}
    asks = {}
    mid_price = None

    executions = []

    def __init__(self):
        # note: reconnection handling needed.
        self.ws = websocket.WebSocketApp("wss://ws.lightstream.bitflyer.com/json-rpc",
                                    on_message=self.on_message, on_open=self.on_open)
        self.wst = threading.Thread(target=lambda: self.ws.run_forever())
        self.wst.daemon = True
        self.wst.start()

    def print_boar(self):
        for price, size in self.asks.items():
            print('price {}, size {}'.format(price, size))
        for price, size in self.bids.items():
            print('price {}, size {}'.format(price, size))

    def update_board(self, message_json):
        self.mid_price = message_json['mid_price']
        for bid in message_json['bids']:
            self.bids[bid['price']] = bid['size']
        for ask in message_json['asks']:
            self.asks[ask['price']] = ask['size']

    def on_message(self, message):
        param_json = json.loads(message)['params']
        channel = param_json['channel']
        message_json = param_json['message']
        if channel == 'lightning_board_snapshot_' + self.channel_symbol:
            self.on_board_snapshot(message_json)

        if channel == 'lightning_board_' + self.channel_symbol:
            self.on_board(message_json)

        if channel == 'lightning_executions_' + self.channel_symbol:
            self.on_execution(message_json)

    def on_open(self):
        channels = [
                'lightning_executions_' + self.channel_symbol,
                'lightning_board_snapshot_' + self.channel_symbol,
                'lightning_board_' + self.channel_symbol,
                ]
        for channel in channels:
            self.ws.send(json.dumps({"method": "subscribe",
                                "params": {"channel": channel}}))

    def on_close(self, ws):
        print('## close ##')

    def on_board_snapshot(self, message_json):
        self.bids = {}
        self.asks = {}
        self.update_board(message_json)

    def on_board(self, message_json):
        self.update_board(message_json)

    def on_execution(self, message_json):
        for execution in message_json:
            self.executions.append(execution)
