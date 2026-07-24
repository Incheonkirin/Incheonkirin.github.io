"""KIRI (한국보험연구원) 전용 파서.

reportList.do?catId=<n> 페이지를 fetch. catId 별로 다른 시리즈:
  - 4  : 연구보고서
  - 7  : CEO Report
  - 8  : CEO Brief
  - 25 : 발간 보고서 (정기간행물 통합)

각 카테고리 페이지에는 두 종류의 마크업이 섞여 있다:
  1. 최상단 1개: <div class="report_top"> (강조 노출)
  2. 나머지 N개: <a class="list_cont"> + sibling <div class="list_cont_btnbox">

docId가 안정적 unique key (downloadFile.do?docId=782989).
"""
from __future__ import annotations
import re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE = "https://www.kiri.or.kr"
# (catId, 표시명, list URL 템플릿, max_items 또는 None)
CATEGORIES = [
    (4, "연구보고서", "/report/reportList.do?catId={}", None),
    (7, "CEO Report", "/report/reportList.do?catId={}", None),
    (8, "CEO Brief", "/report/reportList.do?catId={}", None),
    # KIRI 리포트 시리즈 (publication/list.do)
    (28, "포커스", "/publication/list.do?catId={}", None),
    (29, "이슈 분석", "/publication/list.do?catId={}", None),
    (30, "글로벌 이슈", "/publication/list.do?catId={}", 3),  # 최근 3개만
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36",
    "Accept-Language": "ko,en;q=0.8",
}


def _clean_text(node) -> str:
    if not node:
        return ""
    # <p>는 단락 구분으로 변환
    text = node.get_text(separator="\n", strip=True)
    # 빈 줄 정리
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n\n".join(lines)


def _parse_report_top(soup, rt, category: str) -> dict | None:
    """최상단 강조 카드. <p> 3개 (제목/발간일/저자) + a.file 다운로드 + 같은 컨테이너 안 요약."""
    ps = rt.find_all("p")
    if not ps:
        return None
    title = ps[0].get_text(strip=True)
    pub_date = ps[1].get_text(strip=True) if len(ps) >= 2 else ""
    author = ps[2].get_text(strip=True).replace("저자 :", "").strip() if len(ps) >= 3 else ""
    dl = rt.find("a", class_="file")
    download = urljoin(BASE + "/report/", dl["href"]) if dl and dl.get("href") else None
    viewer = rt.find("a", class_="show")
    viewer_url = urljoin(BASE + "/report/", viewer["href"]) if viewer and viewer.get("href") else None
    doc_id = None
    if download:
        m = re.search(r"docId=(\d+)", download)
        if m:
            doc_id = m.group(1)
    if not doc_id or not title:
        return None
    # 요약: report_top 의 형제 div.report_det_summ
    summary = ""
    summ_div = soup.find("div", class_="report_det_summ")
    if summ_div:
        summary = _clean_text(summ_div)
    return {
        "doc_id": doc_id,
        "title": title,
        "pub_date": pub_date,
        "author": author,
        "category": category,
        "download_url": download,
        "viewer_url": viewer_url,
        "summary": summary,
    }


def _parse_list_card(a, category: str) -> dict | None:
    """반복 카드. a.list_cont 안에 h3 제목 + p>span (저자/발간일)."""
    h3 = a.find("h3")
    title = h3.get_text(strip=True) if h3 else ""
    author = pub_date = ""
    p = a.find("p")
    if p:
        for s in p.find_all("span"):
            t = s.get_text(strip=True)
            if t.startswith("저자"):
                author = t.replace("저자 :", "").strip()
            elif re.match(r"^\d{4}-\d{2}", t):
                pub_date = t
    btnbox = a.find_next_sibling("div", class_="list_cont_btnbox")
    doc_id = None
    if btnbox:
        inp = btnbox.find("input", {"name": "docId"})
        if inp:
            doc_id = inp.get("value")
    if not doc_id or not title:
        return None
    # 요약: a.list_cont 의 형제 div.list_cont_det1
    summary = ""
    summ_div = a.find_next_sibling("div", class_="list_cont_det1")
    if summ_div:
        summary = _clean_text(summ_div)
    return {
        "doc_id": doc_id,
        "title": title,
        "pub_date": pub_date,
        "author": author,
        "category": category,
        "download_url": f"{BASE}/report/downloadFile.do?docId={doc_id}",
        "viewer_url": None,
        "summary": summary,
    }


def parse_category_page(html: str, category: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    rt = soup.find("div", class_="report_top")
    if rt:
        item = _parse_report_top(soup, rt, category)
        if item:
            out.append(item)
    for a in soup.find_all("a", class_="list_cont"):
        item = _parse_list_card(a, category)
        if item:
            out.append(item)
    return out


def fetch_all(timeout: int = 20, sleep_s: float = 0.7) -> tuple[list[dict], list[str]]:
    """모든 카테고리 fetch. (items, statuses) 반환. docId로 dedupe.
    카테고리에 max_items 설정 있으면 최근 N개만 채택.
    """
    by_id: dict[str, dict] = {}
    statuses: list[str] = []
    for cat_id, cat_name, url_tmpl, max_items in CATEGORIES:
        url = BASE + url_tmpl.format(cat_id)
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            statuses.append(f"catId={cat_id} ({cat_name}) → {r.status_code} {len(r.content)}b")
            if r.status_code != 200:
                continue
            items = parse_category_page(r.text, cat_name)
            # 페이지에 노출되는 순서가 최신순. max_items 있으면 앞에서 자름.
            if max_items is not None:
                items = items[:max_items]
            statuses.append(f"  parsed: {len(items)} items" + (f" (limit {max_items})" if max_items else ""))
            for it in items:
                # 같은 docId가 여러 카테고리에서 나오면 첫 등장(=더 좁은 카테고리) 우선
                by_id.setdefault(it["doc_id"], it)
        except Exception as e:
            statuses.append(f"catId={cat_id} → ERROR {e}")
        time.sleep(sleep_s)
    items = list(by_id.values())
    items.sort(key=lambda x: x.get("pub_date") or "0000-00", reverse=True)
    return items, statuses


if __name__ == "__main__":
    import json, sys
    items, statuses = fetch_all()
    for s in statuses:
        print(s, file=sys.stderr)
    print(json.dumps(items, ensure_ascii=False, indent=2))
