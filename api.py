from fastapi import FastAPI, HTTPException, File, UploadFile,Form,Request,Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse,JSONResponse
import hashlib
import hmac
import os
import threading
from dotenv import load_dotenv

from utils.milvs_services import insert
from utils.helper import check_state,change_state
from utils.llm_engine import ask_ai,tool_calling,fetch_data,mongo_worker

load_dotenv()
app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )

threading.Thread(target=mongo_worker, daemon=True).start()

@app.get("/")
def root():
    return JSONResponse(content="Hello", status_code=200)

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
        return PlainTextResponse(status_code=200)
    print(payload)
    print(f"sender: {sender} message:{text}")
    tool_res=tool_calling(text,receiver_number,sender=sender)
    if tool_res:
        text=tool_res
        print(f"Restructure Query:{text}")
    state=check_state(f"{receiver_number}_@_{sender}")
    if state=="AI":
        ask_ai(receiver_number,query=text,sender=sender,reciver_id=receiver_number_id)
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