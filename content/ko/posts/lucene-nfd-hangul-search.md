---
title: "같은 한글인데 Elasticsearch 검색 결과가 달라진 이유"
seoTitle: "한글 자소분리(NFD) 검색 누락: Lucene Nori 원인과 해결"
date: 2026-06-30
description: "화면에는 같은 한글이 NFC와 NFD로 다르게 저장될 때 Lucene Nori 사전 분석과 검색 결과가 달라지는 현상을 재현하고 HangulCompositionCharFilter 해결책을 설명합니다."
tags: [Lucene, Elasticsearch, Nori, Korean-Search, Unicode]
lang: ko
translations:
  en: posts/2026-06-30-nfd-hangul-and-noris-dictionary
  ko: ko/posts/lucene-nfd-hangul-search
---

`보험계약대출이율`이라는 같은 단어를 Nori analyzer에 두 번 넣었다. 화면에 표시되는 글자는 같았다. 하지만 한쪽은 `보험계약`, `보험`, `계약`, `대출`, `율`로 분석됐고, 다른 쪽은 단어 전체가 정체를 알 수 없는 토큰 하나로 남았다.

```text
보험계약@0(len2) 보험@0 계약@1 대출@2 율@4

보험계약대출이율@0
```

두 번째 줄도 브라우저에서는 `보험계약대출이율`로 보인다. 차이는 문자열의 표현 방식뿐이다. 첫 번째는 완성형 한글인 NFC, 두 번째는 초성·중성·종성이 나뉜 NFD다.

이 차이는 analyzer 출력에서 끝나지 않는다. NFD 문서가 저 형태로 색인되면 NFC 질의에서 만들어진 `보험`, `계약`, `대출`, `율` 토큰과 일치하지 않는다. 사용자에게는 분명 문서에 있는 단어인데 검색 결과에는 나오지 않는 문제로 보인다. Elasticsearch도 오류를 내지 않는다.

## 같은 글자인데 Nori는 한쪽만 형태소 분석했다

Python 표준 라이브러리로 두 문자열의 차이를 확인할 수 있다.

```python
import unicodedata

nfc = "비급여"
nfd = unicodedata.normalize("NFD", nfc)

print(nfc == nfd)
print([f"U+{ord(char):04X}" for char in nfc])
print([f"U+{ord(char):04X}" for char in nfd])
```

```text
False
['U+BE44', 'U+AE09', 'U+C5EC']
['U+1107', 'U+1175', 'U+1100', 'U+1173', 'U+11B8', 'U+110B', 'U+1167']
```

NFC의 `비`는 `U+BE44` 한 글자다. NFD에서는 초성 `U+1107`과 중성 `U+1175` 두 글자로 표현된다. 유니코드 정규화를 거치면 같은 문자열이지만, 정규화하기 전에는 길이와 코드 포인트가 모두 다르다.

Nori의 `KoreanTokenizer`는 완성형 음절로 구성된 사전을 사용한다. NFC 입력은 사전에서 복합어와 형태소를 찾을 수 있지만, 결합 자모가 연속된 NFD 입력은 같은 표제어를 찾지 못한다. 결국 공백으로 구분된 전체 어절이 `UNKNOWN` 토큰으로 남는다.

문제는 Nori 사전의 단어가 부족해서가 아니었다. 사전에 도달하기 전에 입력 표현을 맞추지 못한 것이었다.

## 그냥 모든 입력을 NFC로 바꾸면 되지 않을까

가장 먼저 떠오르는 해결책은 Unicode 정규화다. Lucene에는 ICU 기반의 `ICUNormalizer2CharFilter`가 있고, NFC뿐 아니라 폭넓은 유니코드 정규화를 처리할 수 있다. ICU 모듈을 이미 사용하는 시스템이라면 이 방법이 적절하다.

하지만 `analysis-nori` 자체는 ICU에 의존하지 않는다. NFD 한글 한 가지를 처리하기 위해 Nori 모듈에 ICU 전체를 새 의존성으로 추가하면, 지금까지 Nori만 사용하던 애플리케이션의 배포 크기와 의존성 구성이 함께 바뀐다.

그렇다고 각 애플리케이션에서 색인 전 문자열에 `Normalizer.normalize(text, NFC)`를 호출하도록 맡기면 입력 경로마다 처리가 달라진다. 파일 적재에서는 정규화하지만 실시간 색인에서는 빠뜨리거나, index analyzer에는 적용하고 search analyzer에는 적용하지 않는 식의 차이가 생길 수 있다. 검색에 필요한 변환은 analyzer 구성 안에서 같은 방식으로 실행되는 편이 안전하다.

필요했던 것은 범용 정규화기가 아니라, Nori 사전 탐색을 막는 현대 한글의 결합 자모만 처리하는 필터였다.

## ICU 대신 한글 조합만 처리한 이유

이를 위해 `HangulCompositionCharFilter`를 구현했다. 이 필터는 `KoreanTokenizer`가 실행되기 전에 현대 한글의 결합 자모를 완성형 음절로 조합한다.

```text
ᄇ + ᅵ            → 비
ᄀ + ᅳ + ᆸ       → 급
ᄋ + ᅧ            → 여
```

변환을 거친 NFD 입력은 NFC 입력과 같은 Nori 사전 경로를 탄다.

```text
NFD 원문
→ HangulCompositionCharFilter
→ 완성형 한글
→ KoreanTokenizer
→ NFC 입력과 같은 term·품사 분석
```

처리 범위는 현대 한글의 L/V와 L/V/T 결합으로 제한했다. 호환 자모, 옛한글 자모, 중간이 빠진 불완전한 시퀀스까지 임의로 조합하면 필터가 원문의 의미를 추측하게 된다. 이미 완성형인 한글과 비한글 텍스트도 바꿀 이유가 없다.

이 범위 밖의 정규화가 필요하다면 ICU를 쓰는 것이 맞다. `HangulCompositionCharFilter`의 역할은 ICU를 대체하는 것이 아니라, ICU 의존성 없이 Nori가 현대 한글 NFD를 사전에서 찾게 만드는 것이다.

## 검색뿐 아니라 하이라이팅도 맞아야 했다

결합 자모를 완성형 음절로 바꾸면 문자열 길이가 줄어든다. NFD의 `ᄀ + ᅳ + ᆸ` 세 글자가 NFC의 `급` 한 글자가 되기 때문이다. 토큰만 올바르게 만들어도 offset을 변환된 문자열 기준으로 반환하면 검색 결과의 하이라이팅 위치가 원문과 어긋난다.

그래서 필터는 조합된 문자를 출력하는 것과 함께, 각 위치를 원래 NFD 입력의 offset으로 되돌리는 correction map을 유지한다. Analyzer가 `급`이라는 한 글자를 처리하더라도, 검색 화면에서는 원문의 `ᄀ + ᅳ + ᆸ` 전체 범위를 가리켜야 한다.

회귀 테스트도 단순히 최종 term만 비교하지 않았다.

- 같은 문장의 NFC와 NFD 입력이 동일한 term과 품사 태그를 만드는지 확인했다.
- NFD 입력에서 나온 token offset이 원래 입력 위치로 돌아가는지 확인했다.
- 임의로 생성한 현대 한글을 NFD로 분해한 뒤 다시 조합해 NFC와 비교했다.
- 호환 자모, 옛한글, 불완전한 시퀀스, 이미 완성된 한글이 바뀌지 않는지 확인했다.

## 이제 표현 방식이 검색 가능성을 바꾸지 않는다

이 수정은 [Apache Lucene #16242](https://github.com/apache/lucene/pull/16242)로 병합됐다. `analysis-nori` 사용자는 ICU 모듈을 추가하지 않고도 analyzer 앞에 `HangulCompositionCharFilter`를 선택해 NFD 한글을 NFC와 같은 방식으로 분석할 수 있다.

이 문제를 macOS 파일명의 자소분리 현상으로만 보면 놓치기 쉽다. 파일 업로드, OCR, 크롤러, 외부 API처럼 문자열을 전달하는 어느 단계에서도 정규화 형식은 달라질 수 있다. 화면에서 글자를 확인하는 것만으로는 발견할 수 없고, 검색 실패가 발생해도 로그에는 정상적인 문자열과 정상적인 analyzer 실행만 남는다.

한국어 문서를 여러 경로에서 적재한다면 같은 문장을 NFC와 NFD로 만들어 index analyzer와 search analyzer에 모두 넣어보는 테스트가 필요하다. 두 입력의 term, 품사, position, offset이 같아야 한다. 검색 시스템에서 유니코드 표현 방식은 문서가 검색될지 말지를 결정하는 정보가 되어서는 안 된다.

문자 표현을 맞춘 뒤에도 검색 의미가 보존된다는 보장은 없다. 다음 글에서는 Nori가 올바른 token graph를 만들고도 Elasticsearch가 position hole을 잃어 [원문 그대로의 `match_phrase`를 0건으로 만든 문제](/ko/posts/elasticsearch-nori-position-hole)를 다룬다.
