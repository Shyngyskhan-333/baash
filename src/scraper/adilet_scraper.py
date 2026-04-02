"""
Парсер НПА с портала Әділет (adilet.zan.kz).
Иерархический чанкинг и сохранение в строгом JSON-формате.
"""
import asyncio
import json
import os
import re
from pathlib import Path

import aiohttp
import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

MAX_CONCURRENT = int(os.environ.get("ADILET_MAX_CONCURRENT", "30"))
FETCH_RETRIES = 5

session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))
session.headers.update(HEADERS)

RAW_DIR = Path("data/raw")
PARSED_DIR = Path("data/parsed")
RAW_DIR.mkdir(parents=True, exist_ok=True)
PARSED_DIR.mkdir(parents=True, exist_ok=True)

HEADER_START = re.compile(r"^(?:Статья|Глава|Параграф)\s*[\d\.\-]+", re.UNICODE)
HEADER_LINE = re.compile(
    r"(?m)^\s*((?:Статья|Глава|Параграф)\s*[\d\.\-]+[^\n]*)",
    re.UNICODE,
)

DOM_MIN_ARTICLES = 3

def _write_raw_cache(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def fetch_html(doc_id: str) -> str:
    cache = RAW_DIR / f"{doc_id}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    url = f"https://adilet.zan.kz/rus/docs/{doc_id}"
    resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
    resp.raise_for_status()
    _write_raw_cache(cache, resp.text)
    return resp.text

async def fetch_html_async(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    doc_id: str,
) -> str:
    cache = RAW_DIR / f"{doc_id}.html"
    async with semaphore:
        if cache.exists():
            return await asyncio.to_thread(cache.read_text, encoding="utf-8")
        url = f"https://adilet.zan.kz/rus/docs/{doc_id}"
        last_exc = None
        for attempt in range(FETCH_RETRIES):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as resp:
                    resp.raise_for_status()
                    text = await resp.text()
                await asyncio.to_thread(_write_raw_cache, cache, text)
                return text
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exc = e
                await asyncio.sleep(0.5 * (2**attempt))
        raise last_exc

def extract_references(soup: BeautifulSoup) -> list:
    refs = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"/rus/docs/([A-Z]\d+)", a["href"])
        if m:
            refs.append(m.group(1))
    return list(set(refs))

def _strip_junk(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "meta"]):
        tag.decompose()
    for hidden in soup.find_all(style=re.compile(r"display:\s*none")):
        hidden.decompose()

def chunk_article_text(article_id: str, article_number: str, full_text: str) -> list[dict]:
    """Smart hierarchical chunking: ~200-500 words per chunk."""
    paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 10]
    chunks = []
    current_chunk_text = ""
    current_para_num = ""
    current_subpara_num = ""
    chunk_idx = 0
    
    for p in paragraphs:
        m_para = re.match(r"^(\d+)\.", p)
        if m_para:
            current_para_num = m_para.group(1)
            current_subpara_num = ""
            
        m_sub = re.match(r"^(\d+)\)", p)
        if m_sub:
            current_subpara_num = m_sub.group(1)
            
        if len(current_chunk_text) > 800:
            chunks.append({
                "chunk_id": f"{article_id}_{chunk_idx}",
                "text": f"{article_number}\n{current_chunk_text.strip()}",
                "hierarchy": {
                    "article": article_number,
                    "paragraph": current_para_num,
                    "subparagraph": current_subpara_num
                }
            })
            chunk_idx += 1
            current_chunk_text = p + "\n"
        else:
            current_chunk_text += p + "\n"
            
    if current_chunk_text.strip():
        chunks.append({
            "chunk_id": f"{article_id}_{chunk_idx}",
            "text": f"{article_number}\n{current_chunk_text.strip()}",
            "hierarchy": {
                "article": article_number,
                "paragraph": current_para_num,
                "subparagraph": current_subpara_num
            }
        })
    return chunks

def extract_articles_from_dom(soup: BeautifulSoup, doc_id: str) -> list:
    _strip_junk(soup)
    art_node = soup.find("article") or soup.select_one("div.inner_main") or soup.find("body") or soup
    
    blocks = []
    for el in art_node.find_all(["h2", "h3", "h4", "h5", "p", "table"]):
        if el.name == "p" and el.find_parent("table") is not None:
            continue
        blocks.append(el)

    articles = []
    cur_header = None
    cur_anchor = None
    cur_body = []

    def flush():
        nonlocal cur_header, cur_anchor, cur_body
        if not cur_header:
            cur_body = []
            return
        body_text = "\n".join(p for p in cur_body if p)
        if len(body_text.strip()) > 30:
            aid = f"{doc_id}_art_{cur_anchor}" if cur_anchor else f"{doc_id}_art_{len(articles)}"
            articles.append({
                "article_id": aid,
                "article_number": cur_header[:120],
                "text": f"{cur_header}\n{body_text}",
                "chunks": chunk_article_text(aid, cur_header[:120], body_text)
            })
        cur_header, cur_anchor, cur_body = None, None, []

    for el in blocks:
        raw = el.get_text(separator="\n", strip=True)
        m = HEADER_LINE.search(raw)
        if m and (el.name.startswith("h") or el.name == "p"):
            flush()
            a_tag = el.find("a", attrs={"name": True})
            cur_anchor = str(a_tag["name"]).strip() if a_tag and a_tag.get("name") else None
            cur_header = m.group(1).strip()
            continue

        if cur_header:
            t = el.get_text(separator=" ", strip=True)
            if t and "note" not in (el.get("class") or []):
                cur_body.append(t)

    flush()
    return articles

def _document_from_soup(soup: BeautifulSoup, doc_id: str, doc_url: str) -> dict:
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else doc_id
    date_tag = soup.find(string=re.compile(r"\d{2}\.\d{2}\.\d{4}"))
    date = date_tag.strip() if date_tag else ""
    return {
        "doc_id": doc_id,
        "title": title,
        "date": date,
        "url": doc_url,
        "articles": extract_articles_from_dom(soup, doc_id),
        "references": extract_references(soup),
    }

def parse_document_from_html(html: str, doc_id: str) -> dict | None:
    parsed_path = PARSED_DIR / f"{doc_id}.json"
    try:
        soup = BeautifulSoup(html, "lxml")
        doc_url = f"https://adilet.zan.kz/rus/docs/{doc_id}"
        doc = _document_from_soup(soup, doc_id, doc_url)
        with open(parsed_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"  {doc_id}: '{doc['title'][:55]}' — {len(doc['articles'])} статей")
        return doc
    except Exception as e:
        print(f"  {doc_id}: ОШИБКА — {e}")
        return None

async def parse_batch_async(doc_ids: list) -> list:
    if not doc_ids:
        return []
    connector = aiohttp.TCPConnector(ssl=False, limit=max(MAX_CONCURRENT, 10))
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results = []

    docs_to_fetch = []
    for did in doc_ids:
        if (PARSED_DIR / f"{did}.json").exists():
            with open(PARSED_DIR / f"{did}.json", "r", encoding="utf-8") as f:
                results.append(json.load(f))
        else:
            docs_to_fetch.append(did)

    if docs_to_fetch:
        async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as http_session:
            tasks = [fetch_html_async(http_session, sem, did) for did in docs_to_fetch]
            html_payloads = await asyncio.gather(*tasks, return_exceptions=True)

        for doc_id, item in tqdm(list(zip(docs_to_fetch, html_payloads)), desc="Парсинг НПА"):
            if isinstance(item, Exception):
                print(f"  {doc_id}: ОШИБКА загрузки — {item}")
                continue
            doc = parse_document_from_html(item, doc_id)
            if doc:
                results.append(doc)
    return results

def parse_batch(doc_ids: list) -> list:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # Если event_loop уже запущен (например, внутри асинхронного веб-сервера), 
        # запускаем в отдельном потоке.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, parse_batch_async(doc_ids))
            return future.result()
    else:
        return asyncio.run(parse_batch_async(doc_ids))

async def fetch_by_id(doc_id: str) -> dict | None:
    """Fetch and parse a document by its ID."""
    docs = await parse_batch_async([doc_id])
    return docs[0] if docs else None

async def fetch_by_url(url: str) -> dict | None:
    """Fetch and parse a document by its adilet.zan.kz URL."""
    match = re.search(r"/docs/([A-Z0-9]+)", url)
    if not match:
        raise ValueError(f"Invalid adilet url: {url}")
    return await fetch_by_id(match.group(1))

async def fetch_versions(doc_id: str) -> list[dict]:
    """
    Fetch history of document versions from Adilet archive.
    Returns current and previous versions (at least 2 if available).
    """
    print(f"[SCRAPER] Fetching versions for {doc_id}...")
    current_doc = await fetch_by_id(doc_id)
    if not current_doc:
        return []
        
    versions = [{
        "version_id": f"{doc_id}_current",
        "date": current_doc.get("date", ""),
        "status": "effective",
        "doc": current_doc
    }]
    
    # Try to find archived versions
    archive_url = f"https://adilet.zan.kz/rus/archive/docs/{doc_id}"
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(archive_url, timeout=10, ssl=False) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Find links like /rus/archive/docs/K2000000350/20231201
                    archive_links = re.findall(rf"/rus/archive/docs/{doc_id}/\d+", html)
                    # Sort unique links (latest date first)
                    unique_links = sorted(list(set(archive_links)), reverse=True)
                    
                    if unique_links:
                        # Get the most recent archived version (previous to current)
                        prev_rel_url = unique_links[0]
                        prev_ver_id = prev_rel_url.split("/")[-1]
                        
                        # Full doc_id for archival is usually ID_DATE
                        full_archive_id = f"{doc_id}_{prev_ver_id}"
                        
                        if not (PARSED_DIR / f"{full_archive_id}.json").exists():
                             # Fetch this specific HTML
                             full_url = f"https://adilet.zan.kz{prev_rel_url}"
                             async with session.get(full_url, timeout=15, ssl=False) as a_resp:
                                 if a_resp.status == 200:
                                     a_html = await a_resp.text()
                                     prev_doc = parse_document_from_html(a_html, full_archive_id)
                                     if prev_doc:
                                         versions.append({
                                             "version_id": full_archive_id,
                                             "date": prev_doc.get("date", ""),
                                             "status": "archived",
                                             "doc": prev_doc
                                         })
                        else:
                             with open(PARSED_DIR / f"{full_archive_id}.json", "r", encoding="utf-8") as f:
                                 prev_doc = json.load(f)
                                 versions.append({
                                     "version_id": full_archive_id,
                                     "date": prev_doc.get("date", ""),
                                     "status": "archived",
                                     "doc": prev_doc
                                 })
    except Exception as e:
        print(f"[SCRAPER] Error fetching archive for {doc_id}: {e}")
        
    return versions

if __name__ == "__main__":
    SAMPLE_DOC_IDS = ["K1500000377"]
    docs = parse_batch(SAMPLE_DOC_IDS)
    print(f"Успешно спарсено: {len(docs)} документов.")
