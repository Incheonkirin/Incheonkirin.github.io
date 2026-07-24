---
title: "Two correctness fixes and a scalability fix in sentence-transformers v5.6.0"
date: 2026-06-18
description: "Three merged fixes in hard-negative mining and GIST losses (#3816, #3817, #3821): a full similarity-matrix materialization, a missing rank offset in multi-GPU positive masking, and a sign-dependent relative margin."
---

Three of my fixes landed in sentence-transformers v5.6.0, all in the hard-negative mining and GIST loss code paths. Two fix wrong training behavior in the mining and GIST losses; one removes an out-of-memory ceiling.

## #3816: mining materialized the full similarity matrix

`mine_hard_negatives` without FAISS computed the full query-by-corpus similarity matrix in one allocation, and the memory cost scales with the product of the two sizes. The fix mirrors the FAISS branch: iterate over query chunks, keeping only the top candidates per chunk. In my local CPU benchmark (`all-MiniLM-L6-v2`, synthetic 10k queries by 100k documents), peak RSS dropped from 4.56 GB to 1.09 GB, and the mined output was identical in equivalence checks. Mined results are unchanged by design; this fix removes an out-of-memory ceiling, not a bias. [PR #3816](https://github.com/huggingface/sentence-transformers/pull/3816)

## #3817: multi-GPU GIST masked the wrong positives

GIST losses use a guide model to mask false negatives. With `gather_across_devices=True`, embeddings from all ranks are concatenated, so each anchor's true positive sits at an offset determined by the process rank. The positive mask did not apply that offset: on every rank above zero the mask pointed at another rank's rows. With a nonzero margin the unprotected true-positive logit became `-inf`, which yields an infinite loss term; with the default margin the wrong rows were filtered. Single-GPU runs were unaffected; the failure exists only with `gather_across_devices=True`. The fix applies the rank offset in both `GISTEmbedLoss` and `CachedGISTEmbedLoss`. The merged regression tests simulate rank 1 of a 2-process world in a single process; I also verified the red/green behavior locally on a 2-process gloo CPU run. [PR #3817](https://github.com/huggingface/sentence-transformers/pull/3817)

## #3821: the relative margin flipped for negative scores

Mining and GIST losses discarded negatives scoring above `positive_score * (1 - margin)`. For positive scores this is a threshold slightly below the positive. For negative positive-pair scores it lands above the positive: with a positive score of `-0.50` and `margin=0.05`, the threshold is `-0.475`, so a negative at `-0.49`, closer to the anchor than the positive itself, survives the filter. The fix is a sign-independent form, `positive_score - abs(positive_score) * margin`, identical for positive scores and correct for negative ones, applied in the three places that shared the expression (`mine_hard_negatives`, `GISTEmbedLoss`, `CachedGISTEmbedLoss`). [PR #3821](https://github.com/huggingface/sentence-transformers/pull/3821)

<!-- figure: three failure locations on one mining/loss pipeline diagram -->

## Regression properties

Each fix is pinned by a property test: mined output identity across memory strategies (#3816), single-GPU equivalence for the distributed mask (#3817), and threshold ordering across score signs (#3821). All three fail on the previous code and pass after the fixes.
