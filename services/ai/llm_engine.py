from collections import deque
import datetime
import os
import json
from dotenv import load_dotenv
import requests
import copy
import queue
import asyncio

from services.db.redis_helper import check_history,get_counter,append_history,change_state,check_state,send_history
from services.db.mongo_helper import push_to_mongo
from utils.helper import msg_send
from services.ai.llms import get_llm,llm_with_tool
from services.db.milvs_services import search
from services.ai.prompt import response_prompt,tool_prompt
from services.ai.tool import switch_state,followup_handler

load_dotenv()

mongo_queue = queue.Queue()

def mongo_worker():
    while True:
        history, receiver = mongo_queue.get()
        try:
            push_to_mongo(history, receiver)
        except Exception as e:
            print(f"Mongo worker error: {e}")
        finally:
            mongo_queue.task_done()

ai_queue=queue.Queue()

def ai_worker():
    while True:
        receiver_number, text, sender, receiver_number_id = ai_queue.get()
        try:
            asyncio.run(ask_ai(receiver_number,text,sender,receiver_number_id))
        except Exception as e:
            print(f"AI worker error: {e}")
        finally:
            ai_queue.task_done()

async def ask_ai(reciver:str,query:str,sender:str,reciver_id:str):
    tool_res=tool_calling(query,receiver=reciver,sender=sender,reciver_id=reciver_id)
    if tool_res:
        if tool_res=="Human":
            res=check_history(f"{reciver}_@_{sender}")
            chat_history=json.loads(res)
            counter=int(get_counter(f"{reciver}_@_{sender}"))
            counter+=1
            chat_history.append({"user":query,"timestamp":str(datetime.datetime.now()),"SenderID":sender,"answeredby":check_state(f"{reciver}_@_{sender}")})
            append_history(f"{reciver}_@_{sender}",chat_history=chat_history,counter=counter)
            await send_history(f"{reciver}_@_{sender}")
            print("Switch to Human")
            return
        else:
            query=tool_res
            print(f"Restructure Query:{query}")
            
    res=check_history(f"{reciver}_@_{sender}")
    chat_history=list()
    llm_history=list()
    if res:
        chat_history=json.loads(res)
        for items in chat_history:
            if "user" in items:
                llm_history.append({"role":"user","content":items["user"]})
            elif "assistant" in items:
                llm_history.append({"role":"assistant","content":items["assistant"]})
    context=search(query)
    prompt=response_prompt(context,query)
    llm_history.append({"role":"user","content":prompt})
    generation = get_llm().invoke(llm_history)
    response = generation.content
    try:
        chat_history.append({"user":query,"timestamp":str(datetime.datetime.now()),"SenderID":sender,"answeredby":check_state(f"{reciver}_@_{sender}")}) 
        res=requests.post(url=f"{os.getenv('BASE_URL')}{reciver_id}/messages",json=msg_send(sender=sender,response=response),headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"
        })
        chat_history.append({"assistant":response,"timestamp":str(datetime.datetime.now()),"SenderID":sender,"answeredby":check_state(f"{reciver}_@_{sender}")})                       
        print("Sucessfully Send")
    except Exception as e:
        print(f"ERROR: {e}")
    chat_history=deque(chat_history,20)
    counter=int(get_counter(f"{reciver}_@_{sender}"))
    counter+=2
    if counter==20:
        mongo_history=copy.deepcopy(chat_history)
        mongo_queue.put((mongo_history,reciver))
        counter=0
    append_history(f"{reciver}_@_{sender}",list(chat_history),counter=counter)

def tool_calling(msg:str,receiver:str,sender:str,reciver_id:str="",toolused:str="Whatsapp"):
    tool=llm_with_tool(followup_handler,switch_state) 
    sprompt=tool_prompt(msg)
    res=check_history(f"{receiver}_@_{sender}")
    if res is None:
        tool_his=[{"role":"user","content":sprompt}]
    else:
        temp=json.loads(res)
        tool_his=[]
        for items in temp:
            if "user" in items:
                tool_his.append({"role":"user","content":items["user"]})
            elif "assistant" in items:
                tool_his.append({"role":"assistant","content":items["assistant"]})
        tool_his.append({"role":"user","content":sprompt})
    tool_res=tool.invoke(tool_his)
    if(tool_res.tool_calls):
        if(tool_res.tool_calls[0]['name']=="switch_state"):
            change_state(f"{receiver}_@_{sender}")
            if toolused=="Whatsapp":
                try:
                    res = requests.post(url=f"{os.getenv('BASE_URL')}{reciver_id}/messages",json=msg_send(sender=sender,response="A Support representive will soon get back to you"),headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"})
                except Exception as e:
                    print(f"Error sending default Human msg: {e}")
                return "Human"
            else:
                return "A Support representive will soon get back to you"
        elif(tool_res.tool_calls[0]['name']=="followup_handler"):
            text=tool_res.tool_calls[0]['args']['query']
            return text
    return None

async def chatbot_ai(org_number:str,deviceid:str,query:str):
    tool_res=tool_calling(query,receiver=org_number,sender=deviceid,toolused="Chatbot")
    if tool_res:
        if tool_res=="A Support representive will soon get back to you":
            res=check_history(f"{org_number}_@_{deviceid}")
            chat_history=json.loads(res)
            counter=int(get_counter(f"{org_number}_@_{deviceid}"))
            counter+=1
            chat_history.append({"user":query,"timestamp":str(datetime.datetime.now()),"SenderID":deviceid,"answeredby":check_state(f"{org_number}_@_{deviceid}")})
            append_history(f"{org_number}_@_{deviceid}",chat_history=chat_history,counter=counter)
            await send_history(f"{org_number}_@_{deviceid}")
            print("Switch to Human")
            return tool_res
        else:
            query=tool_res
            print(f"Restructure Query:{query}")
    res=check_history(f"{org_number}_@_{deviceid}")
    chat_history=list()
    llm_history=list()
    if res:
        chat_history=json.loads(res)
        for items in chat_history:
            if "user" in items:
                llm_history.append({"role":"user","content":items["user"]})
            elif "assistant" in items:
                llm_history.append({"role":"assistant","content":items["assistant"]})
    context=search(query)
    prompt=response_prompt(context,query)
    llm_history.append({"role":"user","content":prompt})
    generation = get_llm().invoke(llm_history)
    response = generation.content
    chat_history.append({"user":query,"timestamp":str(datetime.datetime.now()),"SenderID":deviceid,"answeredby":check_state(f"{org_number}_@_{deviceid}")}) 
    chat_history.append({"assistant":response,"timestamp":str(datetime.datetime.now()),"SenderID":deviceid,"answeredby":check_state(f"{org_number}_@_{deviceid}")})                       
    chat_history=deque(chat_history,20)
    counter=int(get_counter(f"{org_number}_@_{deviceid}"))
    counter+=2
    if counter==20:
        mongo_history=copy.deepcopy(chat_history)
        mongo_queue.put((mongo_history,org_number))
        counter=0
    append_history(f"{org_number}_@_{deviceid}",list(chat_history),counter=counter)
    return response