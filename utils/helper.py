import redis
import json
import pymongo
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
import os
load_dotenv()

r= redis.Redis(host='localhost', port=6379,db=0,decode_responses=True)
r = redis.Redis.from_url(os.getenv("REDIS_URI"))

def check_state(soruce:str):
    res=r.hget(soruce,"state")
    if res is None:
        r.hset(soruce,mapping={"state":"AI"})
    resp=r.hget(soruce,"state")
    return resp

def check_history(number:str):
    res=r.hget(number,"history")
    return res

def initial_history(number:str,chat_history:list[dict]):
    response=r.hgetall(number)
    chat_history=json.dumps(chat_history)
    res={"state":response['state'],"history":chat_history}
    r.hset(number,mapping=res)

def append_history(number:str,chat_history:list[dict],counter:int):
    response=r.hgetall(number)
    history=json.loads(response.get("history")) 
    for hist in history:
        chat_history.append(hist)
    chat_history=json.dumps(chat_history)
    res={"state":response['state'],"history":chat_history,"counter":counter}
    r.hset(number,mapping=res)

def get_counter(number:str):
    res=r.hget(number,"counter")
    if res is None:
        r.hset(number,mapping={"counter":2})
    resp= r.hget(number,"counter")
    return resp

def push_to_mongo(chat_history:list[dict],reciever:str):
    connection_string = os.getenv("MONGODB_URI")
    try:
        client = MongoClient(connection_string)
        db = client['whatsappbot']
        collection = db[reciever]
        result = collection.insert_many(chat_history)
        print(f"\nSuccessfully inserted {len(result.inserted_ids)} documents.")
        print("Inserted IDs:", result.inserted_ids)

    except pymongo.errors.ConnectionFailure as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client:
            client.close()

