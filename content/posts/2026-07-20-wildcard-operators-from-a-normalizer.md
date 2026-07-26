---
title: "When a normalizer turns fullwidth characters into wildcard operators"
date: 2026-07-20
description: "A keyword field with a normalizer that folds fullwidth forms to ASCII made wildcard queries either over-match or return zero hits, because Elasticsearch normalized the pattern but did not re-escape operators the normalizer produced. Fixed in Elasticsearch #153582."
---

A `wildcard` query for the literal string `foo＊bar` (with a fullwidth asterisk, U+FF0A) on a `keyword` field returned documents it should not have. Escaping the character, `foo\＊bar`, returned zero hits instead of the one exact match. The field used a normalizer that folds fullwidth forms to ASCII, and the operators `*` `?` `\` were the trigger.

## Reproduction matrix

The merged regression indexes four values through a normalizer that maps fullwidth wildcard forms to ASCII:

```text
document 1: foo＊bar  → indexed term foo*bar
document 2: foo？bar  → indexed term foo?bar
document 3: foo＼bar  → indexed term foo\bar
document 4: foobar   → indexed term foobar
```

These assertions pin the distinction between literal fullwidth data and real ASCII operators:

| Query pattern | Meaning after the fix | Hits |
|---|---|---:|
| `foo＊bar` | literal `*` | 1 |
| `foo\＊bar` | the same literal `*` | 1 |
| `foo？bar` | literal `?` | 1 |
| `foo＼bar` | literal `\` | 1 |
| `foo*bar` | zero-or-more wildcard | 4 |
| `foo?bar` | one-character wildcard | 3 |
| `foo\\bar` | literal ASCII backslash | 1 |

Before the fix, a bare fullwidth literal could become an operator after normalization, while an escaped fullwidth literal skipped the normalization needed to match the indexed term. The two spellings therefore produced over-matching and zero hits respectively.

## Mechanism

On a `keyword` field, a `wildcard` query runs its pattern through the field's normalizer so the pattern matches normalized index terms. The catch is that `*`, `?`, and `\` are wildcard control characters, so `normalizeWildcardPattern` normalizes only the literal parts and keeps the operators as operators. When the normalizer itself emits one of those three characters, that separation breaks. Two distinct defects:

- **Escaped content was appended verbatim.** `\＊` is a literal fullwidth asterisk, but its contents skipped normalization, so the query searched for U+FF0A, which the normalizer had folded to `*` at index time. The character is not in the index. Zero hits.
- **Normalized literals were not re-escaped.** A bare `＊` is literal data; the normalizer folds it to `*`, and that `*` went into the compiled query as an operator. The literal became a wildcard and over-matched.

Neither failure raises an error; you get the wrong hit count, and only on fields whose normalizer rewrites one of the three control characters. ICU NFKC is the common case; it maps fullwidth ASCII variants (`＊？＼` and the rest of the fullwidth block) to their ASCII forms. Korean and Japanese text carry these fullwidth punctuation forms routinely.

<!-- figure: pattern → normalize-per-run → re-escape → query tree -->

## Fix

The pattern is walked as alternating literal and operator runs. Each contiguous literal run (spanning plain text and the contents of escapes) is normalized as one unit, so a context-sensitive normalizer such as ICU NFC sees the whole run rather than one character at a time. Any `*` `?` `\` the normalizer produces in that output is then re-escaped, so normalized data can never become an operator. Operator runs are copied through verbatim, and `WILDCARD_PATTERN` now compiles with `DOTALL` so an escape sequence just before a line terminator is still read as an escape.

One deliberate behavior change: a trailing lone backslash (`abc\`) now normalizes to an escaped backslash `\\` rather than passing through raw. Both forms are equivalent in Lucene.

## Tests

The regression test indexes documents whose source contains the fullwidth `＊`, `？`, and `＼` through a normalizer that folds them to ASCII, then asserts hit counts for the bare fullwidth literal, the escaped fullwidth literal, and the real ASCII operator, so the three cases can no longer collapse into each other. Merged as [elastic/elasticsearch #153582](https://github.com/elastic/elasticsearch/pull/153582) and backported to the 9.3, 9.4, 9.5, and 8.19 lines.

## Takeaway

This is the same shape as the other Korean-search failures in this series: a transformation that is correct in isolation (the normalizer folds fullwidth to ASCII, exactly as configured) emits a character that a later stage reads as a control operator rather than data. The fix keeps normalizing and re-escapes at the boundary, so data stays data. If you run `wildcard` queries against `keyword` fields with a non-trivial normalizer, check what that normalizer does to `*`, `?`, and `\`.

For the related Unicode, morphology, and token-graph failures, start with the [Korean search correctness guide](../ko/korean-search-correctness).
