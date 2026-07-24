# engine/ — 모니터링 다이제스트 파이프라인

`reference_monitoring_sources.md` 의 우선순위 1·2 소스를 매일 크롤링해서
`content/pulse/index.md` 에 신규 항목을 모은다.

## 구조

```
engine/
  sources.py          # 소스 정의 (URL, 링크 필터 패턴)
  fetch.py            # 페이지 fetch + diff → state/*.json
  render.py           # state → content/pulse/index.md
  state/<id>.json     # 소스별 누적 상태 (이전 본 링크 + first_seen)
  requirements.txt
```

## 사용

```bash
# 의존성
python3 -m pip install -r engine/requirements.txt

# 전체 fetch (10개 소스)
python3 engine/fetch.py

# 선택 fetch
python3 engine/fetch.py kiri kif

# 렌더
python3 engine/render.py

# Quartz 빌드 후 미리보기
npx quartz build --serve
```

## 동작

1. 각 소스 페이지를 requests로 가져옴 (UA 위장)
2. `<a href>` 전부 추출 → `link_filter` 정규식으로 게시글만 필터
3. URL을 키로 state JSON과 diff
4. 신규 항목에 `first_seen = 오늘` 마킹
5. 소스당 최근 100개만 keep, 나머지 truncate
6. render.py 가 카테고리별로 묶어 markdown 출력

## 한계 (V1)

- **JS 렌더 사이트는 못 잡는다** (카페손보, 토스인슈, 일부 보험사).
  state에 "수집된 링크 없음"으로 표시되므로 사용자가 확인 가능.
  V2에서 Playwright 또는 사이트별 RSS·API 경로 보강.
- **링크 필터 정규식은 추측 기반**. 실제 fetch 후 노이즈 많으면 사이트별로 튜닝.
- **제목이 anchor text** 라서 메뉴/카테고리 링크가 섞일 수 있음. 정규식과 길이(>=4) 필터로 1차 컷.

## 자동화

GitHub Actions 워크플로는 `.github/workflows/engine-fetch.yaml.disabled` 에
초안만 있고 비활성화 상태. 본인이 fetch 결과 한 차례 검수 후 `.disabled` 떼면
매일 자동 실행 + 커밋 + 푸시 + Quartz 빌드 → 배포 체인으로 들어간다.
