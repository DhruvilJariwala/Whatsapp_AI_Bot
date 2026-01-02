from fastapi import FastAPI, HTTPException, File, UploadFile,Form,Request,Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse,JSONResponse
import hashlib
import hmac
import os
import json
from collections import deque
import datetime

from utils.llms import get_llm
from utils.milvs_services import insert,search
from utils.helper import check_state,check_history,initial_history,append_history,push_to_mongo,get_counter
from utils.prompt import response_prompt

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

    reciever_number=payload["entry"][0]["changes"][0]["value"]["metadata"]["display_phone_number"]
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    sender = message["from"]
    text = message["text"]["body"]
    print(f"Sender: {sender}\n")
    print(f"Message: {text}\n")
    status=check_state(source=sender)
    if status=="AI":
        ask_ai(reciever_number,query=text,sender=sender)
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

def ask_ai(reciver:str,query:str,sender:str):
    res=check_history(sender+"_@_"+reciver)
    if res is None:
        context=search(query)
        prompt=response_prompt(context,query)
        chat_history=[{"role":"user","content":prompt}]
        generation = get_llm().invoke(chat_history)
        response = generation.content
        chat_history.pop()
        chat_history.append({"role":"user","content":query,"timestamp":str(datetime.datetime.now())})                        
        chat_history.append({"role":"assistant","content":response,"timestamp":str(datetime.datetime.now())})
        initial_history(sender+"_@_"+reciver,chat_history)
    else:
        history=json.loads(res)
        keys_to_keep=["role","content"]
        hist=[{key: d[key] for key in keys_to_keep}for d in history]
        context=search(query)
        prompt=response_prompt(context,query)
        hist.append({"role":"user","content":prompt})
        generation = get_llm().invoke(hist)
        response = generation.content
        history=deque(history,20)
        history.append({"role":"user","content":query,"timestamp":str(datetime.datetime.now())})
        history.append({"role":"assistant","content":response,"timestamp":str(datetime.datetime.now())})
        counter=int(get_counter(sender+"_@_"+reciver))
        counter+=2
        if counter==20:
            history.append({"senderID":sender})
            history.append({"answeredby":check_state(sender+"_@_"+reciver)})
            push_to_mongo(history,reciver)
            history.pop()
            history.pop()
            counter=0
        append_history(sender+"_@_"+reciver,list(history),counter=counter)