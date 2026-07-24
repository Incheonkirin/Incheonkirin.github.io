"""KIRI PDF 다운로드 + PyMuPDF로 본문 텍스트 추출.

캐시: 같은 docId 두 번 안 받게 /tmp/kiri-pdf-cache/ 활용.
state JSON에 추출된 텍스트를 저장하여 fetch 시 변화 없으면 재다운 회피.
"""
from __future__ import annotations
import os, re, sys, hashlib
from pathlib import Path
import requests
import fitz  # PyMuPDF

CACHE_DIR = Path("/tmp/kiri-pdf-cache")
CACHE_DIR.mkdir(exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)"}
TIMEOUT = 30


def _pdf_path(doc_id: str) -> Path:
    return CACHE_DIR / f"kiri-{doc_id}.pdf"


def download_pdf(doc_id: str, url: str) -> Path | None:
    p = _pdf_path(doc_id)
    if p.exists() and p.stat().st_size > 1024:
        return p
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200 or len(r.content) < 1024:
            return None
        # PDF magic
        if not r.content.startswith(b"%PDF"):
            return None
        p.write_bytes(r.content)
        return p
    except Exception:
        return None


# KIRI PDF 첫 페이지 상단에 거의 항상 들어가는 보일러 텍스트
BOILERPLATE_PATTERNS = [
    r"CEO Brief는 보험산업 관련 이슈를 분석하여[^\n]*",
    r"KIRI 리포트는[^\n]*",
    r"본\s*보고서는[^\n]*제공[^\n]*\n",
]


def _clean(text: str) -> str:
    for pat in BOILERPLATE_PATTERNS:
        text = re.sub(pat, "", text)
    # 합쳐진 짧은 줄 정리
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    # 페이지 번호만 있는 줄 제거
    lines = [ln for ln in lines if not re.match(r"^[\-–—\s]*\d{1,3}[\-–—\s]*$", ln)]
    return "\n".join(lines)


def extract_text(pdf_path: Path, max_pages: int | None = None) -> str:
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return ""
    pages = doc[:max_pages] if max_pages else doc
    text_parts = []
    for page in pages:
        text_parts.append(page.get_text())
    raw = "\n".join(text_parts)
    return _clean(raw)


def extract_for_item(item: dict, max_pages: int = 10) -> str:
    """item dict (download_url, doc_id) 받아서 본문 텍스트 반환. 실패 시 빈 문자열."""
    url = item.get("download_url")
    doc_id = item.get("doc_id")
    if not url or not doc_id:
        return ""
    p = download_pdf(doc_id, url)
    if not p:
        return ""
    return extract_text(p, max_pages=max_pages)


if __name__ == "__main__":
    # 단독 테스트
    test_id = sys.argv[1] if len(sys.argv) > 1 else "792889"
    url = f"https://www.kiri.or.kr/report/downloadFile.do?docId={test_id}"
    p = download_pdf(test_id, url)
    print(f"pdf: {p}")
    if p:
        text = extract_text(p, max_pages=10)
        print(f"chars: {len(text)}")
        print(text[:1500])
