import websocket
import json
import MySQLdb

CHANNEL = "lightning_executions_FX_BTC_JPY"
symbol = 'FX_BTC_JPY'

mysql_json = json.load(open('mysql.json'))
db = MySQLdb.connect(
        host = mysql_json['host'],
        db = mysql_json['db'],
        user = mysql_json['user'],
        passwd = mysql_json['password']
        )
cursor = db.cursor()

def on_message(ws, message):
    message = json.loads(message)
    if message["method"] == "channelMessage":
        params_message = message["params"]["message"]

        for e in params_message:
            date = e['exec_date'].replace('T', ' ').replace('Z', '')
            sql = f'insert into bitflyer_executions values ({e["id"]}, "{e["side"]}", {e["price"]}, {e["size"]}, "{date}", "{e["buy_child_order_acceptance_id"]}", "{e["sell_child_order_acceptance_id"]}", "{symbol}");'
            cursor.execute(sql)
            print(sql)
        db.commit()

def on_open(ws):
    ws.send(json.dumps({"method": "subscribe",
                        "params": {"channel": CHANNEL}}))

def on_close(ws):
    print('## close ##')

if __name__ == "__main__":
    # note: reconnection handling needed.
    ws = websocket.WebSocketApp("wss://ws.lightstream.bitflyer.com/json-rpc",
                                on_message=on_message, on_open=on_open)
    ws.run_forever()
