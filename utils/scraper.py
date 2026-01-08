import os
os.environ["USER_AGENT"] = "Mozilla/5.0 (compatible; LangChainBot/1.0)"

from langchain_community.document_loaders import WebBaseLoader
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

BLOCKED_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".webp", ".zip", ".rar", ".exe", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx", ".mp3", ".mp4",
    ".avi", ".mov", ".wmv", ".css",".js")


MAX_PAGES_TO_CRAWL = 20

def is_file_url(url)->bool:
    path=urlparse(url).path.lower()
    return path.endswith(BLOCKED_EXTENSIONS)

def is_valid(url,domain)->bool:
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme) and parsed.netloc == domain

def extract_endpoints(url,domain_name=None,internal_urls=None)-> list:

    if internal_urls is None:
        internal_urls= set()
    if domain_name is None:
        domain_name=urlparse(url).netloc
    
    if len(internal_urls) >= MAX_PAGES_TO_CRAWL:
        return
    if url in internal_urls:
        return
    internal_urls.add(url)
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, "html.parser")
        
        for link_tag in soup.find_all("a", href=True):
            href = link_tag.get("href")
            full_url = urljoin(url, href)
            if is_valid(full_url,domain_name) and not is_file_url(url) and full_url not in internal_urls:
                extract_endpoints(full_url,internal_urls=internal_urls,domain_name=domain_name)

    except requests.exceptions.RequestException as e:
        internal_urls.remove(url)
    except Exception as e:
        print(f"An unhandled exception occurred: {e}")
    return list(internal_urls)

def scrap(url:list)->list:
    scrapped_data=[]
    loader=WebBaseLoader(url)
    docs=loader.load()
    for i in range(0,len(docs)):
        data=(docs)[i].page_content.replace("\n","").replace("\r","").replace("  "," ")
        scrapped_data.append(data)
    return scrapped_data

def web_scraper(url:str)->str:
    urls=extract_endpoints(url=url,domain_name=urlparse(url=url).netloc)
    scrap_data=scrap(url=urls)
    data="".join(scrap_data)
    data = re.sub(r'\s+', ' ', data)
    return data.strip()