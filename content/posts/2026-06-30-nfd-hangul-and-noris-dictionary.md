---
title: "Why identical Korean text produced different Elasticsearch results"
seoTitle: "NFD Hangul search failures in Lucene Nori: cause and fix"
date: 2026-06-30
description: "NFD Hangul bypassed Lucene Nori's dictionary and silently disappeared from NFC searches. This is how I traced the mismatch and fixed it without adding ICU."
tags: [Lucene, Elasticsearch, Nori, Korean-Search, Unicode]
lang: en
translations:
  en: posts/2026-06-30-nfd-hangul-and-noris-dictionary
  ko: ko/posts/lucene-nfd-hangul-search
---

I sent `보험계약대출이율` through the Nori analyzer twice. Both inputs rendered as the same Korean word. One produced the expected morphemes; the other remained a single unknown token.

```text
보험계약@0(len2) 보험@0 계약@1 대출@2 율@4

보험계약대출이율@0
```

The second line still looks like `보험계약대출이율` in a browser. The difference is how the string is represented: the first input uses precomposed Hangul syllables in NFC, while the second uses decomposed leading, vowel, and trailing jamo in NFD.

This was not merely an analyzer-output curiosity. If a document was indexed in NFD, its one unknown token could not match the `보험`, `계약`, `대출`, and `율` tokens produced from an NFC query. A word visibly present in the document disappeared from search, and neither Lucene nor Elasticsearch reported an error.

## The same word reached only one side of Nori's dictionary

Python's standard library makes the hidden representation difference visible:

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

In NFC, `비` is one code point, `U+BE44`. In NFD, it is the sequence `U+1107 U+1175`. The strings become equivalent after Unicode normalization, but before that step their lengths and code points differ.

Nori's `KoreanTokenizer` looks words up in a dictionary built from precomposed syllables. The NFC input can follow the dictionary path and be decompounded into known morphemes. The conjoining-jamo sequence in the NFD input cannot reach the same entries, so Nori falls back to an `UNKNOWN` token for the whitespace-delimited eojeol.

The dictionary was not missing a Korean word. The input representation prevented that word from reaching the dictionary at all.

## Why not normalize every input to NFC before indexing?

The obvious answer is Unicode normalization. Lucene already provides ICU's `ICUNormalizer2CharFilter`, which handles NFC and much broader normalization. For a deployment that already uses the ICU analysis module, that remains the right solution.

But `analysis-nori` does not depend on ICU. Adding the full ICU module to solve one Korean-specific case would change the dependency and deployment footprint for every application that only needed Nori.

Normalizing strings in application code was also an incomplete fix. A batch file loader might normalize while a real-time ingestion path does not, or an index analyzer might receive NFC while its search analyzer still receives NFD. A transformation required for search correctness is safer when it is declared in the analyzer and runs identically on every path.

The missing piece was narrower than a general-purpose normalizer: compose only the modern conjoining jamo that keep Nori from performing its dictionary lookup.

## Why the fix composes Hangul instead of replacing ICU

I implemented `HangulCompositionCharFilter` to run before `KoreanTokenizer`. It composes modern L/V and L/V/T sequences into precomposed syllables:

```text
ᄇ + ᅵ            → 비
ᄀ + ᅳ + ᆸ       → 급
ᄋ + ᅧ            → 여
```

That puts NFD input onto the same dictionary path as its NFC equivalent.

```text
NFD source
→ HangulCompositionCharFilter
→ precomposed Hangul
→ KoreanTokenizer
→ the same terms and POS tags as NFC
```

The scope is deliberately limited to modern Hangul composition. Compatibility jamo, archaic jamo, incomplete sequences, already-precomposed syllables, and non-Hangul text pass through unchanged. Guessing how to complete or reinterpret those inputs would make the filter alter meaning rather than representation.

This filter does not replace ICU. ICU is still the correct choice when a system needs general Unicode normalization. The new filter gives Nori users one dependency-free way to make modern NFD Hangul reachable by the Korean dictionary.

## Search correctness also had to preserve highlighting

Composition changes string length. The three-code-point NFD sequence `ᄀ + ᅳ + ᆸ` becomes the single NFC syllable `급`. Producing the right token is not enough if its offsets now point into the transformed string rather than the original document; search highlighting would select the wrong range.

The filter therefore records an offset-correction map while it emits composed syllables. Nori can analyze the one-character `급`, while Lucene still maps its token boundaries back to the full three-code-point range in the original NFD text.

The regression suite checks more than final terms:

- the same sentence in NFC and filtered NFD produces the same terms and part-of-speech tags
- token offsets from NFD input map back to the original source positions
- randomly generated modern Hangul survives NFD decomposition and recomposition exactly
- compatibility jamo, archaic jamo, incomplete sequences, and already-composed text remain unchanged

## A storage detail no longer decides whether a document can be found

The change was merged as [Apache Lucene #16242](https://github.com/apache/lucene/pull/16242). Nori users can opt into `HangulCompositionCharFilter` without adding the ICU analysis module, and NFC and modern NFD input can take the same morphological-analysis path.

It is tempting to classify this as the familiar macOS filename issue, but filenames are only one source. File uploads, OCR, crawlers, and external APIs can all change normalization form somewhere along an ingestion path. Visual inspection will not reveal it, and the analyzer can complete successfully while producing the wrong token graph.

For Korean corpora assembled from multiple systems, I now treat paired NFC/NFD analysis as a correctness test: feed the same sentence in both forms to the index and search analyzers, then compare terms, part-of-speech tags, positions, and offsets. Unicode representation is storage detail; it should not decide whether a document is retrievable.

Fixing the input representation still does not guarantee that every later query stage preserves the analyzer's meaning. The next case follows a correct Nori token graph into Elasticsearch, where a lost [position hole made a verbatim `match_phrase` return zero hits](/posts/2026-07-15-elasticsearch-nori-position-hole).
