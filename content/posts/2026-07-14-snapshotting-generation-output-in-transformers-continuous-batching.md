---
title: "Snapshotting generation output in Transformers continuous batching"
date: 2026-07-14
description: "RequestState.to_generation_output() returned live buffers and mutated request state on the soft-reset path: delivered streaming chunks changed underneath callers, and soft-reset requests stopped short of max_new_tokens."
---

Continuous batching keeps the GPU busy by adding and removing requests from the in-flight batch every step. For streaming requests, the server hands back the tokens generated so far after each step. In Transformers that hand-off goes through `RequestState.to_generation_output()`, which packages the request's current tokens into a `GenerationOutput`.

A converter like that should be read-only. The one on `main` was not, in two ways.

First, it returned the request's own lists. `generated_tokens`, `logprobs`, and `timestamps` were passed into `GenerationOutput` by reference, not copied. The engine keeps appending to those lists as generation continues, so an output a caller already received would grow underneath it.

Second, it mutated the request in the soft-reset path. Under KV-cache pressure a request can be offloaded and resumed; resuming folds already-generated tokens back into the "initial" tokens for re-prefill, tracked by `_true_initial_tokens`. In that branch, `to_generation_output()` rewrote `self.generated_tokens` and `self.initial_tokens` while building the output.

The second one matters because streaming calls the converter once per token. Each call re-applied the prompt/generated split to already-split state, so a soft-reset request's bookkeeping drifted and it stopped before reaching `max_new_tokens`.

Reproduction (CPU, no accelerator): two regression tests build a `RequestState`, step it, and convert. One checks that a previously returned output keeps its length after more tokens arrive; the other checks that repeated conversion does not shorten a soft-reset generation. Both fail on `main` and pass with the fix.

End-to-end (single CUDA GPU, CUDA graphs on, cache sized to force soft reset, greedy, `max_new_tokens=30`): on `main`, several of twelve streaming requests stopped at 21-23 tokens, and some already-delivered first chunks later reported length 20/22/8. With the fix, all twelve reached 30 and every first chunk stayed length 1.

The fix makes the converter a snapshot, with one deliberate asymmetry. Prompt tokens never change after prefill, so they stay by reference. The growing buffers (`generated_tokens`, `logprobs`, `timestamps`) are copied, and the soft-reset split is computed into locals without writing back to the request. A full deep copy would have been simpler to reason about, but the converter runs once per generated token, and copying the prompt on every step adds cost proportional to prompt length for data that cannot change. Copying only what grows keeps the per-token overhead bounded by what was just generated.

Fix: [huggingface/transformers#46670](https://github.com/huggingface/transformers/pull/46670), merged 2026-06-16.
