from fastapi import FastAPI, HTTPException, File, UploadFile,Form,Request,Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse,JSONResponse
import hashlib
import hmac
import os
import json
from collections import deque
import datetime
import copy
import threading
import queue
import requests
from dotenv import load_dotenv

from utils.llms import get_llm,llm_with_tool
from utils.milvs_services import insert,search
from utils.helper import check_state,check_history,initial_history,append_history,push_to_mongo,get_counter,change_state,msg_send
from utils.prompt import response_prompt,tool_prompt
from utils.tool import switch_state

load_dotenv()
app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )

@app.get("/webhook")
def verify(request: Request):
    params = request.query_params
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
    if (params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN):
        print("WEBHOOK VERIFIED")
        return PlainTextResponse(content=params.get("hub.challenge"),status_code=200)
    
    return PlainTextResponse(content="Verification failed", status_code=403)

@app.post("/upload")
async def ask(pnumber: str = Form(...),file: UploadFile = File(...)):
    file_name = file.filename
    allowed_extensions = ["pdf"]
    file_extension = file_name.split(".")[-1]
    f_name = file_name.split(".")[0]    
    print(f"File Extension: {file_extension}")
    if file_extension not in allowed_extensions:
        return JSONResponse(content="Unsupported file format!!!", status_code=400)
    response = insert(pnumber=pnumber,file_name=f_name, file_type=file_extension, file=file)
    if response:
        return JSONResponse(content="success", status_code=200)
    else:
        raise HTTPException(detail="There was an error inserting Data", status_code=400)

@app.post("/webhook")
async def incoming_msg(request: Request):
    await verify_signature(request)

    payload = await request.json()
    print(payload)
    entry = payload.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    metadata = value.get("metadata", {})
    receiver_number = metadata.get("display_phone_number")
    receiver_number_id = metadata.get("phone_number_id")
    messages = value.get("messages", [{}])
    message = messages[0] if messages else {}
    sender = message.get("from")
    text = (message.get("text", {}).get("body"))
    print(f"Sender: {sender}\n")
    print(f"Message: {text}\n")
    if not sender or not text:
        return PlainTextResponse("Invalid Sender and Message Value",status_code=403)
    # switch_tool=llm_with_tool(switch_state) 
    # sprompt=tool_prompt(text)
    # switch_prompt=[{"role":"user","content":sprompt}]
    # switch_res=switch_tool.invoke(switch_prompt)
    # if(switch_res.tool_calls):
    #     if(switch_res.tool_calls[0]['name']=="switch_state"):
    #         change_state(reciever_number+"_@_"+sender)
    status=check_state(f"{receiver_number}_@_{sender}")
    if status=="AI":
        ask_ai(receiver_number,query=text,sender=sender,reciver_id=receiver_number_id)
    # else:
        # human()
    return PlainTextResponse(status_code=200)


async def verify_signature(request: Request):
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature:
        return PlainTextResponse(content="Signature Invalid",status_code=403)

    received_hash = signature.replace("sha256=", "")

    body = await request.body()

    expected_hash = hmac.new(
        key=os.getenv("ACCESS_TOKEN").encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return PlainTextResponse(content="Signature Invalid",status_code=403)

mongo_queue = queue.Queue()

def mongo_worker():
    while True:
        history, receiver = mongo_queue.get()
        try:
            push_to_mongo(history, receiver)
        finally:
            mongo_queue.task_done()

threading.Thread(target=mongo_worker, daemon=True).start()

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