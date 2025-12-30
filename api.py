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
def incoming_msg(request: Request):
    print("Message Recieved")
    params=request.query_params
    payload=params.get("JSON_PAYLOAD")
    key=os.getenv("ACCESS_TOKEN")
    hash_value=params.get("SHA256_PAYLOAD_HASH")
    payloadb=json.dumps(payload)
 
    key=key.encode("utf-8")
    payloadb=payloadb.encode("utf-8")
    hmac_hash=hmac.new(key,msg=payloadb,digestmod=hashlib.sha256).hexdigest()

    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    sender = message["from"]
    text = message["text"]["body"]
    print(f"Sender: {sender}\n")
    print(f"Message: {text}\n")

    valid=hmac.compare_digest(hmac_hash,hash_value)

    if(valid):
        return PlainTextResponse(content="Message is Valid",status_code=200)
    else:
        return PlainTextResponse(content="Message is Invalid",status_code=400)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("api:app", host="localhost", port=5000, reload=True)