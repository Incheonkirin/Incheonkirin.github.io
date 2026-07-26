---
title: "Elasticsearch Nori에서 비급여가 급여로 분석되는 이유"
seoTitle: "Elasticsearch Nori 비급여→급여 문제: XPN stoptags 원인과 해결"
date: 2026-06-16
description: "Elasticsearch Nori 기본 품사 필터가 비급여의 비(XPN)를 제거해 급여와 같은 토큰으로 만드는 문제를 재현하고, 사용자 사전과 custom stoptags 해결책을 비교합니다."
lang: ko
translations:
  en: posts/2026-06-16-noris-default-stoptags-drop-korean-negation-prefixes
  ko: ko/posts/elasticsearch-nori-xpn-stoptags
---

보험 약관 검색을 개발하던 중 `비급여`를 검색했는데 `급여` 조항이 함께 나오는 현상을 발견했다. 반대 방향도 같았다. 보장 여부가 정반대인 두 단어가 Elasticsearch 내부에서는 같은 토큰이 된 것이다.

이 문제는 BM25 튜닝이나 임베딩 모델 교체로 고칠 수 없다. 서로 다른 의미가 색인 전에 이미 하나로 합쳐졌기 때문이다.

## 최소 재현

기본 Nori analyzer에 `_analyze`를 호출하면 바로 확인할 수 있다.

```http
GET _analyze
{
  "analyzer": "nori",
  "text": "비급여"
}
```

응답에는 `급여` 하나만 남는다.

```json
{
  "tokens": [
    {
      "token": "급여",
      "start_offset": 1,
      "end_offset": 3,
      "type": "word",
      "position": 1
    }
  ]
}
```

같은 형태의 반대말도 같은 방식으로 합쳐진다.

```text
비급여  → 급여
급여    → 급여

부담보  → 담보
담보    → 담보
```

인덱스 analyzer와 search analyzer에 같은 설정을 사용하면 문서와 질의 양쪽에서 접두사가 사라진다. 색인에는 원래 단어가 `비급여`였는지 `급여`였는지 구분할 정보가 남지 않는다.

## 원인: 기본 stoptags의 XPN

Nori tokenizer는 `비급여`를 다음처럼 분석한다.

```text
비   / XPN  (체언 접두사)
급여 / NNG  (일반 명사)
```

형태소 분석 자체는 맞다. 문제는 다음 단계인 `nori_part_of_speech` 필터다. 기본 `stoptags` 목록에 `XPN`이 포함되어 있어 `비`가 제거된다.

관형사나 일부 기능어를 제거하는 기본값은 일반 검색에서는 합리적일 수 있다. 하지만 보험·법률·의료 문서에서 `비`, `부`, `무`, `미` 같은 접두사는 보장 여부나 적용 여부를 뒤집는 핵심 의미다. 이를 불용어처럼 버리면 주제가 비슷한 문서를 찾는 데는 성공해도, 질의와 반대되는 근거를 반환할 수 있다.

## 해결 1: 중요한 복합어를 사용자 사전에 등록

관리해야 할 고위험 용어가 명확하다면 완성된 명사로 보존하는 방식이 가장 좁고 감사하기 쉽다.

```http
PUT insurance-search
{
  "settings": {
    "analysis": {
      "tokenizer": {
        "nori_domain": {
          "type": "nori_tokenizer",
          "user_dictionary_rules": [
            "비급여",
            "부담보"
          ]
        }
      },
      "analyzer": {
        "nori_domain": {
          "type": "custom",
          "tokenizer": "nori_domain",
          "filter": ["nori_part_of_speech"]
        }
      }
    }
  }
}
```

장점은 영향 범위가 등록한 용어로 제한된다는 것이다. 단점은 새 도메인 용어가 생길 때마다 사전과 회귀 테스트를 함께 관리해야 한다는 점이다.

## 해결 2: custom stoptags에서 XPN을 제외

등록하지 않은 접두사까지 넓게 보존해야 한다면 `XPN`을 뺀 품사 필터를 정의할 수 있다.

```json
{
  "filter": {
    "keep_xpn": {
      "type": "nori_part_of_speech",
      "stoptags": [
        "IC", "MAG", "MAJ", "MM",
        "SP", "SSC", "SSO", "SC", "SE",
        "XSA", "XSN", "XSV",
        "UNA", "NA", "VSV"
      ]
    }
  }
}
```

이 경우 `비급여`는 최소한 `비`와 `급여`라는 서로 다른 토큰 시퀀스로 남는다. 다만 모든 XPN을 보존하므로 다른 질의에서 접두사 노이즈가 늘 수 있다. 운영 코퍼스의 recall과 precision을 함께 측정해야 한다.

| 선택 | 적합한 경우 | 주의점 |
|---|---|---|
| 사용자 사전 | 위험 용어 목록을 통제할 수 있음 | 사전 누락과 유지보수 |
| XPN 보존 | 발견하지 못한 접두사까지 보호해야 함 | 불필요한 접두사 토큰 증가 |

## 회귀 테스트

일반적인 topic relevance만 측정하면 이 문제가 가려질 수 있다. 다음처럼 반대 의미를 한 쌍으로 묶어 검사해야 한다.

```text
질의: 비급여 치료
기대 문서: 비급여 치료 조항
반대 문서: 급여 치료 조항

질의: 급여 치료
기대 문서: 급여 치료 조항
반대 문서: 비급여 치료 조항
```

최소한 analyzer 출력이 서로 달라야 하고, 각 방향에서 기대 문서가 반대 문서보다 위에 있어야 한다. 사용자 사전이나 XPN 보존을 적용한 뒤에는 관련 없는 질의의 품질이 나빠지지 않았는지도 확인한다.

이 동작과 두 해결책은 [Elasticsearch #151157](https://github.com/elastic/elasticsearch/pull/151157)을 통해 공식 Nori 문서에 반영됐다.

다음 단계에서는 토큰이 올바르게 남아도 질의 생성 과정에서 위치 정보가 사라질 수 있다. [원문과 같은 `match_phrase`가 0건을 반환한 문제](/ko/posts/elasticsearch-nori-position-hole)와 [한국어 검색 정확성 가이드](/ko/korean-search-correctness)에서 이어서 설명한다.
