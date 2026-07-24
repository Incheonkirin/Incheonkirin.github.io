---
title: "Searching 비급여 returns 급여: nori's default stoptags drop Korean negation prefixes"
date: 2026-06-16
description: "Elasticsearch's default Korean analyzer removes the XPN part-of-speech tag, which deletes negation prefixes like 비/무/미 and merges antonyms at index time. Documented upstream in Elasticsearch #151157."
---

While building a search system over insurance policy documents, I noticed that searching 비급여 (non-covered) returned 급여 (covered) clauses, and the other way around. Two words with opposite meanings had become the same word inside the engine.

## Reproduction

One `_analyze` call shows it, on Elasticsearch's default Korean configuration:

```
GET _analyze
{
  "analyzer": "nori",
  "text": "비급여"
}
```

The output is a single token: `급여`. The prefix 비 is gone. 부담보 (exclusion of coverage) loses its prefix the same way and becomes 담보 (coverage). Because this happens identically at index time and at query time, covered and non-covered documents are indistinguishable in the index.

In the corpus of 114 insurance policy documents I work with, 비급여 appears 76 times. Coverage status is the axis these documents exist to express, so merging the two terms returns clauses whose coverage meaning is inverted relative to the query.

<!-- figure: token decomposition diagram (비급여 → 비/XPN + 급여/NNG, XPN removed) -->

## Root cause

The nori tokenizer decomposes 비급여 into 비 (XPN, a noun prefix) plus 급여 (NNG, a common noun). As morphological analysis, that is correct. The problem is one step later: the part-of-speech filter `nori_part_of_speech` ships with a default stoptag list that includes XPN.

Removing weak-signal parts of speech by default is reasonable for determiners and particles. But Korean negation prefixes are commonly tagged XPN, and they are not weak signals: they flip the meaning of the noun they attach to. The upstream documentation demonstrates this for 비(非) and 부(不); other XPN-tagged prefixes are subject to the same filter. The default drops them without any indication.

This is not a bug. From the dictionary and tagset's point of view the behavior is consistent, and `stoptags` is configurable. The problem was that none of this was documented, so any team starting Korean search from nori defaults hit the same behavior without warning.

## Fix

The right change was documentation, not a new default. Changing default stoptags would break compatibility with existing indexes, and keeping all XPN tokens would admit other noise. The warning is now in the official nori documentation: [elastic/elasticsearch #151157](https://github.com/elastic/elasticsearch/pull/151157), merged 2026-06-15.

The operational prescription is short. In domains where meaning inversion matters (insurance, legal, medical), set `stoptags` explicitly and consider removing XPN from the list. Whether the extra prefix tokens add noticeable noise is a per-domain question; measure recall and precision on your own corpus.

## Takeaway

Getting from the symptom (wrong coverage results) to the root cause (one default tag) required nothing more than `_analyze`. A large share of Korean search quality problems originate in the analyzer layer before ranking is involved, and English-language test suites do not exercise this class of failure.

A second failure in the same corpus, a `match_phrase` for a string copied verbatim from a document returning zero hits, traced to Elasticsearch's query construction. That one became its own fix, written up in [a later post](2026-07-15-elasticsearch-nori-position-hole).
