import datetime
from pymongo import MongoClient
import pprint
import bitflyer_websocket
import time

client = MongoClient()
db = client.test_database

bf = bitflyer_websocket.BitflyerWebsocket()
while True:
    while not bf.execution_queue.empty():
        message = bf.execution_queue.get()
        db.executions.insert_one(message)

    while not bf.board_snapshot_queue.empty():
        message = bf.board_snapshot_queue.get()
        db.board_snapshots.insert_one(message)

    while not bf.board_update_queue.empty():
        message = bf.board_update_queue.get()
        db.board_updates.insert_one(message)
    time.sleep(0.1)
