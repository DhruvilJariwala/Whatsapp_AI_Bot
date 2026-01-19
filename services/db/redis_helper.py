import redis
from fastapi import WebSocket
import os
from dotenv import load_dotenv
import json
from services.db.mongo_helper import fetch_mongo_data

load_dotenv()

r = redis.Redis.from_url(os.getenv("REDIS_URI"),decode_responses=True)
connected_clients: set[WebSocket] =set()
dead_clients=[]

def check_state(soruce:str,reciever:str=None):
    res=r.hget(soruce,"state")
    if res is None:
        data={"state":"AI","receiver_id":reciever}
        r.hset(soruce,mapping=data)
        return "AI"
    return res

def get_id(number:str):
    res=r.hget(number,"receiver_id")
    return res

def check_history(number:str):
    res=r.hget(number,"history")
    return res

def append_history(number:str,chat_history:list[dict],counter:int):
    response=r.hgetall(number)
    chat_history=json.dumps(chat_history)
    res={"state":response['state'],"history":chat_history,"counter":counter}
    r.hset(number,mapping=res)

def get_counter(number:str):
    res=r.hget(number,"counter")
    if res is None:
        r.hset(number,mapping={"counter":0})
        return 0
    return res

def change_state(number:str):
    r.hset(number,"state","Human")

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