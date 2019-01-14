import pymongo
import logging
import matplotlib.pyplot as plt
import numpy as np
import arrow
import pandas as pd

class Backtest():
    def __init__(self):
        client = pymongo.MongoClient()
        self.db = client.bf
        self.dates = []
        self.prices = []
        self.price_size_map = {}

    def run(self):
        start = arrow.utcnow()
        for execution in self.db.executions.find({'exec_date': {"$gt" :'2019-01-14T00:00:00.'}}):
            print(execution)
            price = execution['price']
            if not self.price_size_map.get(price):
                self.price_size_map[price] = 0
            self.price_size_map[price] += execution['size']

        print("elappsed seconds:", arrow.utcnow() - start)

backtest = Backtest()
backtest.run()

prices = [x[0] for x in sorted(backtest.price_size_map.items())]
sizes = [x[1] for x in sorted(backtest.price_size_map.items())]
df = pd.DataFrame({'price' : prices}, index = sizes)

print(df)
df.plot()
plt.show()
# plt.plot(backtest.dates, backtest.prices)
# plt.show()
