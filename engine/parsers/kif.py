"""한국금융연구원 (KIF) 전용 파서. SPA 사이트라 Playwright 사용.

사이트 구조:
  - /kif4/publication/pub_list?mid=N  → 카테고리 리스트 (JS 렌더)
  - /kif4/publication/pub_detail?mid=N&...&cno=NNNNNN  → 상세 (요약 노출)

카테고리 (mid):
  10 연구보고서, 11 영상보고서, 12 현안이슈, 20 금융브리프,
  21 경제전망, 22 금융연구, 23 한국경제의 분석

PDF는 execDownload(...) JS 함수로 trigger되므로 V1에서는 page에 노출된
요약 텍스트(.tab_content)를 본문으로 사용한다.
unique key는 cno.
"""
from __future__ import annotations
import re, time
from urllib.parse import urljoin, parse_qs, urlparse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

BASE = "https://www.kif.re.kr"
# (mid, 표시명, max_items 또는 None)
CATEGORIES = [
    (20, "금융브리프", None),
    (12, "현안이슈", None),
    (10, "연구보고서", None),
    (21, "경제전망", 5),
    (22, "금융연구", 5),
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36"


def _abs(url: str, base: str) -> str:
    return urljoin(base, url)


def _list_url(mid: int) -> str:
    return f"{BASE}/kif4/publication/pub_list?mid={mid}"


def _parse_list(html: str, mid: int) -> list[dict]:
    """리스트 페이지에서 보고서 카드 추출. 각 카드: cno, title, detail_url, pub_date(있으면)."""
    soup = BeautifulSoup(html, "html.parser")
    items_by_cno: dict[str, dict] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "pub_detail" not in href:
            continue
        # cno parse
        parsed = parse_qs(urlparse(href).query)
        cno_list = parsed.get("cno")
        if not cno_list:
            continue
        cno = cno_list[0]
        text = " ".join(a.get_text(strip=True).split())
        if not text or len(text) < 4:
            continue
        # 제목 앞 prefix "기타보고서", "[특별호]" 같은 카테고리 라벨 제거
        title = re.sub(r"^(연구보고서|기타보고서|영상보고서|현안이슈|금융브리프|경제전망|금융연구)\s*", "", text)
        detail_url = urljoin(_list_url(mid), href)
        items_by_cno[cno] = {
            "cno": cno,
            "title": title.strip(),
            "detail_url": detail_url,
        }
    return list(items_by_cno.values())


def _parse_detail(html: str) -> dict:
    """상세 페이지에서 저자/발간일/요약 추출.
    title은 권호 대표 제목이라 부정확 → list 단계의 anchor text를 그대로 사용.
    """
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {}
    # vol_title (권호 대표 제목)도 같이 저장 — 게시글 메타로 활용 가능
    title_el = soup.select_one(".title_summary")
    if title_el:
        out["vol_title"] = " ".join(title_el.get_text(strip=True).split())
    # info_detail 안에 저자/페이지수/요약 다 있음. 라벨 기반 파싱.
    info = soup.select_one(".info_detail")
    if info:
        rows: list[str] = []
        for line in info.get_text(separator="\n", strip=True).split("\n"):
            ln = line.strip()
            if ln:
                rows.append(ln)
        # 라벨-값 쌍: "저자\n김현태\n페이지 수\n6\n바로보기\n다운로드\n재생\n요약\n..."
        for i, ln in enumerate(rows):
            if ln == "저자" and i + 1 < len(rows):
                out["author"] = rows[i + 1]
            elif ln == "페이지 수" and i + 1 < len(rows):
                out["pages"] = rows[i + 1]
    # 요약 본문은 .tab_content 안에 단락별로
    tab = soup.select_one(".tab_content")
    if tab:
        lines = [ln.strip() for ln in tab.get_text(separator="\n", strip=True).split("\n") if ln.strip()]
        out["summary"] = "\n\n".join(lines)
    return out


def fetch_all(timeout_ms: int = 30000, sleep_ms: int = 300) -> tuple[list[dict], list[str]]:
    """모든 카테고리 fetch. (items, statuses) 반환. cno로 dedupe."""
    by_cno: dict[str, dict] = {}
    statuses: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()
        for mid, cat_name, max_items in CATEGORIES:
            try:
                page.goto(_list_url(mid), wait_until="networkidle", timeout=timeout_ms)
                html = page.content()
                items = _parse_list(html, mid)
                if max_items is not None:
                    items = items[:max_items]
                statuses.append(f"mid={mid} ({cat_name}) list: {len(items)} cards")
                for it in items:
                    it["category"] = cat_name
                    by_cno.setdefault(it["cno"], it)
            except Exception as e:
                statuses.append(f"mid={mid} list ERROR: {e}")

        # 각 detail 페이지 방문해서 요약 채움
        ok = fail = 0
        for it in by_cno.values():
            try:
                page.goto(it["detail_url"], wait_until="networkidle", timeout=timeout_ms)
                html = page.content()
                meta = _parse_detail(html)
                it.update(meta)
                ok += 1
                page.wait_for_timeout(sleep_ms)
            except Exception as e:
                fail += 1
                statuses.append(f"detail cno={it['cno']} ERROR: {e}")
        statuses.append(f"detail fetch: {ok} ok / {fail} failed")
        browser.close()

    items = list(by_cno.values())
    # 발간일(있으면)로 정렬, 없으면 cno desc
    items.sort(key=lambda x: (x.get("pub_date") or "", x.get("cno", "")), reverse=True)
    # KIRI 파서와 동일한 필드명으로 정규화
    for it in items:
        it["doc_id"] = it["cno"]  # render.py 의 doc_id 키와 호환
        it["download_url"] = it["detail_url"]  # PDF 직링크 없음 → KIF detail로
        it["viewer_url"] = None
        # 발간일이 없으면 빈 문자열
        it.setdefault("pub_date", "")
        it.setdefault("author", "")
        it.setdefault("summary", "")
    return items, statuses


if __name__ == "__main__":
    import json, sys
    items, statuses = fetch_all()
    for s in statuses:
        print(s, file=sys.stderr)
    print(json.dumps(items[:3], ensure_ascii=False, indent=2))
    print(f"... total {len(items)}", file=sys.stderr)
