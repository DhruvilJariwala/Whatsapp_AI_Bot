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

connected_clients: dict[str,WebSocket]= dict()
dead_clients={}

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
    r.hset(number,mapping={"state":"AI","history":"[]","counter":0,"support_staff_id":""})
    return "Success"

def set_support_id(number:str,user_id:str):
    if not r:
        return None
    r.hset(number,mapping={"support_staff_id":user_id})

def get_support_id(number:str):
    if not r:
        return None
    res=r.hget(number,"support_staff_id")
    return res

async def send_history(number:str,user_id:str):
    response=check_history(number=number)
    history=json.loads(response)
    data=number.split("_@_")
    recieve=data[0]
    sender=data[1]
    mongo_history=fetch_mongo_data(reciever=recieve,sender=sender)
    chat_history=mongo_history+history
    if user_id in connected_clients:
            try:
                await connected_clients[user_id].send_json(chat_history)
            except:
                dead_clients[user_id]=connected_clients[user_id]

    if user_id in dead_clients:
        connected_clients.pop(user_id,None)

async def send_human_msg(number:str,chat_history:list[dict],counter:int,user_id:str):
    if not r:
        return None
    response=r.hgetall(number)
    history=json.loads(response["history"])
    history=history+chat_history
    history=json.dumps(history)
    res={"state":response['state'],"history":history,"counter":counter}
    r.hset(number,mapping=res)
    if user_id in connected_clients:
        try:
            await connected_clients[user_id].send_json(chat_history)
        except:
            dead_clients[user_id]=connected_clients[user_id]

    if user_id in dead_clients:
        connected_clients.pop(user_id,None)