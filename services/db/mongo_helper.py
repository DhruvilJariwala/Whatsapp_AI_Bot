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