---
draft: true
title: "Designing Autonomy for an Insurance Question-Answering Agent"
date: 2026-06-17
description: Connecting a conversation at Anthropic Build Day to an experiment comparing an agent against a workflow.
tags: [Agent, Evaluation, Workflow, Insurance-Question-Answering]
aliases: ["posts/2026-06-17-Claude-Agentic-Search와-보험-QA"]
---

After Anthropic Build Day ended, I asked one of the engineers a question.

> I am building an insurance question-answering system. Should a human design the business procedure, or should the agent own it?

He thought for a moment and replied.

> Build both and compare them.

A short answer, but the direction was clear. An agent's autonomy can be calibrated on the same questions and the same evaluation criteria.

## Workflow design after retrieval

The water-leak question I described had several tasks mixed into a single sentence.

- The policyholder noticed a leak, then bought the insurance.
- They plan to pay for the current leak out of pocket.
- They ask about coverage for a leak that occurs in the same spot 90 days later.
- They ask which coverages apply to repairing their own home and to damage in the unit below.
- They also want products with different deductible terms.

The search query can be as short as '누수 보험' (water-leak insurance). The answering process is much longer. First, construct the temporal relations among noticing the loss, buying the policy, the waiting period, and the recurrence date. Then find evidence to distinguish a continuation of the earlier loss from a new loss, and map the insured's own property damage and third-party liability to their respective coverages.

Finally, separate policy interpretation from product comparison. When contract details are still missing, the system also has to produce specific follow-up questions.

RAG collects relevant documents. An insurance question-answering system also has to decide the order in which that evidence gets connected. This is where the problem expands from retrieval accuracy to workflow design.

## Two approaches

When a human predefines the insurance workflow, reproducibility and auditability improve. As question types multiply, the cost of managing the branches grows with them.

When Claude builds a plan per question, it adapts to new questions and selects the tools it needs. Search paths and call counts vary from run to run.

The Anthropic engineer's advice meant finding the boundary between the two structures by experiment. First, observe how the agent handles real questions. Freeze recurring procedures into skills and deterministic steps. Keep the areas it performs reliably as the agent's role.

## Three architectures under the same conditions

The experiment compares three architectures.

| Approach | Planning | Evidence collection | Verification |
|---|---|---|---|
| Deterministic | Fixed workflow defined by a human | Tool calls in a fixed order | Rule-based checks |
| Agentic | Claude generates a plan per question | Claude selects and iterates on tools | Claude evaluates the results |
| Hybrid | Claude decomposes the question | The system runs the evidence protocol | Rules and Claude verify together |

My hypothesis is that Hybrid will balance accuracy and reproducibility best. Claude structures the user's question, and the system controls evidence collection and verification.

```text
User question
  → Claude: decompose into claims and subtasks
  → System: run the evidence protocol for each task type
  → Claude: check evidence sufficiency and propose the next task
  → System: verify citations, temporal relations, and answer scope
  → Claude: write the final answer
```

All three architectures receive the same questions, documents, and tools. Each architecture bundles its own planning, evidence collection, and verification, so the comparison evaluates whole architectures rather than isolating a single variable.

## Evaluating the answer and the process

Reading only the final sentences favors fluent answers. In insurance question answering, the path to the answer is part of its quality. I use five criteria.

### Required-issue recall

For each question, I build a gold checklist of the facts and judgments the answer must cover. For the leak case, this includes pre-purchase awareness, whether it is the same loss, the coverage split, exclusions, and the deductible. I measure how many of these items each architecture recovers.

### Evidence support rate

I check whether each cited span directly supports the claim immediately before it. The as-of dates of the product and the policy are verified as well.

### Follow-up request accuracy

Questions with sufficient contract details and loss facts get an answer. Questions that need more information get a specific follow-up question. I measure how accurately each architecture distinguishes the two cases.

### Run reproducibility

Each question runs multiple times. I record the variance in tool selection, search counts, and final conclusions. Average performance and per-run deviation are evaluated together.

### Operating cost

I record tool call counts, token cost, and latency. I analyze the relationship between accuracy and cost, and build workflow routing criteria based on question complexity.

## The autonomy boundary

The system is responsible for checking policy versions and as-of dates, linking claims to their cited evidence, verifying personal data and permissions, and keeping audit logs.

The agent owns decomposing the user's question into subtasks, expanding search queries, and proposing the next task.

The core takeaway from Build Day was a method for finding the autonomy boundary: compare the human workflow and the agent's plan on the same evaluation set, and adjust the boundary based on the results.

The decision rule is the one the experiment defines: run the three architectures on the same evaluation set, score them on the five criteria, freeze recurring procedures into deterministic steps, and keep the areas the agent handles reliably as the agent's role.
