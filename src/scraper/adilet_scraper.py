
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

MAX_CONCURRENT = int(os.environ.get("ADILET_MAX_CONCURRENT", "30"))
FETCH_RETRIES = 5

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

def _resolve_alt_id(doc_id: str) -> str | None:
    if doc_id.endswith("_"):
        return None
    return f"{doc_id}_"

def fetch_html(doc_id: str) -> tuple[str, str]:
    cache = RAW_DIR / f"{doc_id}.html"
    if cache.exists():
        return doc_id, cache.read_text(encoding="utf-8")
    url = f"https://adilet.zan.kz/rus/docs/{doc_id}"

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    with requests.Session() as session:
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        resp = session.get(url, headers=HEADERS, timeout=20, verify=False)
        if resp.status_code == 404:
            alt_id = _resolve_alt_id(doc_id)
            if alt_id:
                alt_cache = RAW_DIR / f"{alt_id}.html"
                if alt_cache.exists():
                    return alt_id, alt_cache.read_text(encoding="utf-8")
                alt_url = f"https://adilet.zan.kz/rus/docs/{alt_id}"
                alt_resp = session.get(alt_url, headers=HEADERS, timeout=20, verify=False)
                if alt_resp.status_code == 200:
                    _write_raw_cache(alt_cache, alt_resp.text)
                    return alt_id, alt_resp.text
        resp.raise_for_status()
        _write_raw_cache(cache, resp.text)
    return doc_id, resp.text

async def fetch_html_async(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    doc_id: str,
) -> tuple[str, str]:
    cache = RAW_DIR / f"{doc_id}.html"
    async with semaphore:
        if cache.exists():
            text = await asyncio.to_thread(cache.read_text, encoding="utf-8")
            return doc_id, text
        url = f"https://adilet.zan.kz/rus/docs/{doc_id}"
        last_exc = None
        for attempt in range(FETCH_RETRIES):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as resp:
                    if resp.status == 404:
                        alt_id = _resolve_alt_id(doc_id)
                        if alt_id:
                            alt_cache = RAW_DIR / f"{alt_id}.html"
                            if alt_cache.exists():
                                alt_text = await asyncio.to_thread(alt_cache.read_text, encoding="utf-8")
                                return alt_id, alt_text
                            alt_url = f"https://adilet.zan.kz/rus/docs/{alt_id}"
                            async with session.get(alt_url, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as alt_resp:
                                if alt_resp.status == 200:
                                    alt_text = await alt_resp.text()
                                    await asyncio.to_thread(_write_raw_cache, alt_cache, alt_text)
                                    return alt_id, alt_text
                    resp.raise_for_status()
                    text = await resp.text()
                await asyncio.to_thread(_write_raw_cache, cache, text)
                return doc_id, text
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exc = e
                await asyncio.sleep(0.5 * (2**attempt))
        raise last_exc

def extract_references(soup: BeautifulSoup) -> list:
    refs = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"/rus/docs/([A-Z]\d+_?)", a["href"])
        if m:
            refs.append(m.group(1))
    return list(set(refs))

def _strip_junk(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "meta"]):
        tag.decompose()
    for hidden in soup.find_all(style=re.compile(r"display:\s*none")):
        hidden.decompose()

def chunk_article_text(article_id: str, article_number: str, full_text: str) -> list[dict]:

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

def extract_fallback_article(soup: BeautifulSoup, doc_id: str) -> list:
    _strip_junk(soup)
    art_node = soup.find("article") or soup.select_one("div.inner_main") or soup.find("body") or soup
    text = art_node.get_text(separator="\n", strip=True)
    paragraphs = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
    if not paragraphs:
        return []

    body_text = "\n".join(paragraphs)
    article_id = f"{doc_id}_art_0"
    return [{
        "article_id": article_id,
        "article_number": "Основной текст",
        "text": body_text,
        "chunks": chunk_article_text(article_id, "Основной текст", body_text),
    }]

def _document_from_soup(soup: BeautifulSoup, doc_id: str, doc_url: str) -> dict:
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else doc_id
    date_tag = soup.find(string=re.compile(r"\d{2}\.\d{2}\.\d{4}"))
    date = date_tag.strip() if date_tag else ""
    articles = extract_articles_from_dom(soup, doc_id)
    if not articles:
        articles = extract_fallback_article(soup, doc_id)
    return {
        "doc_id": doc_id,
        "title": title,
        "date": date,
        "url": doc_url,
        "articles": articles,
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
        parsed_path = PARSED_DIR / f"{did}.json"
        if parsed_path.exists():
            with open(parsed_path, "r", encoding="utf-8") as f:
                results.append(json.load(f))
            continue
        alt_id = _resolve_alt_id(did)
        if alt_id:
            alt_path = PARSED_DIR / f"{alt_id}.json"
            if alt_path.exists():
                with open(alt_path, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
                continue
        docs_to_fetch.append(did)

    if docs_to_fetch:
        async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as http_session:
            tasks = [fetch_html_async(http_session, sem, did) for did in docs_to_fetch]
            html_payloads = await asyncio.gather(*tasks, return_exceptions=True)

        for doc_id, item in tqdm(list(zip(docs_to_fetch, html_payloads)), desc="Парсинг НПА"):
            if isinstance(item, Exception):
                print(f"  {doc_id}: ОШИБКА загрузки — {item}")
                continue
            doc_id_used, html = item
            doc = parse_document_from_html(html, doc_id_used)
            if doc:
                results.append(doc)
    return results

def parse_batch(doc_ids: list) -> list:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, parse_batch_async(doc_ids))
            return future.result()
    else:
        return asyncio.run(parse_batch_async(doc_ids))

async def fetch_by_id(doc_id: str) -> dict | None:

    docs = await parse_batch_async([doc_id])
    return docs[0] if docs else None

async def fetch_by_url(url: str) -> dict | None:
    archive_match = re.search(r"/archive/docs/([A-Z]\d+_?)/(\d{2}\.\d{2}\.\d{4})", url, re.IGNORECASE)
    if archive_match:
        base_doc_id = archive_match.group(1).upper()
        archive_date = archive_match.group(2)
        version_id = f"{base_doc_id}_{archive_date}"
        parsed_path = PARSED_DIR / f"{version_id}.json"
        if parsed_path.exists():
            with open(parsed_path, "r", encoding="utf-8") as f:
                return json.load(f)

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as resp:
                resp.raise_for_status()
                html = await resp.text()

        return parse_document_from_html(html, version_id)

    doc_match = re.search(r"/docs/([A-Z]\d+_?)", url, re.IGNORECASE)
    if doc_match:
        return await fetch_by_id(doc_match.group(1).upper())

    raise ValueError(f"Invalid adilet url: {url}")

async def fetch_versions(doc_id: str) -> list[dict]:
    safe_doc_id = doc_id.strip().upper()
    print(f"[SCRAPER] Fetching versions for {safe_doc_id}...")
    current_doc = await fetch_by_id(safe_doc_id)
    if not current_doc:
        return []

    versions = [{
        "version_id": f"{safe_doc_id}_current",
        "date": current_doc.get("date", ""),
        "status": "current",
        "doc": current_doc
    }]

    history_cache = RAW_DIR / f"{safe_doc_id}_history.html"
    history_url = f"https://adilet.zan.kz/rus/docs/{safe_doc_id}/history"
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            if history_cache.exists():
                html = history_cache.read_text(encoding="utf-8")
            else:
                async with session.get(history_url, timeout=10, ssl=False) as resp:
                    resp.raise_for_status()
                    html = await resp.text()
                _write_raw_cache(history_cache, html)

            archive_matches = re.findall(
                rf"/rus/archive/docs/{re.escape(safe_doc_id)}/(\d{{2}}\.\d{{2}}\.\d{{4}})",
                html,
                re.IGNORECASE,
            )
            archive_dates = sorted(
                set(archive_matches),
                key=lambda value: tuple(int(part) for part in value.split(".")[::-1]),
                reverse=True,
            )

            for archive_date in archive_dates:
                version_id = f"{safe_doc_id}_{archive_date}"
                parsed_path = PARSED_DIR / f"{version_id}.json"
                doc = None

                if parsed_path.exists():
                    with open(parsed_path, "r", encoding="utf-8") as f:
                        doc = json.load(f)

                versions.append({
                    "version_id": version_id,
                    "date": doc.get("date", archive_date) if doc else archive_date,
                    "status": "archived",
                    "doc": doc,
                })
    except Exception as e:
        print(f"[SCRAPER] Error fetching archive for {safe_doc_id}: {e}")

    return versions

if __name__ == "__main__":
    SAMPLE_DOC_IDS = ["K1500000377"]
    docs = parse_batch(SAMPLE_DOC_IDS)
    print(f"Успешно спарсено: {len(docs)} документов.")