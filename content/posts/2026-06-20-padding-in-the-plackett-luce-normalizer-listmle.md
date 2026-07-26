---
title: "The same query learned a different ranking when its batch changed"
seoTitle: "ListMLE padding bug in sentence-transformers: batch-dependent gradients"
date: 2026-06-20
description: "Padding entered the Plackett-Luce normalizer in sentence-transformers, making ListMLE loss and gradients depend on unrelated queries in the batch."
tags: [sentence-transformers, ListMLE, Learning-to-Rank, Reranking]
lang: en
translations:
  en: posts/2026-06-20-padding-in-the-plackett-luce-normalizer-listmle
  ko: ko/posts/sentence-transformers-listmle-padding
---

I held one query fixed: the same two documents, labels `[2, 1]`, and logits `[1.5, 0.3]`. Then I changed only the length of another query in its training batch.

The fixed query's loss changed from `0.2633` to `2.1627`. More seriously, the gradient of its second document changed sign.

| Batch padding width (`max_docs`) | Loss for the same query | Gradient |
| ---: | ---: | --- |
| 2, no padding | 0.2633 | `[-0.2315, +0.2315]` |
| 3, one padded slot | 0.9759 | `[-0.3440, -0.2280]` |
| 4, two padded slots | 1.4671 | — |
| 6, four padded slots | 2.1627 | — |

Nothing about the query, its documents, or its labels had changed. Only its batch neighbor had a longer list. A batching choice was changing the learning objective and, in one position, reversing the optimization direction.

That violates a basic invariant of listwise learning-to-rank: padding may change how efficiently examples are packed, but it must not change what any example teaches the model.

## Why an almost-zero padding value was not harmless

`ListMLELoss` and `PListMLELoss` in sentence-transformers accept variable-length document lists. To batch them, the implementation scattered each query's logits into a matrix of shape `(batch_size, max_docs)` and filled unused positions with `1e-16`.

At first glance, `1e-16` looks indistinguishable from zero. The catch is that it was used as a **logit**, not as probability mass. The Plackett-Luce likelihood exponentiates logits before building each choice-set denominator:

$$
\log P(\pi \mid s) = \sum_{i=1}^{n}
\left(s_{\pi(i)} - \log \sum_{j \geq i} e^{s_{\pi(j)}}\right)
$$

Exponentiation changes the meaning of the padding value:

```text
padding logit = 1e-16
exp(1e-16)    ≈ 1
```

Every empty slot therefore entered the denominator with almost unit mass—as if it were another document competing to be ranked. The longer the longest list in a batch, the more phantom documents were added to every shorter query.

## The mask existed, but it ran one operation too late

The implementation did have a padding mask. That initially made the result look safe. Following the tensor operations showed why it was not.

The code first exponentiated the padded logits and included them in a reverse cumulative sum. Only afterward did it clear the log-probability terms at padded positions. The mask prevented empty slots from contributing their **own loss terms**, but their mass had already contaminated the normalizers of real documents.

```text
old path
padded logits
→ exp
→ reverse cumsum, including padding
→ log probabilities
→ clear padded loss terms
```

This explains both symptoms in the reproduction. Each additional pad increased the denominator and inflated the loss. Because the denominator also determines every real document's derivative, enough padding could flip a gradient's sign.

## Removing padding from the choice set

The correction is one line, but its location matters. I masked the exponentiated scores **before** the cumulative sum:

```python
scores = sorted_logits.exp().masked_fill(~sorted_mask, 0.0)
```

A padded position now contributes zero probability mass. This is equivalent to assigning its logit negative infinity before exponentiation, a common convention in reference ListMLE implementations. If a list has no padding, the change is a no-op.

```text
fixed path
padded logits
→ exp
→ replace padded scores with zero
→ reverse cumsum over real documents only
→ log probabilities
```

The important part is not that the padding value became smaller. It is that padding is no longer a member of the Plackett-Luce choice set.

## The regression test checks the invariant, not one number

A test that asserts only the loss from one fixed tensor could pass while a future change reintroduces batch dependence elsewhere. I instead encoded the property the loss must preserve.

The test evaluates a two-document query by itself, evaluates a three-document query by itself, and then evaluates them together in a padded batch. The batched loss must equal the mean of the two independent losses. The check runs for both affected loss classes and for `respect_input_order=True` and `False`.

All four cases failed on the previous implementation and passed after the mask moved ahead of the normalizer. That gives the fix a useful boundary: list length and batch composition can vary, while the per-query objective remains the same.

## What the benchmark showed—and what it did not

The fix was merged as [sentence-transformers #3827](https://github.com/huggingface/sentence-transformers/pull/3827). During review, maintainer Tom Aarsen fine-tuned `MiniLM-L12` rerankers for one epoch on MS MARCO v1.1 and reported NanoBEIR R100 mean nDCG@10 at the best checkpoint:

| Loss | Without fix | With fix |
| --- | ---: | ---: |
| ListMLE | ~0.39 | 0.529 |
| PListMLE | 0.514 | 0.525 |

The PListMLE row is the controlled comparison: identical seed and configuration, with the fix reverted for the baseline. The ListMLE baseline came from an older sentence-transformers/Transformers setup and was not rerun, so `0.39 → 0.529` should not be presented as a controlled improvement.

The benchmark is useful confirmation that removing the invalid probability mass did not merely make a synthetic test cleaner; it also improved or matched the measured retrieval runs. But the correctness case does not depend on the size of that improvement. Even if aggregate nDCG had stayed flat, an unrelated query's length still must not decide the loss and gradient of the current query.

Batching should change throughput, not the ranking a query teaches. The same upstream release contained two more correctness fixes and a scalability change; I trace those interactions in [three fixes shipped with sentence-transformers v5.6.0](/posts/2026-06-18-three-fixes-in-sentence-transformers-v56).
