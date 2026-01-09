from fastapi import FastAPI, HTTPException, File, UploadFile,Form,Request,Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse,JSONResponse
import hashlib
import hmac
import os
import threading
from dotenv import load_dotenv

from utils.helper import check_state,upload
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
        return PlainTextResponse(status_code=200)
    if not sender or not text:
        print(f"sender:{sender} message:{text}")
        return PlainTextResponse(status_code=200)
    print(payload)
    print(f"sender: {sender} message:{text}")
    state=check_state(f"{receiver_number}_@_{sender}")
    if state=="AI":
        ai_queue.put((receiver_number,text,sender,receiver_number_id))
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
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="localhost", port=5000, reload=True)