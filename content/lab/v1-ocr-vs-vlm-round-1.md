---
draft: true
title: "Comparing OCR and Vision LLMs on 50 Mobile Screenshots"
date: 2026-05-09
type: tool
tags: [OCR, VLM, comparison, automation-tools]
status: round-1
aliases: ["lab/v1-ocr-vlm-비교-1차결과"]
sources:
  - "50 notes in vault/notes/ with a `screenshots` key"
  - "raw results: drafts/lab/comparison_20260509-0233.jsonl"
---

> **TL;DR**: I compared raw text extraction from OCR and Vision LLMs on 50 Korean Facebook mobile screenshots. PaddleOCR and Qwen2.5-VL 7B were close in both ROUGE-L and processing time. Going from 7B to 32B raised ROUGE-L by 0.023; 72B more than doubled processing time for a 0.005 ROUGE-L gain. Under these conditions, 32B had the best balance of ROUGE-L and processing time.

## Environment

- M4 Max 128GB, MLX 4bit (VLM)
- Input: 50 Facebook mobile screenshots stored in my Obsidian vault
- Metrics: time / memory / ROUGE-L (longest-common-subsequence overlap, GT = human-written note body)

## Averages

| Model | Avg time | ROUGE-L | Output chars |
|---|---:|---:|---:|
| tesseract | 1.31s | 0.170 | 1,234 |
| easyocr | 3.26s | 0.167 | 1,309 |
| paddleocr | 14.28s | 0.216 | 1,381 |
| qwen2.5-vl-7b | 14.57s | 0.216 | 1,762 |
| qwen2.5-vl-32b | 50.48s | 0.239 | 1,359 |
| qwen2.5-vl-72b | 107.05s | 0.244 | 1,337 |

## Findings

1. **VLM ROUGE-L ranged from 0.216 to 0.244, compared with about 0.17 for tesseract and easyocr.** This partially confirms my prior hypothesis that VLMs would make a large difference on composite content.
2. **Qwen2.5-VL 7B and PaddleOCR produced similar results.** Their ROUGE-L and processing times were nearly identical. PaddleOCR is simpler to operate.
3. **Marginal returns dropped sharply past 32B.** 72B took more than twice as long as 32B and gained 0.005 ROUGE-L.
4. **Input shape drove performance.** All models handled small, text-centric images well. Images where a capture of an external post was embedded inside a full 1179×2556 screen scored low across every model.

## Limitations

- **The ground truth is in a different format.** The ground truth is manually organized notes, not raw OCR text, so absolute ROUGE-L values diverge from actual extraction accuracy.
- **No post-processing step was included.** In the actual workflow, OCR output is cleaned up with an LLM. This comparison covers only the raw text extraction step.
- **VLMs also normalize output format.** Raw text extraction with OCR and reconstruction with a VLM are not exactly the same task.
