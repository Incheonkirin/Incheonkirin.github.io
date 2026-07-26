---
title: "Elasticsearch·Lucene 한국어 검색 정확성 가이드"
seoTitle: "Elasticsearch·Lucene 한국어 검색 오류 진단: Nori, NFD, match_phrase"
date: 2026-07-26
description: "한글 자소분리, Nori XPN stoptags, token graph position hole, wildcard normalizer처럼 랭킹 전에 한국어 의미가 사라지는 문제를 재현 사례와 함께 진단합니다."
lang: ko
---

한국어 검색 결과가 틀렸다고 해서 항상 랭킹 모델부터 조정할 일은 아니다. BM25나 reranker가 점수를 계산하기 전에 문자 표현, 형태소 필터, token graph, query parser가 검색에 필요한 구분을 이미 바꾸거나 버렸을 수 있다.

이 가이드는 실제 보험 약관 검색에서 발견해 Apache Lucene과 Elasticsearch upstream 수정으로 연결한 네 가지 실패를 하나의 진단 순서로 묶는다.

## 증상별 바로가기

| 검색 증상 | 먼저 확인할 경계 | 재현 사례 |
|---|---|---|
| 같은 한글인데 일부 문서만 검색되지 않음 | NFC/NFD 유니코드 표현 | [한글 자소분리 때문에 검색이 누락되는 이유](/ko/posts/lucene-nfd-hangul-search) |
| `비급여` 검색에 `급여` 문서가 섞임 | Nori 품사 필터와 XPN | [Nori에서 비급여가 급여로 분석되는 이유](/ko/posts/elasticsearch-nori-xpn-stoptags) |
| 문서에서 복사한 문장이 `match_phrase` 0건 | token graph와 position hole | [원문과 같은 match_phrase가 0건인 이유](/ko/posts/elasticsearch-nori-position-hole) |
| 전각 문자를 검색했는데 wildcard처럼 동작 | normalizer와 query operator 경계 | [Normalizer가 전각 문자를 wildcard 연산자로 바꾼 문제](../posts/2026-07-20-wildcard-operators-from-a-normalizer) |

## 1. 문자 표현: 화면이 같아도 analyzer 입력은 다를 수 있다

현대 한글은 완성형 NFC 음절 또는 초성·중성·종성이 분리된 NFD 결합 자모로 표현될 수 있다. 사람 눈에는 같지만 Nori 사전은 완성형 음절을 기준으로 하므로 분석 결과가 달라질 수 있다.

```text
NFC 보험계약대출이율
→ 보험계약@0(len2) 보험@0 계약@1 대출@2 율@4

NFD 보험계약대출이율
→ 보험계약대출이율@0
```

첫 단계는 원문을 눈으로 비교하는 것이 아니라 코드 포인트와 정규화 형식을 기록하는 것이다. Lucene #16242의 `HangulCompositionCharFilter`는 현대 한글 결합 자모만 좁게 조합하고 원문 offset을 보존한다.

## 2. 형태소 필터: 제거한 토큰이 의미를 뒤집는지 확인한다

기본 `nori_part_of_speech` stoptags에는 `XPN`이 포함된다. 그 결과 체언 접두사가 빠져 반대 개념이 같은 토큰으로 합쳐질 수 있다.

```text
비급여 → 급여
부담보 → 담보
```

Analyzer 최적화의 전제는 제거한 토큰이 relevance 판단에 중요하지 않다는 것이다. 보험·법률·의료에서는 이 전제가 쉽게 깨진다. 사용자 사전으로 고위험 복합어를 보존하거나 custom stoptags에서 XPN을 유지한 뒤, 반대 의미 문서를 함께 둔 contrastive test로 평가해야 한다.

## 3. Token graph: 올바른 토큰이 올바른 query를 보장하지 않는다

복합어 분해나 synonym은 graph를 만들고 stop filter는 position hole을 만들 수 있다. Analyzer 출력이 정확해도 query builder가 graph를 실행 가능한 phrase query로 바꾸면서 위치를 잃으면 exact phrase가 더 엄격한 잘못된 query가 된다.

```text
원문
→ analyzed token graph
→ compiled query tree
→ matched documents
```

`match`, `match_phrase slop=0`, `match_phrase slop=1`을 나란히 비교하고, `_analyze`의 position/positionLength와 rewrite된 query tree를 함께 확인한다. `slop`을 올려 결과가 나온다고 해서 analyzer 설정 문제로 결론 내리면 안 된다.

## 4. Normalizer와 연산자: 변환된 데이터가 문법이 될 수 있다

전각 `＊`, `？`, `＼`을 ASCII `*`, `?`, `\`로 접는 것은 normalizer 관점에서 올바르다. 하지만 그 출력이 wildcard pattern parser로 넘어가면 리터럴 데이터가 연산자로 다시 해석될 수 있다.

```text
foo＊bar  --normalize-->  foo*bar
                              ^
                         literal인가 operator인가?
```

경계에서 필요한 불변식은 단순하다. Normalizer가 만든 wildcard 제어 문자는 다시 escape되어 데이터로 남아야 하고, 사용자가 직접 쓴 ASCII operator만 문법으로 유지되어야 한다.

## 재사용 가능한 진단 체크리스트

1. 실제 입력의 Unicode code point와 정규화 형식을 확인한다.
2. index analyzer와 search analyzer의 term, position, positionLength, offset을 저장한다.
3. 반대 의미 쌍이 같은 토큰 시퀀스로 합쳐지는지 검사한다.
4. graph와 hole이 함께 있을 때 compiled query tree를 확인한다.
5. 리터럴 문자가 normalizer 이후 query operator가 되는지 검사한다.
6. unit reproduction을 만든 뒤 전체 검색 시스템에서도 반대 근거가 위로 올라오는지 측정한다.

## Upstream 결과

- [Apache Lucene #16242](https://github.com/apache/lucene/pull/16242): NFD 한글을 조합하는 `HangulCompositionCharFilter`
- [Elasticsearch #151157](https://github.com/elastic/elasticsearch/pull/151157): XPN 기본 stoptag 위험과 두 구성 해결책을 공식 문서화
- [Elasticsearch #152931](https://github.com/elastic/elasticsearch/pull/152931): graph phrase query에서 position hole 보존
- [Elasticsearch #153582](https://github.com/elastic/elasticsearch/pull/153582): normalizer가 만든 wildcard 연산자를 리터럴로 재이스케이프

재현 근거와 범위는 [공개 case study 저장소](https://github.com/Incheonkirin/korean-search-correctness/tree/main/case_studies/korean-retrieval-correctness)에도 정리되어 있다.

핵심은 랭킹 점수를 높이는 것보다 먼저 검색에 필요한 구분이 모든 표현 경계를 통과하는지 확인하는 것이다. 표현이 이미 무너졌다면 더 큰 모델도 잃어버린 정보를 복구한다고 보장할 수 없다.
