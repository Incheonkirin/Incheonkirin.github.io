---
title: 정민기
date: 2026-05-10
---

보험 도메인 데이터 사이언티스트. 7년차. 한국.

지금은 한국 외국계 생명보험사에서 일한 지 2년쯤 됐다. 인수심사 자동화 모형(XGBoost), 청구 사기 탐지(NN, FDS), 설계사 가동 예측(LightGBM), 그리고 통계 기반 추가가입 모형, 이렇게 네 개를 운영하고 있다. 인수심사 모형은 GA 25회차 유지율을 62.2%에서 69.8%로 올렸고(+7.6%p, AUC/F1 +20%), 사기 탐지 모형은 부지급 사례를 70% 넘게 사전탐지해서 작년 기준 약 22억을 방어했다. 가명처리 솔루션은 기획부터 도입까지 직접 끌었다 — 15개 기법, 자동 보고서, 적정성 평가 프로세스 포함. 같이 AI 거버넌스(RUAI)도 운영하면서 AI 기본법·금융분야 AI 가이드라인을 D&T에 발표하고 금감원 CPC를 대응한다. 임직원 Agentic AI Hands-on, AI WG, 내부 AI Lab도 같이.

그전에는 한국 NLP 스타트업에서 5년 반쯤 검색개발팀 매니저로 일했다. BM25 + Contrastive Learning 기반 IR, MRC, RAG 파이프라인까지 직접 만들었다. 가장 보람 있었던 건 약관 RAG QA — 할루시네이션을 90% 줄이고 정확도를 30% 올렸다. 금융권 레퍼런스가 좀 쌓였다 (손해보험사, 증권사, 보증사 등). SFT/DPO/LoRA 파인튜닝도 거기서 다 만져봤다.

지금 이 사이트에서 만들고 있는 건 세 가지다.

하나, 모바일 페북 스크린샷을 옵시디언 노트로 자동 변환하는 파이프라인. 사진첩에서 EXIF 시간으로 그룹핑하고, OCR/Vision LLM으로 텍스트 뽑고, URL이 있으면 trafilatura로 본문 가져오고, Qwen3.5-122B가 PROCESSING_GUIDE 형식으로 정리해서 노트로 저장한다. 본 사이트가 그 결과물 일부.

둘, 신모델이 출시되면 자동 감지해서 본인 도메인 5축 100문제로 평가하는 하니스. 공개 벤치(MMLU, GPQA)는 일반적이라 본인 use case는 못 알려주니까 직접 만든다.

셋, KIRI · 금감원 · 금융위 같은 곳에서 발표하는 보고서에 응답하는 글 시리즈. 매주 새 발표가 무엇이 빠졌는지 — 효과 측정 방법론, 데이터 거버넌스, 다음 단계 — 세 축으로 짚는다.

도구는 Python · SQL 기본 위에 XGBoost · LightGBM · PyTorch · HuggingFace · BERT/ELECTRA, LLM은 OpenAI · Claude · Qwen, 인프라는 LangChain · LlamaIndex · Milvus · Elasticsearch · Azure ML · Databricks, 로컬은 MLX 위주. 자격은 ADsP, 영어는 OPIc IH라 글로벌 본사와 협의 가능.

연락 — incheonkirin@gmail.com
