from pymongo.errors import ConnectionFailure
from pymongo.mongo_client import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def push_to_mongo(chat_history:list[dict],reciever:str):
    connection_string = os.getenv("MONGODB_URI")
    try:
        client = MongoClient(connection_string)
        db = client['whatsappbot']
        collection = db[reciever]
        result = collection.insert_many(chat_history)
        print(f"\nSuccessfully inserted {len(result.inserted_ids)} documents.")
        print("Inserted IDs:", result.inserted_ids)

    except ConnectionFailure as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client:
            client.close()

def fetch_mongo_data(reciever:str,sender:str):
    connection_string = os.getenv("MONGODB_URI")
    mongo_history=[]
    try:
        client = MongoClient(connection_string)
        db = client['whatsappbot']
        collection = db[reciever]
        query_filter={"SenderID":sender}
        cursor=collection.find(query_filter)
        for document in cursor:
            document.pop("_id")
            mongo_history.append(document)
    except ConnectionFailure as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client:
            client.close()
    return mongo_history

def fetch_confing(receiver:str):
    connection_string = os.getenv("MONGODB_URI")
    data=[]
    try:
        client = MongoClient(connection_string)
        db = client['whatsappbot_conifg']
        collection = db[receiver]
        query_filter={}
        cursor=collection.find(query_filter)
        for document in cursor:
            document.pop("_id")
            data.append(document)
    except ConnectionFailure as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client:
            client.close()
    return data


def assign_chat(reciver:str):
    data=fetch_confing(receiver=reciver)
    min_count = min(d["count"] for d in data)
    ids = [d["unique_id"] for d in data if d["count"] == min_count]
    assigned_user_id= ids[0]
    return assigned_user_id

def update_count(reciver:str,user_id:str,mode:str):
    connection_string = os.getenv("MONGODB_URI")
    try:
        client = MongoClient(connection_string)
        db = client['whatsappbot_conifg']
        collection = db[reciver]
        query_filter={"unique_id":user_id}
        doc=collection.find_one(query_filter)
        count=doc.get("count")
        if mode=="up":
            new_value={"$set":{"count":count+1}}
            cursor=collection.update_one(query_filter,new_value)
        if mode=="down":
            new_value={"$set":{"count":count-1}}
            cursor=collection.update_one(query_filter,new_value)
    except ConnectionFailure as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client:
            client.close()
