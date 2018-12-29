import ccxt
import time
import json

key_file = open('key.json', 'r')
keys = json.load(key_file)
bitflyer = ccxt.bitflyer()
liquid = ccxt.liquid()

bitflyer.load_markets()
liquid.load_markets()

def sim_order(exchange, lot, side):
    exchange = bitflyer
    if exchange == 'liquid':
        exchange = liquid

symbols = liquid.symbols
print(symbols)
symbols = bitflyer.symbols
print(symbols)

differences = []
lot = 0.1
pl = 0
while True:
    ticker = bitflyer.fetchTicker(symbol = 'FX_BTC_JPY')
    bitflyer_ticker = ticker
    best_ask = ticker['info']['best_ask']
    best_bid = ticker['info']['best_bid']
    ticker = liquid.fetchTicker(symbol = 'BTC/JPY')
    liquid_ticker = ticker
    market_ask = float(ticker['info']['market_ask'])
    market_bid = float(ticker['info']['market_bid'])

    diff = 0
    if best_ask > market_bid:
        print('best_ask:', best_ask)
        print('market_bid:', market_bid)
        diff = market_bid - best_ask
        print('diff:', market_bid - best_ask)
    else:
        print('market_ask:', market_ask)
        print('best_bid:', best_bid)
        diff = market_ask - best_bid
        print('diff:', market_ask - best_bid)

    differences.append(diff)
    if len(differences) < 20:
        time.sleep(1)
        continue

    time.sleep(1)

