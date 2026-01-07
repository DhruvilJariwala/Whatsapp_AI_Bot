from collections import deque
import datetime
import os
import json
from dotenv import load_dotenv
import requests
import copy
import queue

from utils.helper import check_history,initial_history,msg_send,get_counter,append_history,push_to_mongo,check_state
from utils.llms import get_llm,llm_with_tool
from utils.milvs_services import search
from utils.prompt import response_prompt,tool_prompt
from utils.tool import switch_state,followup_handler


load_dotenv()


mongo_queue = queue.Queue()

def mongo_worker():
    while True:
        history, receiver = mongo_queue.get()
        try:
            push_to_mongo(history, receiver)
        finally:
            mongo_queue.task_done()


def ask_ai(reciver:str,query:str,sender:str,reciver_id:str):
    res=check_history(f"{reciver}_@_{sender}")
    if res is None:
        context=search(query)
        prompt=response_prompt(context,query)
        chat_history=[{"role":"user","content":prompt}]
        generation = get_llm().invoke(chat_history)
        response = generation.content
        try:
            res=requests.post(os.getenv('BASE_URL')+reciver_id+"/messages",json=msg_send(sender=sender,response=response),headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"
            })
            print(res.json())
            print("Sucessfully Send")
        except Exception as e:
            print(f"ERROR: {e}")
        chat_history.pop()
        chat_history.append({"user":query,"assistant":response,"timestamp":str(datetime.datetime.now()),"SenderID":sender,"answeredby":check_state(f"{reciver}_@_{sender}")})                        
        initial_history(f"{reciver}_@_{sender}",chat_history)
    else:
        history=json.loads(res)
        hist=[]
        for items in history:
            hist.append({"role":"user","content":items["user"]})
            hist.append({"role":"assistant","content":items["assistant"]})
        context=search(query)
        prompt=response_prompt(context,query)
        hist.append({"role":"user","content":prompt})
        generation = get_llm().invoke(hist)
        response = generation.content
        try:
            res=requests.post(url=f"{os.getenv('BASE_URL')}{reciver_id}/messages",json=msg_send(sender=sender,response=response),headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"
            })
            print(res.json())
            print("Sucessfully Send")
        except Exception as e:
            print(f"ERROR: {e}")
        history=deque(history,10)
        history.append({"user":query,"assistant":response,"timestamp":str(datetime.datetime.now()),"SenderID":sender,"answeredby":check_state(f"{reciver}_@_{sender}")})                        
        counter=int(get_counter(f"{reciver}_@_{sender}"))
        counter+=1
        if counter==10:
            mongo_history=copy.deepcopy(history)
            mongo_queue.put((mongo_history,reciver))
            counter=0
        append_history(f"{reciver}_@_{sender}",list(history),counter=counter)

def tool_calling(msg:str,receiver:str,sender:str):
    tool=llm_with_tool(followup_handler) 
    sprompt=tool_prompt(msg)
    res=check_history(f"{receiver}_@_{sender}")
    if res is None:
        tool_his=[{"role":"user","content":sprompt}]
    else:
        temp=json.loads(res)
        tool_his=[]
        for items in temp:
            tool_his.append({"role":"user","content":items["user"]})
            tool_his.append({"role":"assistant","content":items["assistant"]})
        tool_his.append({"role":"user","content":sprompt})
    tool_res=tool.invoke(tool_his)
    if(tool_res.tool_calls):
        if(tool_res.tool_calls[0]['name']=="switch_state"):
            # change_state(f"{receiver_number}_@_{sender}")
            print("Hello")
            return None
        elif(tool_res.tool_calls[0]['name']=="followup_handler"):
            text=tool_res.tool_calls[0]['args']['query']
            return text
    return None

def fetch_data(data):
    entry = data.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    metadata = value.get("metadata", {})
    receiver_number = metadata.get("display_phone_number")
    receiver_number_id = metadata.get("phone_number_id")
    messages = value.get("messages", [{}])
    message = messages[0] if messages else {}
    sender = message.get("from")
    text = (message.get("text", {}).get("body"))
    stats=value.get("statuses", [{}])
    statuses=stats[0] if stats else {}
    status=statuses.get("status")
    status_reciepent=statuses.get("recipient_id")
    return [receiver_number,receiver_number_id,sender,text,status,status_reciepent]