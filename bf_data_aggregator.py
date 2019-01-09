import datetime
from pymongo import MongoClient
import pprint
import bitflyer_websocket

client = MongoClient()
db = client.test_database

bf = bitflyer_websocket.BitflyerWebsocket()
while True:
    while not bf.execution_queue.empty():
        message = bf.execution_queue.get()
        print(message)
        inserted_id = db.board_executions.insert_one(message).inserted_id
        print(inserted_id)

    while not bf.board_snapshot_queue.empty():
        message = bf.board_snapshot_queue.get()
        print(message)
        inserted_id = db.board_snapshots.insert_one(message).inserted_id
        print(inserted_id)

    while not bf.board_update_queue.empty():
        message = bf.board_update_queue.get()
        print(message)
        inserted_id = db.board_updates.insert_one(message).inserted_id
        print(inserted_id)
