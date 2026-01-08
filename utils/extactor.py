from fastapi.responses import JSONResponse
from io import BytesIO
import re
import pdfplumber

def file_extractor(file,type:str):
        if type=="pdf":
            file_bytes = file.file.read()
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return data_extractor(text=text)
        else:
            raise JSONResponse(content="Unsupported file format!!!", status_code=400)
        
def data_extractor(text:str):
    max_chunk_size=2000
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text) 
    chunks = []
    
    temp_text=""
    for sentence in sentences:
        if len(temp_text) + len(sentence) > max_chunk_size:
            if temp_text:  
                chunks.append(temp_text.strip())
            temp_text = sentence 
        else:
            temp_text += " " + sentence if temp_text else sentence

    if temp_text:
        chunks.append(temp_text.strip())

    return chunks