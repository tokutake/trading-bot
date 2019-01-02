import ccxt
import time
import json
from forex_python.converter import CurrencyRates

def debug():
    import pdb; pdb.set_trace()

key_file = open('key.json', 'r')
keys = json.load(key_file)
bitflyer = ccxt.bitflyer()
bitmex = ccxt.bitmex()

bitflyer.load_markets()
bitmex.load_markets()

symbols = bitmex.symbols
print(symbols)
symbols = bitflyer.symbols
print(symbols)

c = CurrencyRates()
rate = c.get_rate('USD', 'JPY')
diffs = []
lot = 0.1
pl = 0

def max_diff(n):
    max = None
    for i in range(1, n + 1):
        if len(diffs) - i < 0:
            break
        diff = diffs[len(diffs) - i]
        if max == None:
            max = diff
        if abs(diff) > abs(max):
            max = diff
    return max

def min_diff(n):
    min = 1000000
    for i in range(1, n + 1):
        if len(diffs) - i < 0:
            break
        diff = diffs[len(diffs) - i]
        if diff < min:
            min = diff
    return min

class Position:
    pass

class Asset:
    pass

asset = Asset()
asset.initial_jpy = 20000
asset.jpy = asset.initial_jpy
asset.btc = 0
asset.initial_xbt = 0.01
asset.xbt = asset.initial_xbt

bitflyer_position = Position()
bitmex_position = Position()

bitflyer_position.side = None
bitmex_position.side = None

def pl(bitflyer_price, bitmex_price, rate):
    # debug()
    initial_asset = asset.initial_jpy + asset.initial_xbt * bitmex_price * rate
    total = asset.jpy + asset.xbt * bitmex_price * rate
    if has_position():
        total += bitflyer_price * asset.btc
        unrealized_xbt = 0
        if bitmex_position.side == 'buy':
            unrealized_xbt = (bitmex_price - bitmex_position.price) * bitmex_position.size / bitmex_price
        else:
            unrealized_xbt = (bitmex_position.price - bitmex_price) * bitmex_position.size / bitmex_price
        total += unrealized_xbt * rate
    return total - initial_asset

def open(bitflyer_price, bitmex_price, diff):
    if diff > 0:
        bitflyer_position.side = 'sell'
        bitflyer_position.price = bitflyer_price
        bitflyer_position.size = 0.1
        asset.jpy += bitflyer_price * 0.1
        asset.btc -= 0.1
        bitmex_position.side = 'buy'
        bitmex_position.price = bitmex_price
        bitmex_position.size = 0.1
    else:
        bitflyer_position.side = 'buy'
        bitflyer_position.price = bitflyer_price
        bitflyer_position.size = 0.1
        asset.jpy -= bitflyer_price * 0.1
        asset.btc += 0.1
        bitmex_position.side = 'sell'
        bitmex_position.price = bitmex_price
        bitmex_position.size = 0.1

def close(bitflyer_price, bitmex_price):
    asset.jpy += bitflyer_price * asset.btc
    if bitflyer_position.side == 'buy':
        asset.btc -= 0.1
    else:
        asset.btc -= 0.1
    bitflyer_position.side = None
    bitflyer_position.price = None
    bitflyer_position.size = 0
    if bitmex_position.side == 'buy':
        asset.xbt += (bitmex_price - bitmex_position.price) * bitmex_position.size / bitmex_price
    else:
        asset.xbt += (bitmex_price - bitmex_position.price) * bitmex_position.size / bitmex_price
    bitmex_position.side = None
    bitmex_position.price = None
    bitmex_position.size = 0

def has_position():
    return bitflyer_position.side != None and bitmex_position.side != None

opening_diff = None

while True:
    rate = c.get_rate('USD', 'JPY')
    print('JPY/USD:', rate)
    bitflyer_ticker = bitflyer.fetchTicker(symbol = 'FX_BTC_JPY')
    bitmex_ticker = bitmex.fetchTicker(symbol = 'BTC/USD')
    print('bitmex:', bitmex_ticker['last'])
    print('bitflyer:', bitflyer_ticker['last'])
    diff = bitflyer_ticker['last'] - bitmex_ticker['last'] * rate
    print('diff:', diff)
    print('max diff:', max_diff(5))
    print('jpy:', asset.jpy)
    print('xbt:', asset.xbt)
    print('pl:', pl(bitflyer_ticker['last'], bitmex_ticker['last'], rate))
    if opening_diff:
        print("opening_diff:", opening_diff)
    if max_diff(5) and abs(diff) > abs(max_diff(5)) and not has_position():
        print('open')
        open(bitflyer_ticker['last'], bitmex_ticker['last'], diff)
        opening_diff = diff
    if has_position() and abs(opening_diff) > abs(diff):
        print('close')
        close(bitflyer_ticker['last'], bitmex_ticker['last'])
        opening_diff = None
    diffs.append(diff)
    print()

    time.sleep(2)

