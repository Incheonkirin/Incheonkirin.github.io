---
title: "NFD Hangul does not match nori's dictionary: a composition char filter for Lucene"
date: 2026-06-30
description: "Korean text in NFD form fails nori's precomposed-syllable dictionary lookup and falls back to UNKNOWN tokens, so NFD-indexed text never matches NFC analysis. Apache Lucene #16242 adds an opt-in HangulCompositionCharFilter to analysis-nori."
---

Two Korean strings can be visually identical and byte-different. 비급여 (non-covered) in NFC is three precomposed syllables (U+BE44 U+AE09 U+C5EC). The same text that passed through macOS file APIs or certain pipelines arrives in NFD: each syllable decomposed into conjoining jamo (비 becomes U+1107 U+1175, and so on). Rendered on screen, you cannot tell them apart.

nori's dictionary operates on precomposed syllables, so NFD input fails dictionary lookup and falls back to `UNKNOWN` whitespace-delimited eojeol tokens instead of morphological analysis. The consequence is a mismatch: text indexed in NFD form does not match the analysis of the equivalent NFC text, so NFC queries miss NFD-ingested documents, and nothing in the indexing pipeline reports an error.

<!-- figure: NFC vs NFD codepoint comparison for 비급여 -->

## Fix

The general answer is Unicode normalization with ICU's `ICUNormalizer2CharFilter`. But analysis-nori does not depend on the ICU module, and pulling in the full ICU dependency to fix one Korean-specific case is a heavy trade.

[Apache Lucene #16242](https://github.com/apache/lucene/pull/16242) (merged 2026-06-29) adds an opt-in `HangulCompositionCharFilter` to analysis-nori. It composes modern L/V and L/V/T conjoining-jamo sequences into precomposed syllables before `KoreanTokenizer` runs, so NFD-form Korean analyzes like the equivalent NFC text, and it preserves offset correction back to the original input so highlighting still points at the right characters.

The filter is intentionally narrow. Compatibility jamo, archaic jamo, partial sequences, already-precomposed text, and non-Hangul text pass through unchanged. If you need general normalization, ICU remains the right tool; this covers the common Korean-only case without adding the dependency to nori deployments.

## Tests

The test set pins the equivalence and the boundaries:

- an NFD Korean sentence through the filter plus `KoreanTokenizer` produces the same terms and POS tags as the NFC sentence through `KoreanTokenizer` alone
- offsets from analyzed NFD text map back to the original NFD input
- randomized modern-Hangul NFD composition matches NFC
- non-modern jamo, partial sequences, already-NFC input, and precomposed-LV plus trailing jamo are unchanged

## Recommendation

If your corpus ingests text from macOS or cross-platform sources, check which normalization form actually reaches your analyzer, and add a paired NFC/NFD analyzer test for any source that can emit decomposed Hangul. NFC queries simply miss NFD-indexed documents, and no error is raised anywhere in the pipeline.
