import websocket
import json
import threading
import queue
import ccxt
import datetime

class BitflyerWebsocket():
    is_fx = True

    channel_symbol = 'BTC_JPY'
    symbol = 'BTC/JPY'
    if is_fx:
        channel_symbol = 'FX_BTC_JPY'
        symbol = 'FX_BTC_JPY'

    is_board_initialized = False
    bids = {}
    asks = {}
    mid_price = None
    board_update_queue = queue.Queue()
    board_snapshot_queue = queue.Queue()
    execution_queue = queue.Queue()

    executions = []

    positions = []
    orders = []

    def __init__(self):
        key_json = json.load(open('key.json'))
        self.bf = ccxt.bitflyer({
            'apiKey': key_json['bitflyer']['api_key'],
            'secret': key_json['bitflyer']['api_secret']
        })

        self.bf.load_markets()

        # note: reconnection handling needed.
        self.ws = websocket.WebSocketApp("wss://ws.lightstream.bitflyer.com/json-rpc",
                                    on_message=self.on_message, on_open=self.on_open)
        self.wst = threading.Thread(target=lambda: self.ws.run_forever())
        self.wst.daemon = True
        self.wst.start()

    def print_board(self):
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

    def send_parent_order(self, params):
        return self.bf.request("sendparentorder", "private", "POST", params)

    def get_active_parent_orders(self, params = {}):
        params['product_code'] = self.symbol
        orders = self.bf.request('getparentorders', 'private', params = params)
        active_orders = []
        for order in orders:
            state = order['parent_order_state']
            if state == 'ACTIVE':
                active_orders.append(order)
        return active_orders

    def get_parent_orders(self, params = {}):
        params['product_code'] = self.symbol
        return self.bf.request('getparentorders', 'private', params = params)

    def get_parent_order(self, request_order):
        orders = self.bf.request('getparentorders', 'private', params = {'product_code': self.symbol})
        for order in orders:
            if request_order['parent_order_acceptance_id'] == order['parent_order_acceptance_id']:
                return order
        return None

    def cancel_parent_order(self, order):
        return self.bf.request('cancelparentorder', 'private', 'POST', params = {'product_code': self.symbol, 'parent_order_id': order['parent_order_id']})

    def get_best_ask(self):
        if not self.is_board_initialized:
            return None
        ask = None
        for price, size in self.asks.items():
            if size <= 0.0:
                continue
            if ask == None:
                ask = price
            elif price < ask:
                ask = price
        return ask

    def get_best_bid(self):
        if not self.is_board_initialized:
            return None
        bid = None
        for price, size in self.bids.items():
            if size <= 0.0:
                continue
            if bid == None:
                bid = price
            elif price > bid:
                bid = price
        return bid

    def get_best_bid_with_depth(self, depth):
        total_size = 0
        target_price = None
        for bid in self.bids.items():
            price, size = bid
            total_size += size
            if target_price == None:
                target_price = price
            if total_size >= depth:
                break
            target_price = price
        return target_price

    def spread(self):
        if not self.is_board_initialized:
            return None
        else:
            return self.best_ask() - self.best_bid()

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
        message_json['date'] = datetime.datetime.utcnow()
        self.board_snapshot_queue.put(message_json)
        self.bids = {}
        self.asks = {}
        self.update_board(message_json)
        self.is_board_initialized = True

    def on_board(self, message_json):
        message_json['date'] = datetime.datetime.utcnow()
        self.board_update_queue.put(message_json)
        self.update_board(message_json)

    def on_execution(self, message_json):
        for execution in message_json:
            self.execution_queue.put(execution)
            self.executions.append(execution)

    def getcollateral(self):
        return self.bf.request('getcollateral', 'private')['collateral']

    def getchildorders(self):
        return self.bf.request('getchildorders', 'private', params = {'product_code': self.symbol})

    def getchildorders(self, parent_order_id):
        return self.bf.request('getchildorders', 'private', params = {'product_code': self.symbol, 'parent_order_id': parent_order_id})

    def getpositions(self):
        return self.bf.request('getpositions', 'private', params = {'product_code': self.symbol})

    def create_market_order(self, side, size):
        return self.bf.create_market_order(self.symbol, side, size)
