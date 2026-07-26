---
title: Mingi Jeong
seoTitle: "Mingi Jeong — Lucene, Elasticsearch & Applied ML Engineer"
description: "Failures in Korean search, ranking, and ML systems traced to reproducible tests, then to an upstream fix or a measured decision."
---

<section class="intro">
  <h1 class="lede">I trace failures in Korean search, ranking, and ML systems to reproducible tests — then to an upstream fix or a measured decision.</h1>
  <p class="creds">5.5 years in Korean search and question answering at 42Maru · production ML at MetLife · 18 patches merged into Lucene, Elasticsearch, sentence-transformers, and Transformers.</p>
</section>

<section class="section">
  <div class="section-head">
    <h2 class="section-title">Search correctness</h2>
    <p class="section-frame">Where a transformation that is correct on its own — a normalizer, a decompounder, a dictionary — still makes the search return the wrong thing.</p>
  </div>

  <article class="lead-entry">
    <h3 class="lead-title"><a class="internal" href="posts/2026-06-30-nfd-hangul-and-noris-dictionary">Identical Korean text produced different search results</a></h3>
    <p class="lead-body">A Korean word stored as decomposed Unicode looked normal on screen but bypassed Nori's dictionary and became one unknown token. I traced the silent mismatch to the analyzer boundary, then added a Hangul composition filter that restores the dictionary lookup without adding ICU and preserves offsets for highlighting.</p>
    <p class="lead-result">Merged into Apache Lucene <span class="dim">· reviewed and approved by a core maintainer (Robert Muir) · #16242</span></p>
  </article>

  <div class="entries">
    <article class="entry">
      <h3 class="entry-title"><a class="internal" href="posts/2026-07-15-elasticsearch-nori-position-hole">The exact sentence from a document returned zero hits</a></h3>
      <p class="entry-body">A verbatim <code>match_phrase</code> found nothing because two query paths were dropping a positional gap the Korean analyzer had created.</p>
      <p class="meta">Elasticsearch · Nori · 2026.07 · merged (#152931)</p>
    </article>
    <article class="entry">
      <h3 class="entry-title"><a class="internal" href="posts/2026-06-16-noris-default-stoptags-drop-korean-negation-prefixes">Searching 비급여 (non-covered) returned 급여 (covered)</a></h3>
      <p class="entry-body">The default Korean analyzer removes negation prefixes, merging opposite words at index time.</p>
      <p class="meta">Elasticsearch · Nori · 2026.06 · merged (#151157)</p>
    </article>
    <article class="entry">
      <h3 class="entry-title"><a class="internal" href="posts/2026-07-20-wildcard-operators-from-a-normalizer">A normalizer turned fullwidth characters into wildcard operators</a></h3>
      <p class="entry-body">A <code>keyword</code> normalizer folded fullwidth forms to ASCII <em>after</em> wildcard escaping, so characters that were meant as literals became query operators.</p>
      <p class="meta">Elasticsearch · Wildcard · 2026.07 · merged (#153582)</p>
    </article>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <h2 class="section-title">Ranking &amp; retrieval</h2>
    <p class="section-frame">Learning-to-rank losses and retrieval quality — from a gradient that was quietly wrong to a number a maintainer could measure.</p>
  </div>

  <article class="lead-entry">
    <h3 class="lead-title"><a class="internal" href="posts/2026-06-20-padding-in-the-plackett-luce-normalizer-listmle">A ranking model trained differently depending on the batch</a></h3>
    <p class="lead-body">To train a ranking model quickly, many search queries are scored together in one batch — but each query has a different number of documents, so the shorter lists are filled with empty placeholder slots to make them the same length. Those empty slots were being counted as if they were real documents, so the same query trained differently depending on which other queries happened to share its batch. I excluded the padding from the calculation so the result no longer depends on batch composition.</p>
    <p class="lead-result">Merged into sentence-transformers <span class="dim">· controlled maintainer benchmark: PListMLE nDCG@10 0.514 → 0.525 · #3827</span></p>
  </article>

  <div class="entries">
    <article class="entry">
      <h3 class="entry-title"><a class="internal" href="posts/2026-06-18-three-fixes-in-sentence-transformers-v56">Two correctness fixes and a scalability fix in v5.6.0</a></h3>
      <p class="entry-body">A full similarity-matrix materialization, a missing rank offset in multi-GPU masking, and a sign-dependent relative margin — merged in one release.</p>
      <p class="meta">sentence-transformers · Mining · GIST · 2026.06 · merged (#3816–3821)</p>
    </article>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <h2 class="section-title">ML systems &amp; evaluation</h2>
    <p class="section-frame">Serving state, dataset validity, and label policy — where the right call is a reproducible test or a measured decision, not a bigger model.</p>
  </div>

  <article class="lead-entry">
    <h3 class="lead-title"><a class="internal" href="posts/2026-07-15-aihub-fds-dataset-validity">The fraud labels were visible in 48 transaction amounts</a></h3>
    <p class="lead-body">Before comparing FDS models, I audited 6.38 million AI-Hub rows. The 4.43M-row electronic-network segment used only 48 transaction amounts, and the range covering 98.97% of its rows contained no positives. A high score could therefore reward recovery of the synthesis template rather than behavior-level fraud detection.</p>
    <p class="lead-result">Published as a reproducible audit <span class="dim">· benchmark rejected for behavior-model comparison · code and evidence public</span></p>
  </article>

  <div class="entries">
    <article class="entry">
      <h3 class="entry-title"><a class="internal" href="posts/2026-02-17-when-negative-labels-cant-be-trusted-pu-learning">Treating unreviewed cases as a third label</a></h3>
      <p class="entry-body">Labeling cases that are merely awaiting review as negatives turns past investigation policy into the model's ground truth, so I split "unreviewed" into its own label and measured the selection bias.</p>
      <p class="meta">Label Quality · PU Learning · 2026.02</p>
    </article>
    <article class="entry">
      <h3 class="entry-title"><a class="internal" href="posts/2026-02-16-choosing-a-model-at-0.5-percent-positives">Choosing a model when only 0.5% of cases are positive</a></h3>
      <p class="entry-body">The investigation team can process about 100 cases a day, which turns abstract model metrics into an actual investigation policy under that capacity limit.</p>
      <p class="meta">Model Evaluation · Precision@K · 2026.02</p>
    </article>
    <article class="entry">
      <h3 class="entry-title"><a class="internal" href="posts/2026-07-14-snapshotting-generation-output-in-transformers-continuous-batching">Streaming text changed after it had already been sent</a></h3>
      <p class="entry-body">In batched generation, chunks already streamed to the user could change retroactively because the output read from live shared buffers.</p>
      <p class="meta">Transformers · Serving · 2026.07 · merged (#46670)</p>
    </article>
  </div>
</section>
