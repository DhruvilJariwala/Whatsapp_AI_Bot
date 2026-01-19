import redis
from redis.exceptions import ConnectionError
from fastapi import WebSocket
import os
from dotenv import load_dotenv
import json
from services.db.mongo_helper import fetch_mongo_data

load_dotenv()
r=None
try:
    r = redis.Redis.from_url(os.getenv("REDIS_URI"),decode_responses=True)
except ConnectionError :
    print("Redis Connection Error")    
except Exception as e:
    print(f"Redis Error: {e}")

connected_clients: set[WebSocket] =set()
dead_clients=[]

def check_state(source:str,reciever:str=None):
    if not r:
        return None
    res=r.hget(source,"state")
    if res is None:
        data={"state":"AI","receiver_id":reciever}
        r.hset(source,mapping=data)
        return "AI"
    return res

def get_id(number:str):
    if not r:
        return None
    res=r.hget(number,"receiver_id")
    return res

def check_history(number:str):
    if not r:
        return None
    res=r.hget(number,"history")
    return res

def append_history(number:str,chat_history:list[dict],counter:int):
    if not r:
        return None
    response=r.hgetall(number)
    chat_history=json.dumps(chat_history)
    res={"state":response['state'],"history":chat_history,"counter":counter}
    r.hset(number,mapping=res)

def get_counter(number:str):
    if not r:
        return None
    res=r.hget(number,"counter")
    if res is None:
        r.hset(number,mapping={"counter":0})
        return 0
    return res

def change_state(number:str):
    if not r:
        return None
    r.hset(number,"state","Human")

def close_ticket(number:str):
    if not r:
        return None
    r.hset(number,mapping={"state":"AI","history":"[]","counter":0})
    return "Success"

async def send_history(number:str):
    response=check_history(number=number)
    history=json.loads(response)
    data=number.split("_@_")
    recieve=data[0]
    sender=data[1]
    mongo_history=fetch_mongo_data(reciever=recieve,sender=sender)
    chat_history=mongo_history+history
    for ws in connected_clients:
        try:
           await ws.send_json(chat_history)
        except:
            dead_clients.append(ws)
                
    for ws in dead_clients:
        connected_clients.remove(ws)

async def send_human_msg(number:str,chat_history:list[dict],counter:int):
    if not r:
        return None
    response=r.hgetall(number)
    history=json.loads(response["history"])
    history=history+chat_history
    history=json.dumps(history)
    res={"state":response['state'],"history":history,"counter":counter}
    r.hset(number,mapping=res)
    answer=check_state(number)
    if answer=="Human":
        for ws in connected_clients:
            try:
                await ws.send_json(chat_history)
            except:
                dead_clients.append(ws)

        for ws in dead_clients:
            connected_clients.remove(ws)