import json
import ccxt

symbol = 'FX_BTC_JPY'
key_json = json.load(open('key.json'))
bitflyer = ccxt.bitflyer({
        'apiKey': key_json['bitflyer']['api_key'],
        'secret': key_json['bitflyer']['api_secret']
        })

bitflyer.load_markets()
trades = bitflyer.fetchMyTrades(symbol = symbol)
pl = 0
raw_pl = 0
bitcoin = 0
total_size = 0
first_trade = None
isFirst = True
for trade in trades:
    info= trade['info']
    print(info)
    side = info['side']
    size = info['size']
    price = info['price']
    if isFirst:
        firstTrade = info
        isFirst = False
    print('side:{}, size:{}, price:{}'.format(side, size, price))
    if side == 'BUY':
        pl -= round(price * size)
        raw_pl -= price * size
        bitcoin += size
        total_size += size
    else:
        pl += round(price * size)
        raw_pl += price * size
        bitcoin -= size
        total_size += size

ticker = bitflyer.fetch_ticker(symbol = symbol)
print("first trade:", firstTrade)
print("pl:", pl + bitcoin * ticker['last'])
print("raw pl:", raw_pl + bitcoin * ticker['last'])
print("total size:", total_size)
