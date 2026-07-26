---
title: "원문과 같은 match_phrase가 0건을 반환한 이유"
seoTitle: "Elasticsearch Nori match_phrase 0건: position hole 버그 분석"
date: 2026-07-15
description: "문서에 그대로 있는 보험계약대출이율을 match_phrase로 검색했는데 0건이 된 Elasticsearch Nori token graph position hole 버그를 재현하고 수정 과정을 설명합니다."
lang: ko
translations:
  en: posts/2026-07-15-elasticsearch-nori-position-hole
  ko: ko/posts/elasticsearch-nori-position-hole
---

문서에는 `보험계약대출이율`이라는 문자열이 그대로 들어 있었다. `match`는 문서를 찾았고 `match_phrase`도 `slop=1`에서는 찾았다. 그런데 같은 원문을 `slop=0`으로 검색하면 0건이었다.

이 문제는 BM25 점수나 recall 부족이 아니었다. Analyzer가 만든 token graph를 Elasticsearch가 phrase query로 바꾸는 과정에서 위치 정보 하나가 사라졌다.

## 최소 재현 결과

Elasticsearch 8.15.3과 Lucene 9.11.1에서 문서 하나를 색인해 기록한 결과다. Analyzer는 다음 조건을 함께 사용했다.

- `nori_tokenizer`, `decompound_mode=mixed`
- `nori_readingform`
- `lowercase`
- 조사 `이`를 제거하는 `nori_part_of_speech`

같은 입력을 세 가지 query path로 실행했다.

```json
{ "query": { "match": { "text": "보험계약대출이율" } } }
```

```json
{
  "query": {
    "match_phrase": {
      "text": {
        "query": "보험계약대출이율",
        "slop": 0
      }
    }
  }
}
```

```json
{
  "query": {
    "match_phrase": {
      "text": {
        "query": "보험계약대출이율",
        "slop": 1
      }
    }
  }
}
```

| Query | 결과 |
|---|---:|
| `match` | 1건 |
| `match_phrase`, `slop=0` | 0건 |
| `match_phrase`, `slop=1` | 1건 |

`slop=1`은 해결책이 아니다. 전체 phrase의 허용 간격을 넓혀 버그를 우회했을 뿐, exact phrase의 의미를 복구하지 않는다.

## Token graph에 있던 position hole

`mixed` mode는 원래 복합어와 분해된 경로를 함께 만든다. 품사 필터는 조사 `이`를 제거하지만 그 위치는 hole로 남긴다.

| Token | Position | 설명 |
|---|---:|---|
| 보험계약 | 0 | 원래 복합어, `positionLength=2` |
| 보험 | 0 | 분해 경로 |
| 계약 | 1 | 분해 경로 |
| 대출 | 2 | |
| 이 | 3 | 품사 필터가 제거 |
| 율 | 4 | |

분석된 스트림을 한 줄로 쓰면 다음과 같다.

```text
보험계약@0(len2) 보험@0 계약@1 대출@2 율@4
```

Lucene의 `QueryBuilder.createPhraseQuery`에 같은 스트림을 직접 넣으면 hole이 보존됐다.

```text
text:"보험계약 대출 ? 율" text:"보험 계약 대출 ? 율"
```

하지만 수정 전 Elasticsearch가 만든 zero-slop query tree에는 gap이 없었다.

```text
spanNear([
  spanOr([
    text:보험계약,
    spanNear([text:보험, text:계약], 0, true)
  ]),
  text:대출,
  text:율
], 0, true)
```

이 query는 `대출` 바로 다음 위치에 `율`이 있어야 한다고 요구한다. 인덱스에는 제거된 `이`의 위치가 남아 있으므로 일치하지 않는다.

## 원인 두 가지

`MatchQueryParser`의 graph phrase 처리에는 별개의 결함이 두 개 있었다.

1. `createSpanQuery`가 다음 토큰에서 발견한 gap을 앞 절 뒤가 아니라 한 절 이른 위치에 삽입했다.
2. `analyzeGraphPhrase`가 articulation point에서 graph를 나눈 뒤 바깥 segment를 조립하면서 segment 사이의 `PositionIncrementAttribute`를 전달하지 않았다.

한쪽만 고치면 다른 graph 형태에서 같은 문제가 남는다. [Elasticsearch #152931](https://github.com/elastic/elasticsearch/pull/152931)은 두 경로 모두에서 position increment를 보존하도록 수정했다.

- hole 앞 절을 먼저 추가한 뒤 올바른 위치에 `SpanGap`을 넣었다.
- graph 바깥 segment도 `SpanNearQuery.Builder`로 조립해 위치 증가량을 전달했다.
- 추가된 gap clause를 최종 clause 수에 반영했다.

## 회귀 테스트 범위

특정 한국어 문자열 하나에만 맞추지 않고 graph의 위치별로 테스트했다.

- graph side path 앞·안·뒤의 gap
- graph segment 주변의 여러 gap
- `synonym_graph` 뒤에서 stop filter가 토큰을 제거하는 경우
- Nori mixed decompound와 품사 필터를 함께 쓰는 end-to-end 재현
- stop filter가 synonym filter 앞에 있어 query builder가 복구할 수 없는 통제 사례

Phrase 검색을 검증할 때는 검색 결과 하나만 보지 말고 다음 네 산출물을 같이 봐야 한다.

```text
원문
→ 분석된 token graph
→ 컴파일된 query tree
→ 매칭 문서
```

관련된 앞단 문제로는 [NFD 한글이 Nori 사전 분석에서 빠지는 현상](/ko/posts/lucene-nfd-hangul-search)과 [XPN 제거로 비급여와 급여가 합쳐지는 현상](/ko/posts/elasticsearch-nori-xpn-stoptags)이 있다. [한국어 검색 정확성 가이드](/ko/korean-search-correctness)는 세 문제를 하나의 진단 순서로 연결한다.
