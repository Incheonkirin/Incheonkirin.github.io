---
title: "The fraud dataset whose labels were visible in 48 transaction amounts"
seoTitle: "AI-Hub FDS dataset audit: 6.38M rows and a 48-value amount shortcut"
date: 2026-07-15
description: "I audited 6.38M AI-Hub FDS rows before model comparison and found that a 48-value transaction-amount template nearly reconstructed the fraud labels."
tags: [FDS, Dataset-Audit, Fraud-Detection, Model-Evaluation]
lang: en
translations:
  en: posts/2026-07-15-aihub-fds-dataset-validity
  ko: ko/posts/aihub-fds-dataset-validity
---

Before training an FDS model, I counted the values in one column.

The electronic financial network portion of AI-Hub dataset 71925 contained 4,434,106 audited transactions, but only **48 distinct transaction amounts**. The range at or below KRW 1,000,000 covered 4,388,368 rows—98.97% of the data—and contained **zero positive labels**.

```python
low = df[df["거래금액"] <= 1_000_000]

len(low) / len(df)          # 0.9897
low["이상거래여부"].sum()   # 0
df["거래금액"].nunique()    # 48
```

An amount-only score reached ROC-AUC `0.9969` on the supplied train/validation split. A behavior model could look excellent on this data without learning account history, transaction sequences, or changing customer behavior. It only had to recover the amount template.

That changed the question I was trying to answer. Instead of asking which model won, I first had to ask whether this dataset could distinguish a better fraud model from a better shortcut detector.

## I counted the data before comparing models

The audit covered the released train and validation files I could configure from AI-Hub's synthetic financial transaction dataset: 6,386,977 rows, about 90% of the labeled rows reported on the dataset page.

| Segment | Audited rows | Positive labels | Positive rate |
| --- | ---: | ---: | ---: |
| Electronic financial network | 4,434,106 | 17,175 | 0.39% |
| Card transactions | 1,952,871 | 72,008 | 3.69% |

I started with checks that do not require a sophisticated model: value counts, positive rates by value and range, class-distribution overlap, duplicates, and the integrity of the supplied split. These reveal whether a benchmark has made its answer available through a low-dimensional rule before model architecture enters the discussion.

The amount column in the electronic financial network segment kept failing those checks:

- the top 10 of its 48 amounts cover 98.05% of all rows
- 99.91% of rows use amounts divisible by KRW 1,000
- positive and negative amount distributions have only `0.0065` overlap
- `거래금액=4,000,000` alone captures 30.05% of all positives at 88.13 times the base positive rate

Individually, round amounts or a strong amount signal can be plausible in financial data. Together with a 98.97% region containing no positives, they form something closer to a label codebook than a continuous behavioral feature.

## A high score was evidence of learnability, not benchmark validity

It would be wrong to conclude that transaction amount is irrelevant to real fraud detection. Amount is often useful. The narrower finding is that, in this released synthetic segment, the label can be reconstructed largely from a small set of amount templates.

That distinction matters because a benchmark score normally stands in for a harder claim: a model that performs better has learned a more useful fraud decision rule. Here, a higher score can instead mean that the model recovered the generator's stable template more efficiently.

The card segment provided supporting evidence, although it was not as decisive as the electronic financial network case. Its amount-only ROC-AUC was `0.9519`, and the ten most common approved amounts covered 86.01% of rows. A threshold selected on train, `통합승인금액 >= 318,000`, reached validation F1 `0.7204`. Individual category values were also unusually revealing:

| Single condition | Positive rate | Share of positives captured |
| --- | ---: | ---: |
| `일시불할부구분코드=B` | 97.77% | 33.18% |
| `승인거래코드=1` | 90.85% | 23.01% |
| `가맹점누적매출금액_구간화=3` | 22.92% | 58.18% |

The last condition captures more than half of all positive card rows at 6.22 times the base rate. This does not make the card evidence identical to the 48-value amount template, but it reinforces the need for trivial single-feature baselines before interpreting a complex model's score.

## A stronger baseline invalidated one of my claims

My first audit harness used a dependency-free Naive Bayes model as its no-ID reference. An amount-only model looked too competitive against it. That supported a convenient claim: a simple amount rule could match a fuller model.

The reference was too weak.

I reran the sensitivity analysis with a fixed LightGBM baseline. The relative amount-to-model gates changed from failure to pass on both AI-Hub segments:

| Segment | LightGBM no-ID PR-AUC | Amount-only PR-AUC | Ratio | Relative gate |
| --- | ---: | ---: | ---: | --- |
| Card | 0.9935 | 0.6640 | 0.6683 | PASS |
| Electronic financial network | 0.6161 | 0.4600 | 0.7466 | PASS |

I removed the claim that an amount rule matched a strong model. Keeping it after the stronger baseline contradicted it would have turned an audit into advocacy for a predetermined verdict.

The main electronic-network conclusion did not need that comparison. It still rested on model-independent facts: 48 distinct amounts, the 98.97% zero-positive range, amount-only ROC-AUC `0.9969`, distribution overlap `0.0065`, and the single-value shortcut. Auditing the baseline changed the evidence I was willing to use, without changing the findings that survived it.

## The distributed evaluation code erased the supplied split

I also inspected the anomaly-detection source package distributed with the dataset. Both the card and electronic-network scripts load the supplied train, validation, and test files, concatenate them, preprocess the combined frame, and then create a new random stratified split.

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

Categorical factorization also runs on the combined data before the new split. Under that evaluation path, the original split boundary no longer measures temporal change or generalization to unseen entities. Repeated templates and entities can appear on both sides of the random split.

The electronic-network data also contains 60,538 duplicate feature rows after excluding the label, or 1.365% of the segment. A random re-split makes that duplication more consequential because identical feature templates can land in both training and evaluation data.

A published model scoring well under this procedure proves the released rows are learnable. It does not establish that the score represents deployable behavior-level fraud detection.

## I tested whether the audit itself was too eager to fail data

A protocol that rejects every fraud dataset would not be useful. I therefore ran the same fixed checks on two established public datasets and one synthetic control, rather than choosing thresholds only after seeing the AI-Hub results.

| Dataset | Verdict | Amount-only ROC-AUC | Distinct amounts | Top-10 amount share |
| --- | --- | ---: | ---: | ---: |
| K-Claims-Synth v0.2 | PASS | 0.5387 | 99,227 | 0.11% |
| ULB Credit Card Fraud | WARN | 0.7196 | 32,767 | 16.29% |
| BAF Base | WARN | 0.5939 | 994,971 | 0.00% |
| AI-Hub card | FAIL | 0.9519 | 1,931 | 86.01% |
| AI-Hub electronic network | FAIL | 0.9969 | 48 | 98.05% |

ULB and BAF produced warnings for broad single-feature subgroups, but they did not fail on the concentrated amount-template pattern. The result is graded rather than universal: the protocol can pass, warn, or fail, and the strongest AI-Hub finding remains an outlier under the same rules.

## The useful outcome was a decision about the data

The audited electronic financial network release is not suitable for ranking behavior-based FDS models in its current form. Its labels are overwhelmingly recoverable from a 48-value amount template, and the distributed evaluation path removes the supplied split boundary.

That is not the same as saying the files have no value. They can still support large-scale ingestion tests, schema demonstrations, class-imbalance exercises, and examples of why trivial baselines matter. What they cannot support, without redesigning or removing the shortcut structure, is a claim that a higher F1 or AUC identifies a better model of fraud behavior.

There are also limits to the audit. It covers the released train and validation rows I had available, not every labeled row stated on the AI-Hub page. The generator implementation is not public, so the evidence identifies structure in the released data rather than assigning intent or a specific bug inside the generator. The LightGBM run is a frozen sensitivity check, not a tuned model competition.

The value of doing this before model development is practical: it prevents weeks of optimization from producing a precise answer to the wrong question. The code, thresholds, source-file hashes, sensitivity runs, and per-dataset reports are published in [fraud-dataset-validity](https://github.com/Incheonkirin/fraud-dataset-validity). The source data is [AI-Hub dataset 71925](https://www.aihub.or.kr/aihubdata/data/view.do?aihubDataSe=data&currMenu=115&dataSetSn=71925&topMenu=100).
