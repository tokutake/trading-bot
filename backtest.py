import pymongo
import logging
import matplotlib.pyplot as plt
import numpy as np
import arrow
import pandas as pd
from collections import deque
from decimal import *

class Side():
    def __init__(self, side):
        self.side = side

    def opposite(self):
        if self.side == 'BUY':
            return 'SELL'
        else:
            return 'BUY'
    def is_opposite(self, side):
        return self.equals(side.opposite())

    def equals(self, side):
        return self.side == side

class Order():
    def __init__(self):
        self.state = None

class Position():
    def __init__(self):
        self.id = 0
        pass

class Execution():
    pass

class Exchange():
    def __init__(self):
        self.orders = {}
        self.current_order_id = 1
        self.positions = {}
        self.current_position_id = 1
        self.initial_collateral = 1000
        self.leverage = 15
        self.collateral = self.initial_collateral
        self.best_bid = None
        self.best_ask = None
        self.mid_price = None
        self.asks = {}
        self.bids = {}
        # milliseconds
        self.order_delay_time = 1000
        # bitcoin size precision
        self.size_precision = 8
        self.current_time = None
        getcontext().prec = self.size_precision
        self.is_board_initialized = False

    def get_pl(self):
        profit = self.collateral - self.initial_collateral
        for id, position in self.positions.items():
            mid_price = Decimal(self.mid_price)
            price = Decimal(position.price)
            print("get_pl(): position.size", position.size)
            if position.side == 'BUY':
                profit += round((mid_price - price) * position.size)
            else:
                profit += round((price - mid_price) * position.size)

        print("get_pl(): mid_price:{self.mid_price},profit:{profit}")
        print()
        return profit

    def send_limit_order(self, side, price, size):
        order = Order()
        order.side = side
        order.price = price
        order.size = Decimal(size)
        order.order_date = self.now().shift(seconds = self.order_delay_time)
        order.executed_size = Decimal(0)
        order.type = 'LIMIT'
        order.id = self.current_order_id
        order.state = 'ACTIVE'
        self.current_order_id += 1
        self.orders[order.id] = order

    def cancel_order(self, order):
        pass

    def opposite_side(self, side):
        if side == 'BUY':
            return 'SELL'
        else:
            return 'BUY'

    def execute_position(self, new_position):
        closed_positions = []
        # 要調査:まとまったpositionは複数の約定に分割される？
        for id, position in self.positions.items():
            if self.opposite_side(position.side) == new_position.side:
                executed_size = Decimal(0)
                # positionが完全に約定する場合
                if position.size <= new_position.size:
                    new_position.size -= position.size
                    executed_size = position.size
                    position.size = Decimal(0)
                # positionが一部約定した場合
                else:
                    position.size -= new_position.size
                    executed_size = new_position.size
                    new_position.size = Decimal(0)

                pl = 0
                if position.side == 'BUY':
                    pl = round((new_position.price - position.price) * executed_size)
                else:
                    pl = round((position.price - new_position.price) * executed_size)
                self.collateral += pl

                if position.size == 0:
                    closed_positions.append[position]
                if new_position.size == 0:
                    break

        if new_position.size > 0:
            self.positions[new_position.id] = new_position
        for position in closed_positions:
            del self.positions[positions.id]

    def on_execution(self, execution):
        execution_price = execution['price']
        execution_side = execution['side']
        exec_date = arrow.get(execution['exec_date'])
        execution_size = Decimal(execution['size'])

        for id, order in self.orders.items():
            position = None
            if self.opposite_side(order.side) == execution_side and order.order_date > exec_date:
                matched = False
                # 値段が不利な約定をシミュレーションするよりは、order自体に先行する板情報を持たせた方が良い？
                # import pdb; pdb.set_trace()
                # 板のシミュレーションまで行なっていないので、買いの注文価格を下回る価格の約定があった場合、約定したとしている
                if order.side == 'BUY' and order.price < execution_price:
                    matched = True
                if order.side == 'SELL' and order.price > execution_price:
                    matched = True
                if matched:
                    position = Position()
                    position.side = order.side
                    position.price = execution_price
                    position.size = Decimal(0)

                    # 注文が完全に約定した場合
                    if order.size - order.executed_size >= execution_size:
                        position.size += order.size - execution_size
                        execution_size -= order.size - order.executed_size
                        order.executed_size = order.size
                        order.state = 'COMPLETED'
                    # 注文が一部約定した場合
                    else:
                        position.size += execution_size
                        order.executed_size += execution_size
                        execution_size = 0

            if position:
                position.date = self.now()
                position.id = self.current_position_id
                self.current_position_id += 1
                self.execute_position(position)

        completed_orders = []
        for id, order in self.orders.items():
            if order.state == 'COMPLETED':
                completed_orders.append(order)
        for order in completed_orders:
            del self.orders[order.id]


    def on_my_order_execute(self, order, execution):
        pass

    def now(self):
        return self.current_time

    def update_board(self, message_json):
        self.mid_price = message_json['mid_price']
        for bid in message_json['bids']:
            self.bids[bid['price']] = bid['size']
        for ask in message_json['asks']:
            self.asks[ask['price']] = ask['size']
        if len(self.bids) > 0:
            sorted_bids = sorted(self.bids.items(), reverse = True, key = lambda bid : bid[0])
            self.best_bid = sorted_bids[0][0]
        if len(self.asks) > 0:
            sorted_asks = sorted(self.asks.items(), key = lambda ask : ask[0])
            self.best_ask = sorted_asks[0][0]
        if message_json['message_type'] == 'snapshot':
            self.is_board_initialized = True

class Strategy():
    def __init__(self, exchange):
        self.exchange = exchange

    def on_update(self):
        if len(self.exchange.orders) == 0 and self.exchange.mid_price != None:
            # import pdb; pdb.set_trace()
            self.exchange.send_limit_order('BUY', self.exchange.mid_price, 1)

class Backtest():
    def __init__(self):
        client = pymongo.MongoClient()
        self.db = client.bf
        self.dates = []
        self.prices = []
        self.price_size_map = {}
        self.exchange = Exchange()
        self.strategy = Strategy(self.exchange)
        self.pls = []

    def run(self):
        start = arrow.utcnow()
        start_time = arrow.utcnow().shift(minutes = -1)
        date_str = start_time.strftime("%Y-%m-%dT%H:%M")

        messages = []


        for execution in self.db.executions.find({'exec_date': {"$gt" : date_str}}):
            execution['date'] = arrow.get(execution['exec_date']).datetime.replace(tzinfo=None)
            execution['message_type'] = 'execution'
            messages.append(execution)

        for snapshot in self.db.board_snapshots.find({'date': {"$gt" : start_time.datetime}}):
            snapshot['message_type'] = 'snapshot'
            messages.append(snapshot)

        for board_update in self.db.board_updates.find({'date': {"$gt" : start_time.datetime}}):
            board_update['message_type'] = 'board_update'
            messages.append(board_update)

        sorted_messages = sorted(messages, key = lambda item : item['date'])

        for message in sorted_messages:
            if message['message_type'] == 'execution':
                print(message)
                self.exchange.current_time = arrow.get(message['exec_date'])
                self.exchange.on_execution(message)
                self.strategy.on_update()
                self.prices.append(message['price'])
                self.dates.append(message['exec_date'])
                self.pls.append(self.exchange.get_pl())
            else:
                self.exchange.update_board(message)

        print("elapsed seconds:", arrow.utcnow() - start)

backtest = Backtest()
backtest.run()

df_price = pd.DataFrame({'price' : backtest.prices}, index = backtest.dates)
df_pl = pd.DataFrame({'pl' : backtest.pls}, index = backtest.dates)

print(df_price)
df_price.plot()
df_pl.plot()
plt.show()
