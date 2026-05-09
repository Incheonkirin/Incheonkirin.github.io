---
title: "OCR vs Vision LLM 1차 비교 — 페북 모바일 스샷 50장 raw 추출"
date: 2026-05-09
type: tool
tags: [OCR, VLM, 비교실험, 자동화도구]
status: 1차결과
sources:
  - vault/notes/ 중 screenshots: 키 보유 노트 50개
  - 결과 raw: drafts/lab/comparison_20260509-0233.jsonl
---

> **TL;DR**: 페북 한국어 모바일 스샷에서 raw OCR 4종(Tesseract/EasyOCR/PaddleOCR) + Vision LLM 3종(Qwen2.5-VL 7B/32B/72B) 비교. **PaddleOCR ≈ Qwen-VL 7B** (정확도/시간 동일), Qwen-VL 72B는 32B 대비 비용 대비 효과 거의 없음. **32B가 sweet spot.**

## 환경

- M4 Max 128GB, MLX 4bit (VLM)
- 입력: 옵시디언 vault에 보관된 페북 모바일 스샷 50장
- 메트릭: 시간/메모리/ROUGE-L (의미 보존, GT = 사람 작성 노트 본문)

## 평균 비교

| 모델 | 평균 시간 | ROUGE-L | 출력 chars |
|---|---:|---:|---:|
| tesseract | 1.31s | 0.170 | 1,234 |
| easyocr | 3.26s | 0.167 | 1,309 |
| paddleocr | 14.28s | 0.216 | 1,381 |
| qwen2.5-vl-7b | 14.57s | 0.216 | 1,762 |
| qwen2.5-vl-32b | 50.48s | 0.239 | 1,359 |
| qwen2.5-vl-72b | 107.05s | 0.244 | 1,337 |

## 핵심 발견

1. **VLM 압도적 X** — 사전 가설("VLM이 짬뽕 컨텐츠에 압도적")은 부분만 맞음. 정확도 차이 0.17→0.24, 약 40%.
2. **Qwen-VL 7B ≈ PaddleOCR** — 정확도 동일, 시간 동일. PaddleOCR이 운영 단순성 우위.
3. **Qwen-VL 32B → 72B**: 시간 2배, 정확도 +0.005. 32B가 sweet spot.
4. **best/worst 패턴** — best는 모두 단순 텍스트 위주 작은 이미지. worst는 모두 1179×2556 모바일 풀스크린 + "이미지 안에 또 이미지" (페북에서 외부 글 캡처해 첨부한 패턴).

## 한계

- **GT 형식 mismatch**: GT가 raw OCR 텍스트가 아니라 본인이 정리한 노트라 ROUGE-L 절대값 낮음.
- **Pipeline A 후처리 빠짐**: OCR 결과를 LLM(Qwen3.5)으로 정리하는 단계가 빠짐. 그게 본인 워크플로우의 진짜 단위.
- **GT 도구 자체 보정**: VLM은 추출 시 자동 reformat 가능. raw OCR과 task가 동일하지 않음.

## 다음

→ **[v2 비교 실험](./v2-end-to-end-pipeline.md)**: PROCESSING_GUIDE 7단계 end-to-end 파이프라인 (사진첩 원본 + URL fetch + Qwen3.5 정리 + 위키링크) 비교.

## 도구 코드

- 비교 batch: `pipeline_v1/scripts/batch_compare.py`
- 추출 wrapper: `pipeline_v1/{ocr,vlm}/`
- 메트릭: `pipeline_v1/metrics.py`

GitHub: incheonkirin/incheonkirin.github.io 안 코드 직접 fork 가능.
