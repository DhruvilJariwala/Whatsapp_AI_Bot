from fastapi.responses import JSONResponse
from fastapi import HTTPException,Request
import datetime
from services.db.milvs_services import insert_doc,insert_url
import hashlib
import hmac
import os
from dotenv import load_dotenv

load_dotenv()

def upload(number:str,file=None,url=None):
    if file and not url:
        file_name = file.filename
        allowed_extensions = ["pdf"]
        file_extension = file_name.split(".")[-1]
        f_name = file_name.split(".")[0]    
        print(f"File Extension: {file_extension}")
        if file_extension not in allowed_extensions:
            return JSONResponse(content="Unsupported file format!!!", status_code=400)
        response = insert_doc(pnumber=number,file_name=f_name, file_type=file_extension, file=file)
        if response:
            return JSONResponse(content="success", status_code=200)
        else:
            raise HTTPException(detail="There was an error inserting Data", status_code=400)
    elif url and not file:
        response=insert_url(pnumber=number,url=url)
        if response:
            return JSONResponse(content="success", status_code=200)
        else:
            raise HTTPException(detail="There was an error inserting Data", status_code=400)
    else:
        file_name = file.filename
        allowed_extensions = ["pdf"]
        file_extension = file_name.split(".")[-1]
        f_name = file_name.split(".")[0]    
        print(f"File Extension: {file_extension}")
        if file_extension not in allowed_extensions:
            return JSONResponse(content="Unsupported file format!!!", status_code=400)
        doc_response = insert_doc(pnumber=number,file_name=f_name, file_type=file_extension, file=file)
        url_response= insert_url(pnumber=number,url=url)
        if doc_response and url_response:
            return JSONResponse(content="success", status_code=200)
        else:
            return HTTPException(detail="There was an error inserting Data", status_code=400)
        
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
    timestamp=statuses.get("timestamp")
    if timestamp:
        date=datetime.datetime.fromtimestamp(int(timestamp))
    else:
        date=None
    return [receiver_number,receiver_number_id,sender,text,status,status_reciepent,date]


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
    

def msg_send(sender:str,response:str):
    return {
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": sender,
  "type": "text",
  "text": {
    "body": response
  }
}