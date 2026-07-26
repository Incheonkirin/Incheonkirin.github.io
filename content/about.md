---
title: Profile
seoTitle: "Mingi Jeong — Search & Applied ML Engineering Profile"
description: Korean search and ML systems engineer. 5.5 years of Korean search and question answering, production ML at MetLife, 18 external patches merged into Lucene, Elasticsearch, sentence-transformers, Transformers, MLflow, and LlamaIndex.
---

I am a Korean search and ML systems engineer. I spent five and a half years at 42Maru building Korean search and question-answering systems, and I now develop ML models for the insurance business at MetLife and own their operation, monitoring, and iteration after deployment.

## MetLife · Data Scientist · 2024–present

I build and operate models for customer retention, sales activity, and risk review, tracking operational metrics and data drift in production and reworking the recurring operations around them.

Beyond modeling, I work on enterprise AI-use standards and review processes, and help business teams understand and actually use AI in their work.

## 42Maru · Search / Question Answering · 2019–2024

I built query interpretation with structured search expressions and dictionaries and tuned BM25. I designed evaluation sets to measure ranking quality, and worked across the search stack: RAG, MRC, and unstructured-data pipelines. [DSME semantic question answering](http://www.aitimes.kr/news/articleView.html?idxno=13427) and [Hana Bank OCR-NLP](https://www.venturesquare.net/844917) are projects from this period.

Failure cases collected from the question-answering system fed into national dataset projects I worked on, which released 5 datasets with about 2.27M question–answer pairs through NIA AI-Hub. KAIST and KakaoBank's [K-FinHallu](https://arxiv.org/abs/2605.29523) uses dataset 71610, and ACL FinNLP 2024's [FINALE](https://aclanthology.org/2024.finnlp-2.9/) cites datasets 71610, 71568, and 71565.

## Public engineering

I turn problems found in insurance policy documents and Korean-language queries into reproducible tests and upstream fixes. 18 external patches have been merged into Lucene, Elasticsearch, sentence-transformers, Transformers, MLflow, and LlamaIndex.

The Unicode, morphology, token-graph, and wildcard failures are connected in an [Elasticsearch·Lucene Korean search correctness guide](ko/korean-search-correctness).

- [sentence-transformers #3827](https://github.com/huggingface/sentence-transformers/pull/3827): excluded padding from the Plackett-Luce normalizer in ListMLE losses. The maintainer's NanoBEIR benchmark measured mean nDCG@10 of 0.529 for the fixed ListMLE (against a ~0.39 baseline from older library versions) and 0.525 vs 0.514 in the controlled PListMLE comparison. [Post](posts/2026-06-20-padding-in-the-plackett-luce-normalizer-listmle)
- [Apache Lucene #16242](https://github.com/apache/lucene/pull/16242): added `HangulCompositionCharFilter` to analysis-nori so NFD-decomposed Hangul analyzes like NFC text. [Post](posts/2026-06-30-nfd-hangul-and-noris-dictionary)
- [Elasticsearch #151157](https://github.com/elastic/elasticsearch/pull/151157): documented nori's default XPN stoptag behavior, in which Korean negation prefixes are dropped and antonyms like 비급여/급여 merge at index time. [Post](posts/2026-06-16-noris-default-stoptags-drop-korean-negation-prefixes)
- [Elasticsearch #152931](https://github.com/elastic/elasticsearch/pull/152931): fixed token-graph position holes that made verbatim `match_phrase` queries return zero hits. [Post](posts/2026-07-15-elasticsearch-nori-position-hole)
- [Transformers #46670](https://github.com/huggingface/transformers/pull/46670): fixed continuous-batching state management where already-streamed output changed retroactively and soft-reset requests ended early. [Post](posts/2026-07-14-snapshotting-generation-output-in-transformers-continuous-batching)
- [sentence-transformers v5.6.0](https://github.com/huggingface/sentence-transformers/releases/tag/v5.6.0): two correctness fixes and a scalability fix in hard-negative mining and GIST losses (#3816, #3817, #3821). [Post](posts/2026-06-18-three-fixes-in-sentence-transformers-v56)

## Technical scope

`Korean search` · `Retrieval correctness` · `Applied ML` · `Model operations` · `Python` · `PyTorch` · `Databricks`

## Contact

[GitHub](https://github.com/incheonkirin) · [LinkedIn](https://www.linkedin.com/in/mingi-jeong-8a9210180/) · [incheonkirin@gmail.com](mailto:incheonkirin@gmail.com)
