import json
import ccxt
import arrow
import time

symbol = 'FX_BTC_JPY'
key_json = json.load(open('key.json'))
bitflyer = ccxt.bitflyer({
        'apiKey': key_json['bitflyer']['api_key'],
        'secret': key_json['bitflyer']['api_secret']
        })

bitflyer.load_markets()
pl = 0
raw_pl = 0
bitcoin = 0
total_size = 0
first_trade = None
isFirst = True
before = None
willBreak = False
now = arrow.utcnow().shift(hours=9)
today = arrow.get('{}-{:02d}-{:02d}'.format(now.year, now.month, now.day))
while True:
    time.sleep(10)
    params = {}
    if before:
        params = {'before': before}
    trades = bitflyer.fetchMyTrades(symbol, None, 500, params)
    if len(trades) > 0:
        before = trades[0]['id']
    for trade in trades:
        info= trade['info']
        print(info)
        side = info['side']
        size = info['size']
        price = info['price']
        exec_date = arrow.get(info['exec_date']).shift(hours=9)
        if exec_date < today:
            willBreak = True
            break
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
    if willBreak:
        break

ticker = bitflyer.fetch_ticker(symbol = symbol)
print(ticker)
print("first trade:", firstTrade)
print("pl:", pl + bitcoin * ticker['last'])
print("raw pl:", raw_pl + bitcoin * ticker['last'])
print("bitcoin:", bitcoin)
print("total size:", total_size)
