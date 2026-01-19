from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    return ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model=os.getenv("GROQ_MODEL_NAME"), temperature=0, max_tokens=None)


def llm_with_tool(*args):
    llm=get_llm()
    tools=list(args)
    return llm.bind_tools(tools, tool_choice="auto")
