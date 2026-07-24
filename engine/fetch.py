"""각 소스 페이지를 fetch하고, 새 게시글 링크를 state/<id>.json에 기록.

전략:
  - requests로 HTML 가져오기 (UA 위장)
  - BeautifulSoup으로 <a> 추출, link_filter 정규식 매칭
  - 제목은 anchor text (트림). 빈 텍스트는 제외.
  - URL은 절대경로로 정규화
  - state JSON과 diff → 신규에는 first_seen=오늘
  - 100개까지 keep (오래된 항목은 truncate)

JS 렌더 사이트는 link이 거의 안 잡힘 → render.py에서 "fetch 결과 없음" 표시.
"""
from __future__ import annotations
import json, re, sys, time, os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from sources import SOURCES
from parsers import kiri as kiri_parser
from parsers import kif as kif_parser

PARSERS = {
    "kiri": kiri_parser,
    "kif": kif_parser,
}

ROOT = Path(__file__).parent
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "ko,en;q=0.8"}
TIMEOUT = 20
MAX_KEEP = 100


def load_state(sid: str) -> dict:
    p = STATE_DIR / f"{sid}.json"
    if not p.exists():
        return {"id": sid, "last_fetch": None, "last_status": None, "items": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(sid: str, state: dict) -> None:
    p = STATE_DIR / f"{sid}.json"
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_url(base: str, href: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("#", "javascript:", "mailto:", "tel:")):
        return None
    return urljoin(base, href)


def extract_links(html: str, base_url: str, link_filter: str | None) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    pat = re.compile(link_filter) if link_filter else None
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        url = normalize_url(base_url, a["href"])
        if not url:
            continue
        title = " ".join(a.get_text(strip=True).split())
        if not title or len(title) < 4:
            continue
        if pat and not pat.search(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({"title": title[:200], "url": url})
    return out


def fetch_with_parser(src: dict, parser) -> dict:
    """전용 파서가 있는 소스. items의 unique key는 doc_id.
    body_text(PDF 추출)가 없는 항목은 다운+추출 후 채움.
    """
    import pdf_extract  # lazy
    sid = src["id"]
    state = load_state(sid)
    existing = {it["doc_id"]: it for it in state.get("items", []) if "doc_id" in it}
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = now_iso[:10]

    items, statuses = parser.fetch_all()
    new_count = 0
    for it in items:
        if it["doc_id"] not in existing:
            it["first_seen"] = today
            existing[it["doc_id"]] = it
            new_count += 1
        else:
            prev = existing[it["doc_id"]]
            it["first_seen"] = prev.get("first_seen", today)
            # 기존 body_text 보존 (재추출 피함)
            if prev.get("body_text") and not it.get("body_text"):
                it["body_text"] = prev["body_text"]
            existing[it["doc_id"]] = it

    # PDF URL이 있는 항목만 본문 추출 (KIF는 PDF 직링크 없음 → skip)
    pdf_status: list[str] = []
    extracted = skipped = failed = no_pdf = 0
    for it in existing.values():
        if it.get("body_text"):
            skipped += 1
            continue
        url = it.get("download_url") or ""
        if not re.search(r"\.pdf(\?|$)|downloadFile", url, re.I):
            no_pdf += 1
            continue
        text = pdf_extract.extract_for_item(it, max_pages=15)
        if text:
            it["body_text"] = text
            extracted += 1
        else:
            it["body_text"] = ""
            failed += 1
    pdf_status.append(
        f"pdf extract: {extracted} new / {skipped} cached / {failed} failed / {no_pdf} skip(no pdf url)"
    )
    statuses.extend(pdf_status)

    merged = list(existing.values())
    merged.sort(key=lambda x: (x.get("pub_date") or "0000-00", x.get("first_seen", "")), reverse=True)
    merged = merged[:MAX_KEEP]

    state["last_fetch"] = now_iso
    state["last_status"] = statuses
    state["items"] = merged
    state["new_count_this_run"] = new_count
    save_state(sid, state)
    return state


def fetch_source(src: dict) -> dict:
    # 전용 파서가 있으면 거기로 dispatch
    parser_name = src.get("parser")
    if parser_name:
        parser = PARSERS.get(parser_name)
        if parser is None:
            raise ValueError(f"unknown parser: {parser_name}")
        return fetch_with_parser(src, parser)

    # 이하 generic fetcher
    sid = src["id"]
    state = load_state(sid)
    existing = {it["url"]: it for it in state.get("items", []) if "url" in it}
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = now_iso[:10]

    all_new = []
    statuses = []
    for url in src["urls"]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            statuses.append(f"{url} → {r.status_code} ({len(r.content)} bytes)")
            if r.status_code != 200:
                continue
            items = extract_links(r.text, url, src.get("link_filter"))
            for it in items:
                if it["url"] not in existing:
                    it["first_seen"] = today
                    existing[it["url"]] = it
                    all_new.append(it)
        except Exception as e:
            statuses.append(f"{url} → ERROR: {e}")
        time.sleep(0.5)  # polite

    merged = list(existing.values())
    merged.sort(key=lambda x: x.get("first_seen", "1970-01-01"), reverse=True)
    merged = merged[:MAX_KEEP]

    state["last_fetch"] = now_iso
    state["last_status"] = statuses
    state["items"] = merged
    state["new_count_this_run"] = len(all_new)
    save_state(sid, state)
    return state


def main():
    only = set(sys.argv[1:])  # python fetch.py kiri kif  → 선택 fetch
    for src in SOURCES:
        if only and src["id"] not in only:
            continue
        print(f"[fetch] {src['id']:18s} ({src['name']})")
        st = fetch_source(src)
        print(f"        items={len(st['items'])}  new={st.get('new_count_this_run',0)}")
        for s in st["last_status"]:
            print(f"        {s}")


if __name__ == "__main__":
    main()
