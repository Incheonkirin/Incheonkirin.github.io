---
title: "같은 쿼리인데 배치가 바뀌자 ListMLE gradient가 달라졌다"
seoTitle: "sentence-transformers ListMLE padding 버그: batch에 따라 gradient가 달라진 이유"
date: 2026-06-20
description: "padding이 Plackett-Luce normalizer에 들어가면서 같은 쿼리의 ListMLE loss와 gradient가 batch 구성에 따라 달라진 원인과 수정 과정을 설명합니다."
tags: [sentence-transformers, ListMLE, Learning-to-Rank, Reranking]
lang: ko
translations:
  en: posts/2026-06-20-padding-in-the-plackett-luce-normalizer-listmle
  ko: ko/posts/sentence-transformers-listmle-padding
---

한 쿼리를 고정했다. 문서 두 개, label `[2, 1]`, logit `[1.5, 0.3]`은 그대로 두고 같은 학습 배치에 들어가는 다른 쿼리의 문서 수만 바꿨다.

고정해 둔 쿼리의 loss가 `0.2633`에서 `2.1627`까지 달라졌다. 더 심각한 것은 두 번째 문서의 gradient 부호까지 바뀌었다는 점이다.

| 배치의 padding 폭 (`max_docs`) | 같은 쿼리의 loss | Gradient |
| ---: | ---: | --- |
| 2, padding 없음 | 0.2633 | `[-0.2315, +0.2315]` |
| 3, padding 1개 | 0.9759 | `[-0.3440, -0.2280]` |
| 4, padding 2개 | 1.4671 | — |
| 6, padding 4개 | 2.1627 | — |

쿼리도, 문서도, 정답 순서도 바뀌지 않았다. 함께 묶인 다른 쿼리의 목록이 길어졌을 뿐인데 이 쿼리가 모델에 주는 학습 신호가 달라졌고, 한 위치에서는 최적화 방향이 반대로 뒤집혔다.

Listwise learning-to-rank에서 지켜져야 할 조건은 단순하다. Padding은 여러 쿼리를 빠르게 계산하기 위한 장치일 뿐, 각 쿼리가 무엇을 학습시키는지는 바꾸면 안 된다.

## 0에 가까운 padding 값인데 왜 영향을 줬을까

sentence-transformers의 `ListMLELoss`와 `PListMLELoss`는 쿼리마다 문서 수가 다른 입력을 받는다. 이를 하나의 배치로 만들기 위해 각 쿼리의 logit을 `(batch_size, max_docs)` 행렬에 담고, 비어 있는 위치를 `1e-16`으로 채웠다.

`1e-16`만 보면 사실상 0처럼 보인다. 문제는 이 값이 확률이 아니라 **logit**이었다는 데 있다. Plackett-Luce likelihood는 각 순위의 선택 확률을 계산하기 전에 logit을 지수화한다.

$$
\log P(\pi \mid s) = \sum_{i=1}^{n}
\left(s_{\pi(i)} - \log \sum_{j \geq i} e^{s_{\pi(j)}}\right)
$$

지수화를 거치면 padding 값의 의미가 완전히 달라진다.

```text
padding logit = 1e-16
exp(1e-16)    ≈ 1
```

비어 있는 칸 하나가 normalizer 안에서는 확률 질량이 거의 1인 문서 하나로 취급됐다. 배치에서 가장 긴 쿼리의 문서 수가 늘어날수록 짧은 쿼리마다 존재하지 않는 경쟁 문서가 더 많이 붙는 구조였다.

## 마스크는 있었지만 한 단계 늦었다

구현에는 이미 padding mask가 있었다. 처음 코드를 보면 padding이 제외되는 것처럼 보이는 이유다. 실제 tensor 연산 순서를 따라가 보니 마스크가 적용되는 시점이 문제였다.

기존 코드는 padding logit을 먼저 지수화한 뒤, 그 값까지 포함해 reverse cumulative sum을 만들었다. 그 다음에야 padding 위치의 log probability를 0으로 지웠다. Padding 위치의 **loss 항 자체**는 사라졌지만, 실제 문서의 normalizer에 들어간 확률 질량은 이미 남아 있었다.

```text
기존 계산
padding이 포함된 logits
→ exp
→ padding까지 포함한 reverse cumsum
→ log probability
→ padding 위치의 loss 항 제거
```

이 순서가 재현 결과를 그대로 설명한다. Padding이 늘 때마다 분모가 커져 loss가 증가했다. 같은 분모가 실제 문서의 미분값에도 영향을 주기 때문에, padding이 충분히 늘면 gradient 부호까지 바뀔 수 있었다.

## Padding을 선택 후보에서 완전히 제외했다

수정 코드는 한 줄이지만 적용 위치가 핵심이다. 지수화된 score를 cumulative sum에 넣기 전에 padding 위치를 0으로 만들었다.

```python
scores = sorted_logits.exp().masked_fill(~sorted_mask, 0.0)
```

이제 padding은 normalizer에 어떤 확률 질량도 더하지 않는다. 지수화 전에 padding logit을 음의 무한대로 두는 방식과 같은 결과이고, padding이 없는 목록에서는 기존 계산과 완전히 동일하다.

```text
수정된 계산
padding이 포함된 logits
→ exp
→ padding score를 0으로 변경
→ 실제 문서만 reverse cumsum
→ log probability
```

중요한 것은 padding 값을 더 작은 수로 바꾼 것이 아니다. 존재하지 않는 문서를 Plackett-Luce의 선택 후보에서 제거한 것이다.

## 특정 loss 값이 아니라 batch invariance를 테스트했다

특정 tensor 하나의 loss만 고정값과 비교하면, 이후 구현이 바뀌었을 때 다른 경로에서 같은 문제가 다시 생겨도 놓칠 수 있다. 그래서 회귀 테스트에는 이 loss가 지켜야 할 성질을 직접 넣었다.

문서가 두 개인 쿼리와 세 개인 쿼리를 각각 계산한 뒤, 두 쿼리를 padding이 있는 하나의 배치로 묶어 다시 계산했다. 배치 loss는 두 개별 loss의 평균과 같아야 한다. 이 검사를 `ListMLELoss`와 `PListMLELoss`, `respect_input_order=True`와 `False`의 네 조합에 모두 적용했다.

기존 구현에서는 네 경우가 모두 실패했고, 수정 뒤에는 모두 통과했다. 이제 목록 길이와 배치 구성은 달라질 수 있지만 각 쿼리의 학습 목적은 변하지 않는다.

## 성능 수치는 어디까지 말할 수 있을까

수정은 [sentence-transformers #3827](https://github.com/huggingface/sentence-transformers/pull/3827)로 병합됐다. 리뷰 과정에서 maintainer Tom Aarsen이 `MiniLM-L12` reranker를 MS MARCO v1.1로 1 epoch 학습하고, best checkpoint의 NanoBEIR R100 mean nDCG@10을 비교했다.

| Loss | 수정 전 | 수정 후 |
| --- | ---: | ---: |
| ListMLE | ~0.39 | 0.529 |
| PListMLE | 0.514 | 0.525 |

여기서 같은 seed와 설정으로 fix만 되돌려 비교한 것은 PListMLE의 `0.514 → 0.525`다. ListMLE의 `~0.39`는 이전 sentence-transformers와 Transformers 버전에서 얻은 과거 실행 결과이고, 같은 환경에서 다시 측정한 baseline이 아니다. 따라서 `0.39 → 0.529`를 통제된 성능 향상으로 표현해서는 안 된다.

이 benchmark는 잘못된 확률 질량을 제거한 수정이 실제 retrieval 학습에서도 성능을 떨어뜨리지 않고 개선으로 이어졌다는 확인이다. 하지만 correctness의 근거가 성능 향상 폭에 달린 것은 아니다. 평균 nDCG가 같게 나왔더라도, 무관한 다른 쿼리의 길이가 현재 쿼리의 loss와 gradient를 바꾸는 계산은 고쳐야 한다.

배치는 처리량을 바꿀 수는 있어도 쿼리가 가르치는 순위를 바꾸면 안 된다. 같은 upstream release에 들어간 다른 두 correctness 수정과 한 가지 확장성 개선은 [sentence-transformers v5.6.0에 병합된 세 가지 문제](/posts/2026-06-18-three-fixes-in-sentence-transformers-v56)에서 이어서 다룬다.
