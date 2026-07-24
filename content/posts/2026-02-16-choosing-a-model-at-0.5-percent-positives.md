---
title: "Choosing a Model at 0.5% Positives"
date: 2026-02-16
description: Connecting model metrics to investigation capacity and actual decisions on extremely imbalanced data.
tags: [Model-Evaluation, Precision-at-K, Decision-Policy]
source: velog
original_url: https://velog.io/@incheonkirin/0.5-%EC%96%91%EC%84%B1-%EB%8D%B0%EC%9D%B4%ED%84%B0%EC%97%90%EC%84%9C-%EB%AA%A8%EB%8D%B8%EC%9D%84-%EC%84%A0%ED%83%9D%ED%95%98%EB%8A%94-%EB%B2%95
aliases: ["posts/2026-02-16-0.5%-양성-데이터에서-모델을-선택하는-법"]
---

While reviewing an FDS (fraud detection system) model, I was asked this question.

> How did you use AUROC for model selection?

At first I answered in terms of F1. With only 0.5% positives, looking at precision and recall together seemed right. Once I connected the model to operations, another question came up.

> How many cases can the investigation team handle per day?

Putting investigation capacity into the criteria changes what model selection is. It turns from a contest of classification performance into a problem of allocating limited review capacity.

## What AUROC explains

Assume 500 actual anomalies out of 100,000 cases. The model's recall is 80% and its FPR is 1%.

- It finds 400 of the 500 actual anomalies.
- 995 of the 99,500 normal cases are flagged for investigation.
- The total investigation queue is 1,395 cases, and precision is about 28.7%.

AUROC shows how well the model ranks positives against negatives across the whole dataset.

The operations team asks a different question. If they investigate 100 cases a day, how many will the top 100 catch? That calls for Precision@100 and Recall@100.

AUROC describes the full ranking; top-K metrics describe the actual investigation window. The two answer different questions.

## The limits of F1

F1 summarizes the balance of precision and recall in a single value.

$$F_1 = \frac{2 \cdot Precision \cdot Recall}{Precision + Recall}$$

F1 is useful for quickly comparing threshold candidates on imbalanced data. Using it as an operating criterion requires throughput and cost as well.

First, throughput. The point where F1 peaks may flag 2,000 cases. If the team's daily throughput is 100 cases, the actual operating window is the top 100.

Second, cost. An unnecessary investigation and a missed anomaly cost different amounts. The criteria have to reflect both the investigation volume the organization can sustain and the risk level it can accept.

So I split the metrics into three layers.

| What to check | Metrics |
|---|---|
| Ranking quality over the full dataset | AUROC, AUPRC |
| Detection in the actual investigation window | Precision@K, Recall@K, Lift@K |
| Sustainability of the operating policy | investigation volume, FP/FN cost, monthly detection yield |

As the positive rate drops, AUPRC and top-K metrics matter more. An FPR change that looks small in ROC space converts to hundreds of extra investigations in absolute counts.

## Choosing K and the threshold

Before searching for a threshold, I fixed K. Daily, weekly, and monthly investigation capacity comes from headcount, time per case, and the separate handling rule for high-risk cases.

Once K is set to 100, models can be compared under the same condition. Model A's threshold may be 0.82 and model B's 0.61, but both surface the top 100 cases. Now Precision@100 and Recall@100 can sit side by side.

In the early phase, while cost data accumulates, I use constraints.

- Keep precision at 30% or higher.
- Keep recall on high-risk types at 70% or higher.
- Run investigations at 100 cases per day.

Stating the constraints makes the model-selection rationale concrete.

> Among candidates that satisfy the operating constraints, select the model with the highest Recall@100.

## Rechecking in time order

FDS data exhibits seasonality, policy changes, and new anomaly types. Backtests over multiple periods check the following.

- Monthly variation in Precision@K and Recall@K
- Stability of the threshold and detection counts
- Detection distribution by organization, product, and channel
- Performance before and after policy changes

Set the threshold on the validation period, then apply it to a future test period. After deployment, track the actual investigation yield and late-confirmed anomalies. Only with this loop does a model score connect to operating outcomes.

F1 is still useful, but its role changed. F1 summarizes threshold candidates; investigation capacity and cost policy make the final choice.

The model outputs a risk score, and the policy translates that score into investigation counts and cost. A good FDS model supports consistent decisions within a limited investigation capacity.

## References

- [The Relationship Between Precision-Recall and ROC Curves](https://doi.org/10.1145/1143844.1143874)
- [The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets](https://doi.org/10.1371/journal.pone.0118432)
