---
title: "An FDS Dataset Solvable with 48 Transaction Amounts: Auditing 6.38M AI-Hub Rows"
date: 2026-07-15
description: "Audited 6.38M rows of AI-Hub's synthetic financial fraud data for amount shortcuts, split integrity, and duplicate risk, and assessed whether it can serve as a public FDS benchmark."
---

Before comparing FDS models, I checked whether the data can support the comparison. The target is the public train and validation portion of AI-Hub dataset 71925, "이상 판별을 위한 금융거래 정보 및 사용자 패턴 합성데이터" (synthetic financial transaction and user pattern data for anomaly detection): 6,386,977 rows. It consists of 4,434,106 rows from the 전자금융공동망 segment (Korea's shared interbank electronic banking network) and 1,952,871 card rows, about 90% of the labeled data AI-Hub reports.

The short version: the 전자금융공동망 data is hard to use as a benchmark for comparing behavior-based FDS models. The range at or below 1,000,000 won covers 98.97% of the data and contains zero positives, and the amount column across 4.43M rows contains only 48 distinct values. ROC-AUC computed from the amount alone was 0.9969.

This conclusion does not mean the amount is useless for real fraud detection. It means the labels in the public data can mostly be reconstructed from the amount templates of the synthesis process, not from transaction behavior.

## Audit scope

| Dataset | Rows | Positives | Positive rate |
|---|---:|---:|---:|
| 전자금융공동망 | 4,434,106 | 17,175 | 0.39% |
| Card | 1,952,871 | 72,008 | 3.69% |

Instead of reporting a single model score, the audit separated split integrity, single-feature shortcuts, ID memorization, duplicates, temporal shift, and label leakage into distinct checks. Rules and thresholds are fixed in code, and the same protocol also ran on other public FDS datasets.

## Amount template in the 전자금융공동망 data

The first check counted positives per amount bucket. In the snippets below, 거래금액 is the transaction amount and 이상거래여부 is the anomaly label.

```python
low = df[df["거래금액"] <= 1_000_000]

len(low) / len(df)          # 0.9897
low["이상거래여부"].sum()   # 0
```

Transactions at or below 1,000,000 won: 4,388,368 rows, 98.97% of the total. Zero positives in this range. Inspecting the structure of the amount column further, the same pattern repeated.

- The 4,434,106 rows use only 48 distinct amount values
- The top 10 amounts cover 98.05% of all rows
- 99.91% of amounts are multiples of 1,000 won
- ROC-AUC using the amount alone: 0.9969
- Distribution overlap between positive and negative amounts: 0.0065
- The single value `거래금액=4,000,000` captures 30.05% of all positives, 88.13x the base rate

This is closer to a codebook than a continuous behavioral feature. A model can score well by reconstructing the amount template, without learning account behavior or transaction sequences.

## Card data as supporting evidence

The card data also shows the shortcut. The rule `통합승인금액 >= 318,000` (통합승인금액 is the total approved amount), selected on train, scored F1 0.7204 on validation. Certain code values also carried high positive rates.

| Condition | Positive rate | Share of all positives captured |
|---|---:|---:|
| `일시불할부구분코드=B` | 97.77% | 33.18% |
| `승인거래코드=01` | 90.85% | 23.01% |

Here 일시불할부구분코드 is the lump-sum vs. installment code and 승인거래코드 is the approval transaction code.

The card verdict is weaker than the 전자금융공동망 one. Re-measured against a LightGBM reference model, the card data passed the amount-only PR-AUC and F1 relative-ratio gates. The final verdict rests on split integrity, an amount-only ROC-AUC of 0.9519, and one categorical value that captures 58.18% of positives. That value is separate from the two examples shown above.

Card is a supporting case showing the shortcut exists. 전자금융공동망 is the core case, meeting seven failure conditions on the amount template alone.

## Baseline sensitivity

The first audit used dependency-free Naive Bayes as the no-ID reference model. It was too weak to anchor a performance ratio against the amount-only model. Rerunning the sensitivity test with a fixed LightGBM baseline flipped the relative-ratio gate on both datasets from FAIL to PASS.

| Dataset | LightGBM no-ID PR-AUC | amount-only PR-AUC | Ratio | Relative-ratio gate |
|---|---:|---:|---:|---|
| Card | 0.9935 | 0.6640 | 0.6683 | PASS |
| 전자금융공동망 | 0.6161 | 0.4600 | 0.7466 | PASS |

So I removed the claim "an amount rule matches a strong model" from the final evidence. The 전자금융공동망 verdict stands on results that do not depend on a reference model: the 48 amount values, the 98.97% zero-positive range, the amount-only ROC-AUC, the distribution overlap, and the single-value shortcut.

A benchmark audit has to validate the comparison baseline along with the target. A weak baseline can inflate a model's apparent strength, and it can just as easily inflate a data defect.

## Split handling in the distributed validation code

I also reviewed the source of the official detection model distributed with the data. The card and 전자금융공동망 scripts load the provided train, validation, and test sets, concatenate them into one frame, and re-split with random stratified sampling after preprocessing.

```python
df = pd.concat([train_df, valid_df, test_df], ignore_index=True)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.1,
    random_state=42,
    stratify=y,
)
```

Categorical factorization also ran on the full data before the new split. Under this structure, temporal shift and generalization to unseen entities cannot be measured. The 전자금융공동망 data additionally contains duplicate feature rows after excluding the label, at 1.365% of the total. Random re-splitting creates paths for the same template or entity to land in both train and test.

## Cross-dataset protocol check

The same checks ran on ULB Credit Card Fraud, BAF Base, and my own synthetic dataset. If every dataset fails, the audit rules are too aggressive.

| Dataset | Verdict | amount-only ROC-AUC | Distinct amounts | Top-10 amount share |
|---|---|---:|---:|---:|
| K-Claims-Synth v0.2 | PASS | 0.5387 | 99,227 | 0.11% |
| ULB Credit Card Fraud | WARN | 0.7196 | 32,767 | 16.29% |
| BAF Base | WARN | 0.5939 | 994,971 | 0.00% |
| AI-Hub card | FAIL | 0.9519 | 1,931 | 86.01% |
| AI-Hub 전자금융공동망 | FAIL | 0.9969 | 48 | 98.05% |

The comparison datasets received WARN for single-feature subgroups but did not fail on amount templates, distribution overlap, duplicates, or temporal conditions. This provides evidence that the protocol does not blanket-fail FDS datasets.

## Gates before model development

Applied to a real ML workflow, the audit runs in this order.

1. Fix the split by time and entity first.
2. Fit preprocessing and aggregation on train, then apply to validation and test.
3. Keep amount thresholds, single categorical values, and ID-only models as formal baselines.
4. Check zero-positive ranges, distinct value counts, duplicates, and label conflicts before training.
5. Sensitivity-test the reference model and the audit thresholds themselves on other datasets.
6. Once the data passes the gates, select models by AUPRC, Precision@K, and recall at investigation capacity.

The AI-Hub data remains usable for practicing large-scale loading, schema handling, and imbalanced training. F1 or AUC obtained from the current public structure is not enough to rank behavior-based FDS models.

The audit code, fixed thresholds, LightGBM sensitivity results, and per-dataset JSON and Markdown reports are published at [fraud-dataset-validity](https://github.com/Incheonkirin/fraud-dataset-validity). File hashes and the reviewed lines of the official model source are recorded there as well.

Data: [AI-Hub 71925](https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=data&currMenu=115&dataSetSn=71925&topMenu=100)
