import ccxt
import time
import json

key_file = open('key.json', 'r')
keys = json.load(key_file)
bitflyer = getattr(ccxt, 'bitflyer')()
liquid = getattr(ccxt, 'liquid')()

bitflyer.load_markets()
liquid.load_markets()

symbols = liquid.symbols
print(symbols)
symbols = bitflyer.symbols
print(symbols)


while True:
    ticker = bitflyer.fetchTicker(symbol = 'FX_BTC_JPY')
    bitflyer_ticker = ticker
    best_ask = ticker['info']['best_ask']
    best_bid = ticker['info']['best_bid']
    print('best_ask:', best_ask)
    print('best_bid:', best_bid)
    ticker = liquid.fetchTicker(symbol = 'BTC/JPY')
    liquid_ticker = ticker
    market_ask = float(ticker['info']['market_ask'])
    market_bid = float(ticker['info']['market_bid'])
    print('market_ask:', market_ask)
    print('market_bid:', market_bid)

    if best_ask > market_bid:
        ask = best_ask
        bid = market_bid
        print('diff:', ask - bid)
    else:
        ask = market_ask
        bid = best_bid
        print('diff:', ask - bid)
    time.sleep(1)
