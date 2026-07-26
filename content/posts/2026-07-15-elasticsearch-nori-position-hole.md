---
title: "Zero Hits for the Exact Source Text: Position Holes in Elasticsearch nori"
date: 2026-07-15
description: "Why exact phrase search failed when position holes disappeared from the token graph built by nori mixed decompounding and the part-of-speech filter, and how the fix landed in Elasticsearch."
lang: en
translations:
  en: posts/2026-07-15-elasticsearch-nori-position-hole
  ko: ko/posts/elasticsearch-nori-position-hole
---

A document contained the exact string `보험계약대출이율` (insurance policy loan interest rate). `match` found the document, and `match_phrase` found it at `slop=1`. The same string in `match_phrase` with `slop=0` returned 0 hits.

This was not a scoring or recall problem. A single piece of position information was being dropped while Elasticsearch converted the analyzer's token graph into a phrase query.

## Minimal reproduction

On Elasticsearch 8.15.3 and Lucene 9.11.1, I created an index with a single document. The analyzer was configured as follows.

- `nori_tokenizer`, `decompound_mode=mixed`
- `nori_readingform`
- `lowercase`
- `nori_part_of_speech`

`mixed` mode emits the original compound alongside its decomposed tokens. The part-of-speech filter removes the particle `이`. The analysis output contains both a graph and a position hole.

| Token | Position | Note |
|---|---:|---|
| 보험계약 | 0 | original compound, `positionLength=2` |
| 보험 | 0 | decomposed path |
| 계약 | 1 | decomposed path |
| 대출 | 2 | |
| 이 | 3 | removed by the part-of-speech filter |
| 율 | 4 | |

Running three queries with the same source text produced the following.

| Query | Result |
|---|---:|
| `match` | 1 hit |
| `match_phrase`, `slop=0` | 0 hits |
| `match_phrase`, `slop=1` | 1 hit |

Removing the graph or removing the part-of-speech filter restored the match at `slop=0`. Only when both conditions were present did the position relationships in the phrase query change.

## Token stream vs. query tree

Feeding the same token stream directly into Lucene's `QueryBuilder.createPhraseQuery` preserved the position hole.

```text
text:"보험계약 대출 ? 율" text:"보험 계약 대출 ? 율"
```

The `?` marks the position of the removed particle `이`. The decomposed path carries positions `보험@0 계약@1 대출@2 율@4`, matching the indexed positions.

Rewriting the `slop=0` query in Elasticsearch produced a different structure.

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

Both graph paths remain, but the one-position gap between `대출` (loan) and `율` (rate) is missing. The query requires the two tokens to be adjacent, while the index keeps the removed particle's position between them, so the phrase did not match.

`slop=1` was not a fix. It widens the tolerance for the entire phrase and at the same time switches Elasticsearch's internal execution to the finite-strings path. That path preserves the position hole, which is why the query returned the document.

## Root cause

`MatchQueryParser`'s graph phrase handling contained two separate defects.

The first was gap placement in `createSpanQuery`. A gap found on the next token was added before the preceding clause instead of after it. The `SpanGap` entered one clause early, creating position relationships different from the token stream.

The second was the outer assembly in `analyzeGraphPhrase`. After splitting the token graph at articulation points, the code joined the segments without reading the `PositionIncrementAttribute` between them. Gaps created outside a side path were dropped entirely from the final `SpanNearQuery`.

Fixing only one side leaves the same problem for other graph shapes. The fix preserves position increments on both paths.

- Added the pending clause first, then inserted the `SpanGap` at the correct position.
- Assembled the segments outside the graph with `SpanNearQuery.Builder` as well, passing position increments through.
- Counted the added gap clauses to match the final clause count.

## Regression tests

I organized the regression tests by graph position rather than tying them to one specific Korean string.

- a gap before, inside, and after a graph side path
- multiple gaps around a graph segment
- a stop filter removing tokens after `synonym_graph`
- an end-to-end reproduction combining nori mixed decompounding and the part-of-speech filter
- a stop filter placed before the synonym filter, which query construction cannot recover

The last item is a control that marks the boundary of the fix. When analyzer ordering prevents the synonym rule itself from matching, the query builder cannot repair it.

The fix was merged as [Elasticsearch #152931](https://github.com/elastic/elasticsearch/pull/152931). Alongside the `MatchQueryParser` change, it included 197 added lines of unit tests and a 46-line nori YAML REST test. The reproduction data and query trees are available in the [public case study](https://github.com/Incheonkirin/korean-search-correctness/tree/main/case_studies/korean-retrieval-correctness).

## Detection

A single search result or one aggregate metric rarely surfaces this problem. Bag-of-words retrieval does not use positions, and phrase tests without a graph never enter the affected code path. In an overall nDCG figure, other candidate documents can mask a miss on the exact-phrase path.

When verifying phrase search correctness, inspect four artifacts together.

```text
source text
→ analyzed token graph
→ compiled query tree
→ matched documents
```

An analyzer producing correct tokens does not by itself preserve search semantics. Position relationships can change at the query construction stage, before ranking is involved.

Related failures at earlier boundaries: [NFD Hangul misses nori's dictionary](2026-06-30-nfd-hangul-and-noris-dictionary), and [the default XPN stoptag collapses 비급여 into 급여](2026-06-16-noris-default-stoptags-drop-korean-negation-prefixes). The [Korean search correctness guide](../ko/korean-search-correctness) connects all three.
