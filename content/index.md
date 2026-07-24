---
title: Mingi Jeong
description: "Failure reports from Korean search and ML serving: bugs reproduced, traced to their source, and fixed."
---

A query for 비급여 (non-covered) returns clauses about 급여 (covered). A sentence copied verbatim from a document returns zero hits. Korean's agglutinative structure exposes failures across the search and serving stack—failures that aggregate metrics can miss. This blog documents how they were reproduced, traced, and fixed.

## Writing

### [Verbatim search returns zero hits: position holes in Elasticsearch nori](posts/2026-07-15-elasticsearch-nori-position-hole)

With nori's mixed decompounding and a POS filter enabled, a `match_phrase` for the original text returned zero hits. I fixed the two paths where token-graph position holes were lost in span queries and added regression tests.

_Elasticsearch · Nori · Retrieval · 2026.07_


### [An FDS dataset solvable with 48 transaction amounts: auditing 6.38M AI-Hub records](posts/2026-07-15-aihub-fds-dataset-validity)

I audited 6.38 million records of AI-Hub's financial anomaly dataset. 4.43M interbank-network rows contained only 48 distinct transaction amounts, and the bracket covering 98.97% of the data had zero positives.

_Fraud Detection · Data Validation · 2026.07_


### [Snapshotting generation output in Transformers continuous batching](posts/2026-07-14-snapshotting-generation-output-in-transformers-continuous-batching)

Already-streamed chunks changed retroactively, and soft-reset requests stopped before `max_new_tokens`. I replaced the per-token output transform with a snapshot.

_Transformers · Serving · 2026.07_


### [When a normalizer turns fullwidth characters into wildcard operators](posts/2026-07-20-wildcard-operators-from-a-normalizer)

A `keyword` field with a normalizer that folds fullwidth forms to ASCII made `wildcard` queries over-match or return zero hits, because normalized operators were not re-escaped. Fixed and backported to four release lines.

_Elasticsearch · Wildcard · CJK · 2026.07_

### [NFD Hangul does not match nori's dictionary: a composition char filter for Lucene](posts/2026-06-30-nfd-hangul-and-noris-dictionary)

Korean text in NFD form fails nori's dictionary lookup and falls back to UNKNOWN tokens, so NFC queries miss NFD-indexed text. Lucene #16242 adds an opt-in char filter that composes conjoining jamo before tokenization.

_Lucene · Nori · Unicode · 2026.06_


### [Padding was inflating the Plackett-Luce normalizer in ListMLE](posts/2026-06-20-padding-in-the-plackett-luce-normalizer-listmle)

Padded slots contributed unit mass to every real document's normalizer, so loss and gradients depended on batch composition. The maintainer benchmarked both affected losses on NanoBEIR after the fix.

_sentence-transformers · Ranking loss · 2026.06_


### [Two correctness fixes and a scalability fix in sentence-transformers v5.6.0](posts/2026-06-18-three-fixes-in-sentence-transformers-v56)

A full similarity-matrix materialization, a missing rank offset in multi-GPU positive masking, and a sign-dependent relative margin, all merged in one release.

_sentence-transformers · Mining · GIST · 2026.06_



### [Searching 비급여 returns 급여: nori's default stoptags drop Korean negation prefixes](posts/2026-06-16-noris-default-stoptags-drop-korean-negation-prefixes)

Elasticsearch's default Korean analyzer removes the XPN tag, deleting negation prefixes and merging antonyms at index time. The behavior is now documented upstream.

_Elasticsearch · Nori · Korean · 2026.06_


### [Managing unreviewed cases as a third label](posts/2026-02-17-when-negative-labels-cant-be-trusted-pu-learning)

Labeling cases that are merely awaiting review as negatives turns past investigation policy into the model's ground truth. I split "unreviewed" into its own label and measured the selection bias.

_Label Quality · PU Learning · 2026.02_


### [Choosing a model when positives are 0.5%](posts/2026-02-16-choosing-a-model-at-0.5-percent-positives)

The investigation team can process 100 cases a day. This post turns model metrics into an actual investigation policy under that capacity.

_Model Evaluation · Precision@K · 2026.02_

