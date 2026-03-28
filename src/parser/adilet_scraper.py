"""
Парсер НПА с портала Әділет (adilet.zan.kz).

Пакетная загрузка: aiohttp + asyncio.Semaphore (переменная ADILET_MAX_CONCURRENT, по умолчанию 30).
Одиночный parse_document: синхронный requests без искусственной задержки.
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

# adilet.zan.kz uses a certificate that Windows cannot verify (missing root CA).
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

# Заголовок нормы: Статья / Глава / Параграф + номер
HEADER_START = re.compile(r"^(?:Статья|Глава|Параграф)\s*[\d\.\-]+", re.UNICODE)
HEADER_LINE = re.compile(
    r"(?m)^\s*((?:Статья|Глава|Параграф)\s*[\d\.\-]+[^\n]*)",
    re.UNICODE,
)

DOM_MIN_ARTICLES = 3


def _write_raw_cache(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def fetch_html(doc_id: str) -> str:
    """Синхронная загрузка одного документа (кэш raw → HTTP)."""
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
    """Параллельная загрузка: кэш или GET с ретраями; ssl=False как у requests verify=False."""
    cache = RAW_DIR / f"{doc_id}.html"
    async with semaphore:
        if cache.exists():
            return await asyncio.to_thread(cache.read_text, encoding="utf-8")
        url = f"https://adilet.zan.kz/rus/docs/{doc_id}"
        last_exc: Exception | None = None
        for attempt in range(FETCH_RETRIES):
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=20),
                    ssl=False,
                ) as resp:
                    resp.raise_for_status()
                    text = await resp.text()
                await asyncio.to_thread(_write_raw_cache, cache, text)
                return text
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exc = e
                await asyncio.sleep(0.5 * (2**attempt))
        assert last_exc is not None
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


def _content_root(soup: BeautifulSoup):
    art = soup.find("article")
    if art:
        return art
    inner = soup.select_one("div.inner_main")
    if inner:
        return inner
    return soup.find("body") or soup


def _is_centered_p(p) -> bool:
    al = (p.get("align") or "").lower()
    if al == "center":
        return True
    st = p.get("style") or ""
    return bool(re.search(r"text-align\s*:\s*center", st, re.I))


def _is_note_block(node) -> bool:
    if node.name != "p":
        return False
    classes = node.get("class") or []
    return "note" in classes


def _anchor_name(node) -> str | None:
    a = node.find("a", attrs={"name": True})
    if a and a.get("name"):
        return str(a["name"]).strip()
    return None


def _parse_header_from_node(el):
    """Возвращает (header_text, anchor) или None."""
    if el.name in ("h2", "h3", "h4", "h5"):
        raw = el.get_text(separator="\n", strip=True)
        m = HEADER_LINE.search(raw)
        if m:
            return (m.group(1).strip(), _anchor_name(el))
        return None

    if el.name == "p":
        for sub in ("b", "strong"):
            b = el.find(sub, recursive=False)
            if b is not None:
                t = re.sub(r"\s+", " ", b.get_text(separator=" ", strip=True))
                if HEADER_START.match(t):
                    an = _anchor_name(b) or _anchor_name(el)
                    return (t, an)
        if _is_centered_p(el):
            raw = re.sub(r"\s+", " ", el.get_text(separator=" ", strip=True))
            if HEADER_START.match(raw):
                return (raw[:500].strip(), _anchor_name(el))
            m = HEADER_LINE.search(raw)
            if m:
                line = m.group(1).strip()
                if HEADER_START.match(line):
                    return (line, _anchor_name(el))
        return None

    return None


def _block_text(el) -> str:
    return el.get_text(separator=" ", strip=True)


def _join_body(parts: list[str]) -> str:
    return "\n\n".join(p for p in parts if p)


def extract_articles_from_dom(soup: BeautifulSoup, doc_id: str) -> list:
    """Разбор статей по структуре HTML (<article>, <p><b>Статья…, <h3>Глава…, center)."""
    _strip_junk(soup)
    root = _content_root(soup)
    if not root:
        return []

    blocks = []
    for el in root.find_all(["h2", "h3", "h4", "h5", "p", "table"]):
        if el.name == "p" and el.find_parent("table") is not None:
            continue
        blocks.append(el)

    articles = []
    cur_header = None
    cur_anchor = None
    cur_body: list[str] = []

    def flush():
        nonlocal cur_header, cur_anchor, cur_body
        if not cur_header:
            cur_body = []
            return
        body_text = _join_body(cur_body)
        if len(body_text.strip()) > 30:
            aid = (
                f"{doc_id}_art_{cur_anchor}"
                if cur_anchor
                else f"{doc_id}_art_{len(articles)}"
            )
            articles.append(
                {
                    "id": aid,
                    "doc_id": doc_id,
                    "number": cur_header[:120],
                    "text": f"{cur_header}\n{body_text}",
                }
            )
        cur_header = None
        cur_anchor = None
        cur_body = []

    for el in blocks:
        parsed = _parse_header_from_node(el)
        if parsed:
            flush()
            cur_header, cur_anchor = parsed
            continue
        if _is_note_block(el):
            continue
        if cur_header:
            t = _block_text(el)
            if t:
                cur_body.append(t)

    flush()
    return articles


def clean_html(soup: BeautifulSoup) -> str:
    """Удаляет мусорные теги и нормализует текст для чистого отображения."""
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "meta"]):
        tag.decompose()

    for hidden in soup.find_all(style=re.compile(r"display:\s*none")):
        hidden.decompose()

    for block_tag in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "br"]):
        block_tag.insert_after("\n")

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def extract_articles_regex(soup: BeautifulSoup, doc_id: str) -> list:
    """Fallback: плоский текст + regex по переводам строк."""
    articles = []
    full_text = clean_html(soup)
    pattern = re.compile(
        r"(?P<header>^(?:Статья|Глава|Параграф)\s*[\d\.\-]+.*)\n",
        re.MULTILINE,
    )
    parts = pattern.split(full_text)

    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if len(body) > 30:
            articles.append(
                {
                    "id": f"{doc_id}_re_{i}",
                    "doc_id": doc_id,
                    "number": header[:120],
                    "text": f"{header}\n{body}",
                }
            )
    return articles


def extract_articles_fallback_paragraphs(soup: BeautifulSoup, doc_id: str) -> list:
    """Последний fallback: длинные абзацы."""
    full_text = clean_html(soup)
    paragraphs = [p.strip() for p in full_text.split("\n\n") if len(p.strip()) > 100]
    articles = []
    for i, p in enumerate(paragraphs):
        articles.append(
            {
                "id": f"{doc_id}_p_{i}",
                "doc_id": doc_id,
                "number": f"§{i+1}",
                "text": p,
            }
        )
    return articles


def extract_articles(soup: BeautifulSoup, doc_id: str) -> list:
    html_snapshot = str(soup)
    work = BeautifulSoup(html_snapshot, "lxml")
    articles = extract_articles_from_dom(work, doc_id)
    if len(articles) < DOM_MIN_ARTICLES:
        work2 = BeautifulSoup(html_snapshot, "lxml")
        articles = extract_articles_regex(work2, doc_id)
    if not articles:
        work3 = BeautifulSoup(html_snapshot, "lxml")
        articles = extract_articles_fallback_paragraphs(work3, doc_id)
    return articles


def _document_from_soup(soup: BeautifulSoup, doc_id: str, doc_url: str) -> dict:
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else doc_id
    date_tag = soup.find(string=re.compile(r"\d{2}\.\d{2}\.\d{4}"))
    date = date_tag.strip() if date_tag else ""
    return {
        "id": doc_id,
        "title": title,
        "date": date,
        "url": doc_url,
        "articles": extract_articles(soup, doc_id),
        "references": extract_references(soup),
    }


def parse_document_from_html(html: str, doc_id: str) -> dict | None:
    """Парсинг уже загруженного HTML; пишет data/parsed/{doc_id}.json."""
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


# ─── История документа / предыдущая редакция (archive) ─────────────────────

def fetch_history_html(doc_id: str) -> str:
    """Страница «История изменений»: /rus/docs/{id}/history."""
    cache = RAW_DIR / f"{doc_id}_history.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    url = f"https://adilet.zan.kz/rus/docs/{doc_id}/history"
    resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
    resp.raise_for_status()
    cache.write_text(resp.text, encoding="utf-8")
    return resp.text


def parse_history_archive_links(html: str, doc_id: str) -> list[dict]:
    """
    Ссылки вида /rus/archive/docs/{doc_id}/DD.MM.YYYY, хронология от старой к новой.
    Каждый элемент: url, date_label (DD.MM.YYYY), sort_key (YYYYMMDD).
    """
    soup = BeautifulSoup(html, "lxml")
    pat = re.compile(
        rf"/rus/archive/docs/{re.escape(doc_id)}/(\d{{2}})\.(\d{{2}})\.(\d{{4}})\b"
    )
    by_key: dict[str, dict] = {}
    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        m = pat.search(href)
        if not m:
            continue
        d, mo, y = m.group(1), m.group(2), m.group(3)
        sort_key = f"{y}{mo}{d}"
        date_label = f"{d}.{mo}.{y}"
        full = href if href.startswith("http") else f"https://adilet.zan.kz{href}"
        by_key[sort_key] = {"url": full, "date_label": date_label, "sort_key": sort_key}
    return sorted(by_key.values(), key=lambda r: r["sort_key"])


def get_previous_edition_url(doc_id: str) -> tuple[str | None, str | None]:
    """URL предпоследней редакции и её дата (последняя в таблице = текущая)."""
    try:
        hist_html = fetch_history_html(doc_id)
        rows = parse_history_archive_links(hist_html, doc_id)
        if len(rows) < 2:
            return None, None
        prev = rows[-2]
        return prev["url"], prev["date_label"]
    except Exception:
        return None, None


def _archive_raw_cache_path(doc_id: str, date_label: str) -> Path:
    slug = date_label.replace(".", "_")
    return RAW_DIR / f"archive_{doc_id}_{slug}.html"


def parse_archive_document_from_html(
    html: str,
    logical_id: str,
    base_doc_id: str,
    source_url: str,
    edition_date: str,
) -> dict | None:
    """Парсинг HTML архивной редакции; пишет data/parsed/{logical_id}.json."""
    parsed_path = PARSED_DIR / f"{logical_id}.json"
    try:
        soup = BeautifulSoup(html, "lxml")
        doc = _document_from_soup(soup, logical_id, source_url)
        doc["base_doc_id"] = base_doc_id
        doc["edition_date"] = edition_date
        doc["is_archive_edition"] = True
        with open(parsed_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(
            f"  {logical_id} (архив {edition_date}): '{doc['title'][:45]}' — {len(doc['articles'])} статей"
        )
        return doc
    except Exception as e:
        print(f"  {logical_id}: ОШИБКА архива — {e}")
        return None


def fetch_and_parse_previous_edition(doc_id: str) -> dict | None:
    """
    Находит предпоследнюю редакцию в истории, скачивает archive HTML, парсит в JSON.
    id результата: {doc_id}_prev_{YYYYMMDD}.
    """
    try:
        hist_html = fetch_history_html(doc_id)
        rows = parse_history_archive_links(hist_html, doc_id)
        if len(rows) < 2:
            print(f"  {doc_id}: нет предыдущей редакции в истории (строк: {len(rows)})")
            return None
        prev = rows[-2]
        cache_path = _archive_raw_cache_path(doc_id, prev["date_label"])
        if cache_path.exists():
            html = cache_path.read_text(encoding="utf-8")
        else:
            resp = requests.get(prev["url"], headers=HEADERS, timeout=20, verify=False)
            resp.raise_for_status()
            html = resp.text
            cache_path.write_text(html, encoding="utf-8")
        logical_id = f"{doc_id}_prev_{prev['sort_key']}"
        return parse_archive_document_from_html(
            html, logical_id, doc_id, prev["url"], prev["date_label"]
        )
    except Exception as e:
        print(f"  {doc_id}: ОШИБКА предыдущей редакции — {e}")
        return None


def parse_document(doc_id: str) -> dict | None:
    try:
        html = fetch_html(doc_id)
        return parse_document_from_html(html, doc_id)
    except Exception as e:
        print(f"  {doc_id}: ОШИБКА — {e}")
        return None


async def parse_batch_async(doc_ids: list) -> list:
    """Параллельная загрузка HTML (aiohttp), затем разбор BeautifulSoup в текущем потоке."""
    if not doc_ids:
        return []
    connector = aiohttp.TCPConnector(ssl=False, limit=max(MAX_CONCURRENT, 10))
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results: list = []

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as http_session:
        tasks = [fetch_html_async(http_session, sem, did) for did in doc_ids]
        html_payloads = await asyncio.gather(*tasks, return_exceptions=True)

    for doc_id, item in tqdm(
        list(zip(doc_ids, html_payloads)),
        desc="Парсинг НПА",
        total=len(doc_ids),
    ):
        if isinstance(item, Exception):
            print(f"  {doc_id}: ОШИБКА загрузки — {item}")
            continue
        doc = parse_document_from_html(item, doc_id)
        if doc:
            results.append(doc)
    return results


def parse_batch(doc_ids: list) -> list:
    """Синхронная обёртка над параллельной загрузкой (удобно для Streamlit / CLI)."""
    return asyncio.run(parse_batch_async(doc_ids))


SAMPLE_DOC_IDS = [
    "K1500000377",  # Гражданский процессуальный кодекс 2015
]

if __name__ == "__main__":
    print("Запускаем парсер Адилет...\n")
    docs = parse_batch(SAMPLE_DOC_IDS)
    print(f"\nУспешно: {len(docs)} документов")
    print(f"Статей всего: {sum(len(d['articles']) for d in docs)}")
