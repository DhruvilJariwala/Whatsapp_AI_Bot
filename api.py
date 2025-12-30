from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import hashlib
import hmac
import os
import json

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

@app.post("/webhook")
async def incoming_msg(request: Request):
    await verify_signature(request)

    payload = await request.json()

    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    sender = message["from"]
    text = message["text"]["body"]
    print(f"Sender: {sender}\n")
    print(f"Message: {text}\n")
    

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
        raise PlainTextResponse(content="Signature Invalid",status_code=403)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("api:app", host="localhost", port=5000, reload=True)