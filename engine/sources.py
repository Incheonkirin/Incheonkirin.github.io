"""모니터링 소스 정의. reference_monitoring_sources.md 의 우선순위 1·2 기준.

각 소스는 다음 메타를 가진다:
  - id: 파일명/슬러그
  - name: 표시명
  - category: priority1_research / priority2_insurer
  - urls: 크롤링할 페이지 리스트 (한 소스에 게시판 여러 개 가능)
  - link_filter: 게시글 링크로 인정할 URL 패턴 (정규식, optional)
  - notes: 비고
"""

SOURCES = [
    # ── 우선순위 1: 연구기관 ──────────────────────────────────────
    {
        "id": "kiri",
        "name": "한국보험연구원 (KIRI)",
        "category": "priority1_research",
        "parser": "kiri",   # 전용 파서. urls/link_filter 무시.
        "notes": "연구보고서 / CEO Report / CEO Brief / 정기간행물 4개 카테고리 통합",
    },
    {
        "id": "kif",
        "name": "한국금융연구원 (KIF)",
        "category": "priority1_research",
        "parser": "kif",  # SPA 사이트 → Playwright 사용. urls 무시.
        "notes": "금융브리프·현안이슈·연구보고서·경제전망·금융연구. PDF 직링크 없음 → KIF 페이지 요약 사용.",
    },
    {
        "id": "hanaif",
        "name": "하나금융경영연구소",
        "category": "priority1_research",
        "urls": [
            "https://www.hanaif.re.kr/boardList.do?hmpeMnuSn=000000000095",
        ],
        "link_filter": r"(boardDetail|hmpeMnuSn)",
        "notes": "연구보고서 게시판",
    },
    {
        "id": "kbfg",
        "name": "KB금융지주 경영연구소",
        "category": "priority1_research",
        "urls": [
            "https://www.kbfg.com/kbresearch/report/reportList.do",
        ],
        "link_filter": r"(reportView|/kbresearch/)",
        "notes": "KB연구소 리포트",
    },
    {
        "id": "klia",
        "name": "생명보험협회 (KLIA)",
        "category": "priority1_research",
        "urls": [
            "https://www.klia.or.kr/consumer/news/news.do",
        ],
        "link_filter": r"(news|notice|board)",
        "notes": "소식지·뉴스",
    },
    # ── 우선순위 2: 보험사 ────────────────────────────────────────
    {
        "id": "hanwha_life",
        "name": "한화생명 뉴스룸",
        "category": "priority2_insurer",
        "urls": [
            "https://www.hanwhalife.com/static/company/news/CO_NW_LB_CD000_P10000.jsp",
        ],
        "link_filter": r"(news|notice)",
        "notes": "뉴스룸",
    },
    {
        "id": "samsung_life",
        "name": "삼성생명",
        "category": "priority2_insurer",
        "urls": [
            "https://www.samsunglife.com/individual/customer/news",
        ],
        "link_filter": r"(news|notice|press)",
        "notes": "고객센터 뉴스",
    },
    {
        "id": "kp_insurance",
        "name": "카카오페이손해보험 (1순위 타겟)",
        "category": "priority2_insurer",
        "urls": [
            "https://www.kakaopayinsurance.com/notice",
            "https://www.kakaopayinsurance.com/insurance",
        ],
        "link_filter": r"(notice|insurance|product)",
        "notes": "공지·상품. JS 렌더 가능성",
    },
    {
        "id": "toss_insurance",
        "name": "토스인슈어런스",
        "category": "priority2_insurer",
        "urls": [
            "https://toss.im/tossinsurance",
        ],
        "link_filter": r"(insurance|notice|news)",
        "notes": "메인. JS 렌더 가능성",
    },
    {
        "id": "meritz",
        "name": "메리츠화재",
        "category": "priority2_insurer",
        "urls": [
            "https://www.meritzfire.com/customer-center/notice.do",
        ],
        "link_filter": r"(notice|board)",
        "notes": "고객센터 공지",
    },
]


def by_category():
    out = {}
    for s in SOURCES:
        out.setdefault(s["category"], []).append(s)
    return out
