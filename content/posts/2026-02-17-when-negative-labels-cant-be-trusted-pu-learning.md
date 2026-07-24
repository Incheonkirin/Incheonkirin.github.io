---
title: "Managing Unreviewed Data as a Third Label"
date: 2026-02-17
description: Designing the label generation process and selection bias of a fraud detection system as observable data structures.
tags: [Label-Quality, Selection-Bias, PU-Learning]
source: velog
original_url: https://velog.io/@incheonkirin/%EC%9D%8C%EC%84%B1-%EB%A0%88%EC%9D%B4%EB%B8%94%EC%9D%84-%EB%AF%BF%EC%9D%84-%EC%88%98-%EC%97%86%EC%9D%84-%EB%95%8C-PU-Learning
aliases: ["posts/2026-02-17-음성-레이블을-믿을-수-없을-때--PU-Learning"]
---

When I first looked into PU Learning, I started with the uPU and nnPU losses. After redrawing the data flow, I found I had to define the label generation process before choosing an algorithm.

The model flags 1,000 cases as suspicious. The review team checks 100 of them. If the 900 cases still waiting for review get a normal label, what does the next model learn?

The next model learns the past review policy along with the actual anomaly patterns. Case types the previous model selected often keep accumulating in the training data, and the other types harden into normal. Breaking this feedback loop starts with recording how each label was produced.

## Separating confirmed negatives from unreviewed cases

I split the labels in operational data into three states.

| State | Meaning | Treatment in training |
|---|---|---|
| Confirmed Positive | Confirmed anomalous after review | Positive |
| Confirmed Negative | Confirmed normal after review | Negative |
| Unreviewed | Awaiting review results | Unlabeled |

The key is separating confirmed-normal from awaiting-review. Confirmed normal is a result a person verified. Awaiting review means the outcome has not yet been observed.

```text
All cases
  └─ Risk scores computed by model and rules
       └─ Top K cases selected for review
            ├─ Confirmed anomalous
            └─ Confirmed normal

N-K cases outside the selection
  └─ Remain Unreviewed
```

In the training table, `normal=1` applies only to Confirmed Negative. Unreviewed stays as is. This distinction is what allows supervised learning, propensity weighting, and PU learning to be validated separately.

## The review policy behind the label distribution

Traditional PU Learning often uses the SCAR (Selected Completely At Random) assumption, under which confirmed positives are a random sample of all positives.

$$P(s=1 \mid x, y=1) = c$$

The review process in a fraud detection system (FDS) prioritizes cases by scores and rules. Cases with high scores, or cases matching specific rules, get selected first. So I model the per-case selection probability as $e(x)$.

$$P(s=1 \mid x, y=1) = e(x)$$

The model learns anomaly patterns together with the existing review policy. Case types the past policy selected often accumulate abundant labels. Types with few review opportunities accumulate Unreviewed.

In this structure, the per-case selection reason and the policy version matter. Storing both makes the selection mechanism observable and provides the basis for probability correction.

## Recording review context in the training data

I added the following fields next to the label.

```text
case_id
score_at_selection
review_selected
selection_policy_version
selection_reason
review_result
reviewed_at
outcome_confirmed_at
```

`selection_policy_version` is the column that explains changes in the label distribution. Model replacements, rule changes, and shifts in the review team's priorities all connect to this value. When Precision changes next month, the effect of the model and the effect of the review criteria can be examined separately.

## Validation in four steps

### 1. Reserve a random review slice

Allocate part of the total review capacity to a random or stratified sample. This sample becomes the reference point for estimating positive rates per score band and selection propensity.

### 2. Link delayed outcomes

Some cases get their outcomes confirmed after the review date, through complaints, clawbacks, or external verification. Separate the prediction time from the outcome confirmation time, and backfill labels after the observation window passes.

### 3. Compare baselines under identical conditions

Compare three models over the same time window and review capacity.

1. Build a supervised baseline on review-completed data.
2. Build a baseline that applies binary labels to all data.
3. Apply propensity weighting or a PU approach.

The common metrics are Precision@K, Recall@K on delayed confirmed positives, and review yield per score band. The PU model's role is to push positives the past policy under-selected up the ranking.

### 4. Track the model and the review policy together

Track the review-target distribution per rule and score band, late-arriving positives from the Unreviewed segment, and the yield of the random review slice on the same dashboard.

## PU Learning as the second stage

PU Learning is a framework for estimating the positives hidden in the unlabeled set. In an FDS, I observe the label states and the selection policy first. Propensity and PU approaches go on top of that.

The operating principle fits in two sentences.

> Unreviewed cases get the Unreviewed state. The review policy is recorded alongside the label.

The label generation process constrains model performance.
