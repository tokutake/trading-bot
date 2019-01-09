from pymongo import MongoClient
import matplotlib.pyplot as plt

c = MongoClient()
db = c.test_db

def price_histgram():
    count = 0
    price_map = {}
    for e in db.board_executions.find({}):
        price = e['price']
        if price_map.get(price) == None:
            price_map[price] = 0
        price_map[price] += e['size']
        print(e)
        count += 1

    sizes = []
    keys = sorted(price_map.keys())
    for k in keys:
        sizes.append(price_map[k])
        print(price_map[k], k)

    plt.plot(keys, sizes)
    plt.show()

def board_block_sim():
    for e in db.board_executions.find({}):

price_histgram()
