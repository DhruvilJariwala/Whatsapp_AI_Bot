from fastapi import FastAPI, HTTPException, File, UploadFile,Form,Request,Body,WebSocketDisconnect,WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import hashlib
import hmac
import os
import threading
from dotenv import load_dotenv
import requests
import datetime
import asyncio

from utils.helper import check_state,append_history,get_counter,get_id,upload,msg_send,connected_clients
from utils.llm_engine import fetch_data,mongo_worker,ai_worker,ai_queue

load_dotenv()

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )

threading.Thread(target=mongo_worker, daemon=True).start()
threading.Thread(target=ai_worker, daemon=True).start()

@app.websocket("/ws/messages")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)

    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        connected_clients.remove(ws)

@app.get("/")
def root():
    return JSONResponse(content="Hello", status_code=200)

@app.get("/webhook")
def verify(request: Request):
    params = request.query_params
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
    if (params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN):
        print("WEBHOOK VERIFIED")
        return JSONResponse(content=params.get("hub.challenge"),status_code=200)
    
    return JSONResponse(content="Verification failed", status_code=403)

@app.post("/upload")
async def ask(pnumber: str = Form(...),file: UploadFile |  None = File(None),url: str | None = Form(None)):
    if not file and not url:
        raise HTTPException(status_code=422,detail="Either file or url must be provided (or both).")
    upload(pnumber,file=file,url=url)

@app.post("/webhook")
async def incoming_msg(request: Request):
    await verify_signature(request)

    payload = await request.json()
    data=fetch_data(payload)
    receiver_number=data[0]
    receiver_number_id=data[1]
    sender=data[2]
    text=data[3]
    status=data[4]
    status_recipient_id=data[5]
    date=data[6]
    if status:
        print(f"message status:{status} recipient_id: {status_recipient_id} date: {date}")
        return JSONResponse(content="OK",status_code=200)
    if not sender or not text:
        print(f"sender:{sender} message:{text}")
        return JSONResponse(content="OK",status_code=200)
    print(payload)
    print(f"sender: {sender} message:{text}")
    state=check_state(f"{receiver_number}_@_{sender}",reciever=receiver_number_id)
    if state=="AI":
        ai_queue.put((receiver_number,text,sender,receiver_number_id))
    elif state=="Human":
        history=[]
        history.append({"user":text,"timestamp":str(datetime.datetime.now()),"SenderID":sender,"answeredby":check_state(f"{receiver_number}_@_{sender}")})  
        count=get_counter(f"{receiver_number}_@_{sender}")
        count=int(count)+1
        await append_history(f"{receiver_number}_@_{sender}",chat_history=history,counter=count)
    return JSONResponse(content="OK",status_code=200)

async def verify_signature(request: Request):
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature:
        return JSONResponse(content="Signature Invalid",status_code=403)

    received_hash = signature.replace("sha256=", "")

    body = await request.body()

    expected_hash = hmac.new(
        key=os.getenv("ACCESS_TOKEN").encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return JSONResponse(content="Signature Invalid",status_code=403)

@app.post("/human")
async def human(msg:str=Body(...),receiver_number:str=Body(...),sender:str=Body(...)):
    response=get_id(f"{receiver_number}_@_{sender}")
    history=[]
    history.append({"user":msg,"timestamp":str(datetime.datetime.now()),"SenderID":sender,"answeredby":check_state(f"{receiver_number}_@_{sender}")})  
    count=get_counter(f"{receiver_number}_@_{sender}")
    count=int(count)+1
    try:
        res = requests.post(url=f"{os.getenv('BASE_URL')}{response}/messages",json=msg_send(sender=sender,response=msg),headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"})
        append_history(f"{receiver_number}_@_{sender}",chat_history=history,counter=count)
        return JSONResponse(content="OK",status_code=200)
    except Exception as e:
        print(f"Error sending Human msg {e}")
        return JSONResponse(content="OK",status_code=400)