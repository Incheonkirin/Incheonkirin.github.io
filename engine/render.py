"""state/*.json → content/private/pulse-inbox/*.md 수집·렌더링.

각 보고서가 노트 1개 (`content/private/pulse-inbox/{발간일}-{출처}-{slug}.md`).
Quartz ignorePatterns로 웹에는 비공개. 사이트에 올릴 글은 수동으로 content/pulse/에 선별 복사.

frontmatter:
  title: 원본 제목
  date: 발간일 (YYYY-MM-DD; KIRI는 YYYY-MM만 주므로 -01 패딩)
  tags: [출처태그, 카테고리]
  source: 출처 표시명
  pdf_url: PDF 다운로드 URL
  source_url: 원문 페이지 URL

본문:
  - 메타 (출처·카테고리·저자·발간일)
  - 요약 텍스트 (원문에서 그대로 가져옴)
  - 첨부: PDF 링크
  - 원문 링크
"""
from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
STATE_DIR = ROOT / "state"
PULSE_DIR = ROOT.parent / "content" / "private" / "pulse-inbox"

# 출처별 메타 (state id → 표시명 + 태그 + 원문 URL 빌더)
SOURCE_META = {
    "kiri": {
        "name": "한국보험연구원",
        "tag": "KIRI",
        "source_url": "https://www.kiri.or.kr/report/reportList.do",
    },
    "kif": {
        "name": "한국금융연구원",
        "tag": "KIF",
        "source_url": "https://www.kif.re.kr/kif4/publication/pub_list?mid=20",
    },
}


def _slugify(title: str, max_len: int = 60) -> str:
    """한글 유지, 공백 → 하이픈, 안전하지 않은 문자 제거."""
    t = title.strip()
    t = re.sub(r"[\[\]()‘’“”\"'`]", "", t)  # 따옴표·괄호 제거
    t = re.sub(r"[/\\<>:|?*#]", "", t)  # 파일시스템 금지문자
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"-+", "-", t)
    t = t.strip("-")
    return t[:max_len]


def _normalize_date(pub: str) -> str:
    """YYYY-MM 또는 YYYY-MM-DD → YYYY-MM-DD. 비어있으면 today."""
    if not pub:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", pub):
        return pub
    if re.match(r"^\d{4}-\d{2}$", pub):
        return f"{pub}-01"
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _strip_volume_prefix(title: str) -> str:
    """제목 앞 '[권호 : 25-20] ' 같은 prefix를 잘라낸 깨끗한 제목."""
    return re.sub(r"^\[권호\s*:\s*[^\]]+\]\s*", "", title).strip()


def _excerpt(text: str, max_chars: int = 4000) -> tuple[str, bool]:
    """본문 텍스트를 max_chars 까지 자르되 문단 경계 우선."""
    if len(text) <= max_chars:
        return text, False
    cut = text.rfind("\n\n", 0, max_chars)
    if cut < max_chars * 0.5:
        cut = text.rfind("\n", 0, max_chars)
    if cut < max_chars * 0.5:
        cut = max_chars
    return text[:cut].rstrip(), True


# ── PDF 본문 가독성 정리 ────────────────────────────────────────
_HEADER_RES = [
    re.compile(r"^KIRI 리포트.*?\s*\d+\s*$"),
    re.compile(r"^KIRI 리포트\s+(이슈 분석|포커스|글로벌 이슈|특별기고|보험법 동향)\s*\d*\s*$"),
    re.compile(r"^KIRI Weekly\s*$"),
    re.compile(r"^\s*[-–]\s*\d+\s*[-–]\s*$"),
    re.compile(r"^\s*\d+\s*$"),  # 페이지 번호 단독
    re.compile(r"^보험연구원\s*$"),
    re.compile(r"^Korea Insurance Research Institute\s*$"),
    re.compile(r"^www\.kiri\.or\.kr\s*$"),
    re.compile(r"^CEO Brief는 보험산업.*?제공되는 리포트입니다.*$"),
    re.compile(r"^<그림\s*\d+.*?>\s*.*$"),
    re.compile(r"^<표\s*\d+.*?>\s*.*$"),
    re.compile(r"^자료:.*$"),
    re.compile(r"^주\)?\s*:.*$"),
    re.compile(r"^\(단위:.*\)\s*$"),
    re.compile(r"^요\s*약\s*$"),  # "요 약" 단독 라인 (제목 위에 떠다님)
    re.compile(r"^[가-힣]{2,4}\s+(연구위원|연구원|선임연구위원|부연구위원|책임연구원|수석연구위원)\s*$"),  # "한진현 연구위원"
    re.compile(r"^\d{4}\.\s?\d{1,2}\.(\s?\d{1,2}\.)?\s*$"),  # "2026.05.18." 날짜 단독
]

_FOOTNOTE_LINE = re.compile(r"^\d{1,2}\)\s")
_HANGUL = re.compile(r"[가-힣]")

# 글머리 기호 → 마크다운 들여쓰기
_BULLET_TOP = re.compile(r"^[○¡]\s*")     # top level
_BULLET_SUB = re.compile(r"^[∙Ÿ•]\s*")    # nested
_BULLET_DASH = re.compile(r"^[-–]\s+")    # 이미 dash (보통 nested^2)
_BULLET_NUM = re.compile(r"^\d+\.\s+")    # "1. 인공지능 시대..." 섹션 헤더 (top)


def _is_header_footer(line: str) -> bool:
    for pat in _HEADER_RES:
        if pat.match(line):
            return True
    return False


def _normalize_body(text: str, title: str = "", series: str = "") -> str:
    """PDF에서 추출한 raw 본문을 마크다운 친화적으로 정리.

    - 페이지 헤더/푸터/그림 캡션 라인 제거
    - 글머리 기호(○∙¡Ÿ•) → 마크다운 들여쓰기 bullet
    - 연속된 본문 라인을 공백 한 칸으로 합침 (한국어/영어 공통)
    - 단어 끝 하이픈은 다음 줄과 붙임
    """
    # 페이지 헤더로 자주 나오는 단독 라인: 보고서 제목, 시리즈명
    extra_headers = set()
    if title:
        extra_headers.add(title.strip())
    if series:
        extra_headers.add(series.strip())

    lines = []
    for raw in text.splitlines():
        ln = raw.rstrip()
        if not ln:
            lines.append("")
            continue
        s = ln.strip()
        if _is_header_footer(s):
            continue
        if s in extra_headers:
            continue
        lines.append(ln)

    out_blocks: list[str] = []
    current = ""

    def flush():
        nonlocal current
        if current.strip():
            out_blocks.append(current.strip())
        current = ""

    for ln in lines:
        s = ln.strip()
        if not s:
            flush()
            continue

        if m := _BULLET_NUM.match(s):
            flush()
            current = f"**{s}**"  # "1. ..." 같은 섹션 헤더는 굵게
            continue
        if _BULLET_TOP.match(s):
            flush()
            current = f"- {_BULLET_TOP.sub('', s)}"
            continue
        if _BULLET_SUB.match(s):
            flush()
            current = f"  - {_BULLET_SUB.sub('', s)}"
            continue
        if _BULLET_DASH.match(s):
            flush()
            current = f"    - {_BULLET_DASH.sub('', s)}"
            continue

        # 각주 라인 ("5) 경기도 보도자료..." 같이 라인 시작이 'N) ')
        if _FOOTNOTE_LINE.match(s):
            flush()
            out_blocks.append(f"> {s}")  # 인용 블록 + 다음 라인과 분리
            current = ""
            continue

        # 본문 continuation
        if current:
            last = current[-1]
            if last == "-":
                # 영어 단어 분리 하이픈
                current = current[:-1] + s
            else:
                # 어절 경계 가정: 항상 공백 추가
                current = current + " " + s
        else:
            current = s
    flush()

    # 합쳐진 단락 끝에 페이지 헤더가 붙어 있으면 잘라냄
    # (예: "...할 것임 AI 영상 분석 기술을 이용한 위험 관리 이슈 분석")
    cleanup_patterns = []
    if title:
        cleanup_patterns.append(re.escape(title.strip()))
    if series:
        cleanup_patterns.append(re.escape(series.strip()))
    if cleanup_patterns:
        # 단락 끝의 " <title>"/"<series>" 한 번 또는 두 번 반복
        suffix_re = re.compile(
            r"(?:\s+(?:" + "|".join(cleanup_patterns) + r")){1,3}\s*$"
        )
        out_blocks = [suffix_re.sub("", b).strip() for b in out_blocks]
        out_blocks = [b for b in out_blocks if b]

    text = "\n\n".join(out_blocks)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^(- |\s+- )\s+", r"\1", text, flags=re.M)
    return text


def _post_path(item: dict, source_meta: dict) -> Path:
    date = _normalize_date(item.get("pub_date", ""))
    clean_title = _strip_volume_prefix(item["title"])
    slug = _slugify(clean_title)
    src_slug = source_meta["tag"].lower()
    return PULSE_DIR / f"{date}-{src_slug}-{item['doc_id']}-{slug}.md"


def _render_post(item: dict, source_meta: dict) -> str:
    date = _normalize_date(item.get("pub_date", ""))
    clean_title = _strip_volume_prefix(item["title"])
    tag = source_meta["tag"]
    category = item.get("category", "").strip()
    display_title = clean_title
    if category and category not in clean_title:
        display_title = f"{clean_title} ({category})"
    tags = [tag]
    if category:
        tags.append(category)
    pdf_url = item.get("download_url") or ""
    viewer = item.get("viewer_url") or ""
    # PDF 직링크인지 (KIRI) 일반 detail URL인지 (KIF) 구분
    is_pdf_link = bool(re.search(r"\.pdf(\?|$)|downloadFile", pdf_url, re.I))
    src_url = source_meta["source_url"]
    author = item.get("author", "")
    pub_label = item.get("pub_date", "")
    summary = (item.get("summary") or "").strip()

    fm_lines = [
        "---",
        f'title: "[{tag}] {display_title}"',
        f"date: {date}",
        "tags:",
    ]
    for t in tags:
        fm_lines.append(f'  - "{t}"')
    fm_lines.append(f'source: "{source_meta["name"]}"')
    if pdf_url:
        key = "pdf_url" if is_pdf_link else "detail_url"
        fm_lines.append(f'{key}: "{pdf_url}"')
    fm_lines.append(f'source_url: "{src_url}"')
    fm_lines.append("---")
    fm = "\n".join(fm_lines)

    meta_parts = []
    if pub_label:
        meta_parts.append(f"**발간**: {pub_label}")
    if category:
        meta_parts.append(f"**구분**: {category}")
    if author:
        meta_parts.append(f"**저자**: {author}")
    meta_parts.append(f"**출처**: [{source_meta['name']}]({src_url})")
    meta_line = " · ".join(meta_parts)

    body = [fm, "", meta_line, ""]
    if summary:
        body.append("## 요약")
        body.append("")
        body.append(summary)
        body.append("")
    body_text = (item.get("body_text") or "").strip()
    if body_text:
        normalized = _normalize_body(body_text, title=clean_title, series=category)
        excerpt, truncated = _excerpt(normalized, max_chars=4500)
        body.append("## 본문 발췌")
        body.append("")
        body.append(excerpt)
        if truncated:
            body.append("")
            body.append(f"_… (전체 본문은 [원문 PDF]({pdf_url})에서 확인)_")
        body.append("")
    body.append("## 원문")
    body.append("")
    if pdf_url:
        label = "PDF 다운로드" if is_pdf_link else "원문 페이지 (PDF 다운로드 포함)"
        body.append(f"- [{label}]({pdf_url})")
    if viewer:
        body.append(f"- [뷰어로 바로보기]({viewer})")
    body.append(f"- [원문 게시판]({src_url})")
    body.append("")
    return "\n".join(body)


def _render_index(all_posts: list[dict]) -> str:
    now = datetime.now(timezone.utc).astimezone()
    lines = [
        "---",
        "title: Pulse",
        f"date: {now.strftime('%Y-%m-%d')}",
        "---",
        "",
        "연구기관·보험사 신규 게시물을 매일 크롤링해서 자동으로 올리는 게시판. "
        "각 게시글은 출처 태그(`[KIRI]` 등) + 원문 요약 + PDF 링크.",
        "",
        f"_총 {len(all_posts)}개 게시글 · 마지막 업데이트 {now.strftime('%Y-%m-%d %H:%M %Z')}_",
        "",
    ]
    return "\n".join(lines) + "\n"


def render():
    PULSE_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    all_posts: list[dict] = []

    # 기존 자동생성 게시글 정리 (index.md 제외, *-<src>-<docId>-*.md 패턴만)
    for old in PULSE_DIR.glob("*.md"):
        if old.name == "index.md":
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}-\w+-\d+-", old.name):
            old.unlink()

    for sid, meta in SOURCE_META.items():
        sp = STATE_DIR / f"{sid}.json"
        if not sp.exists():
            continue
        st = json.loads(sp.read_text(encoding="utf-8"))
        for it in st.get("items", []):
            if "doc_id" not in it:
                continue
            p = _post_path(it, meta)
            content = _render_post(it, meta)
            p.write_text(content, encoding="utf-8")
            all_posts.append(it)
            written += 1

    index = PULSE_DIR / "index.md"
    index.write_text(_render_index(all_posts), encoding="utf-8")
    print(f"[render] {written} posts written to {PULSE_DIR} (skipped {skipped})")


if __name__ == "__main__":
    render()
