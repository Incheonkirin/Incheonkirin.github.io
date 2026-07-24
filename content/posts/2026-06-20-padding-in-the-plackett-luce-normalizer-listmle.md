---
title: "Padding was inflating the Plackett-Luce normalizer in ListMLE"
date: 2026-06-20
description: "sentence-transformers' ListMLE losses let padded slots contribute unit mass to every real document's normalizer, so loss and gradients depended on batch composition. Fixed in #3827, with maintainer-run NanoBEIR benchmarks for both affected losses."
---

A listwise reranker loss should give the same gradient for a query regardless of which other queries share its batch. In sentence-transformers' `ListMLELoss` and `PListMLELoss`, it did not: the loss of a fixed query changed with the document count of the longest other query in the batch.

## Mechanism

ListMLE maximizes the Plackett-Luce log-likelihood of the ground-truth ordering $\pi$ given scores $s$:

$$
\log P(\pi \mid s) = \sum_{i=1}^{n} \Big( s_{\pi(i)} - \log \sum_{j \geq i} e^{s_{\pi(j)}} \Big)
$$

The implementation scatters each list's logits into a `(batch_size, max_docs)` matrix and pads shorter lists with a logit of `1e-16`. Since $e^{10^{-16}} \approx 1$, every padded slot enters the reverse cumulative sum that forms the per-position normalizer with roughly unit mass, inflating the denominator of every real document's log-probability. The padding mask was applied after the cumulative sum (`log_probs[~mask] = 0.0`), which removes the padded positions' own terms but not their contribution to the real positions' normalizers.

For a single list with labels `[2, 1]` and logits `[1.5, 0.3]`, batched at different padding widths:

| `max_docs` | loss | grad |
| --- | --- | --- |
| 2 (no padding) | 0.2633 | `[-0.2315, +0.2315]` |
| 3 (1 pad) | 0.9759 | `[-0.3440, -0.2280]` |
| 4 (2 pads) | 1.4671 | |
| 6 (4 pads) | 2.1627 | |

The same list's loss grows with padding width and the second document's gradient flips sign. Variable-length lists are the normal case for reranker training data, so training ran on a corrupted signal whenever list lengths varied within a batch.

<!-- figure: normalizer contamination diagram (padded slots feeding the reverse cumsum) -->

## Fix

Zero the padded scores before the cumulative sum, with a mask in the same sorted order as the logits:

```python
scores = sorted_logits.exp().masked_fill(~sorted_mask, 0.0)
```

Zero mass in the normalizer is equivalent to the `-inf`-before-exp convention used by reference ListMLE implementations such as allRank. For lists with no padding the change is a no-op.

The regression test batches a 2-document query with a 3-document query and asserts the batched loss equals the mean of the two per-query losses, parametrized over `respect_input_order`. It fails on the previous code (4 failed) and passes with the fix (4 passed).

## Impact

Merged as [sentence-transformers #3827](https://github.com/huggingface/sentence-transformers/pull/3827). The maintainer fine-tuned `MiniLM-L12` rerankers on MS MARCO v1.1 (1 epoch, identical seed and config) with and without the fix, for both affected losses, and reported NanoBEIR R100 mean nDCG@10:

| Loss | no fix | with the fix |
| --- | --- | --- |
| ListMLE | ~0.39 | 0.529 |
| PListMLE | 0.514 | 0.525 |

The maintainer noted the ListMLE no-fix number came from an earlier run on older library versions and was not rerun, so the controlled comparison is the PListMLE row; the result was described as strictly greater than or equal to no-fix everywhere, and a genuine correctness win for ListMLE.
