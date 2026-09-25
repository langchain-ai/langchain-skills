# Converting an existing agent to route on a decision model

A six-step audit for finding where typed classification replaces a generative call, and for proving it was worth doing. The framing of steps 1–2 is adapted from [jevify](https://github.com/ryana/jevify), a prompt for investigating what a decision model makes possible in an existing project.

Keep exploration separate from production changes. Do not edit the agent until step 6.

---

## 1. Understand the project as it is

Read the real code, not the README. For each model call, record: what it costs, what it returns, and what the caller actually *uses* from the return.

Tie every finding to a specific file and line. Look for:

- **Generate-then-parse.** A completion immediately fed to `json.loads`, a regex, or `.startswith(...)`. The prose was never the product.
- **Prompted classifiers.** Prompts containing "respond with one of", "answer yes or no", "rate 1–5", "reply ONLY with".
- **Budget-driven sampling.** Code that checks the first N items, or runs a check only on weekends, because doing it always is too expensive.
- **Brittle proxies.** Keyword lists, regexes, or heuristics standing in for semantic judgment because a model call was too slow or costly.
- **Re-reading.** The same document sent to a model repeatedly, once per question.

## 2. Reconsider from first principles

The pivot question: **if many semantic judgments were affordable inside your latency budget, what would you design differently?**

Sort ideas into three buckets, and give the third real weight:

1. **Direct savings** — same behavior, lower cost or latency.
2. **Better outcomes** — same feature, better decisions (judging every item instead of sampling).
3. **New capabilities** — things currently impossible: reacting mid-interaction, continuously reassessing state, filtering a firehose.

Bucket 3 is where the leverage is. Bucket 1 is the easiest to justify and the least interesting.

## 3. Make each opportunity concrete

For every candidate, write down:

- The integration point — which node, which file.
- The input state — exactly what gets sent.
- Which primitives apply — `Noul`, `Choice`, or `Score`, and why.
- Which questions **share one request** versus genuinely depend on a prior answer. Questions in one request are answered independently; if B depends on A's answer, they are two requests and two nodes.
- How plain code consumes the result — the routing function, in full.
- What still needs generation or retrieval. Most workflows keep an LLM for the part that produces text; the decision model only picks *which* items get there.

**Do not bury hard reasoning in a fuzzy question.** "Is this code correct?" is not a classification. If a question needs multi-step reasoning to answer, it needs a reasoning model.

## 4. Test the economics honestly

Estimate the whole workflow, not one call: retries, fallbacks, the escalation path, and the generative work that remains.

- Separate **per-request latency** from **end-to-end**. Fan-out changes the second and not the first.
- Compare against the cheaper alternatives you skipped: deterministic code, caching, embeddings, a smaller model. Sometimes a regex really is the right answer.
- If you have no measurements yet, state the assumption and the break-even point rather than a number you cannot defend.

When benchmarking against an LLM baseline, make the baseline fair — native structured output (`method="json_schema"`), no tool-schema injection, caching enabled on any stable prompt prefix. An unfair baseline makes the result useless for deciding anything.

## 5. Design an evaluation that can falsify the idea

A decision model returns probabilities. Probabilities are signals whose calibration must be tested **on your workload**; vendor benchmarks do not transfer.

- **Baselines** — current behavior, and the cheapest non-model alternative.
- **Asymmetric costs** — a false negative on a privilege check is not a false positive on a spam check. Weight them.
- **Latency distribution** — p50 and p99, not the mean.
- **Adversarial and ambiguous inputs** — items that *should* land mid-rubric. These are where thresholds get decided.
- **Threshold and fallback validation** — sweep thresholds against labeled data. Do not hand-pick them from a handful of examples.
- **Go/no-go criteria, written before you run it.**

`langsmith-skills` covers dataset construction and evaluators for this step.

## 6. Deliver a recommendation

- A ranked table of opportunities with expected impact and confidence.
- Detailed designs for the top three.
- A sketch of how the system would look if designed this way from scratch — often different from the incremental patch.
- The **smallest decisive experiment**: the one change that would settle it.
- Rejected ideas, with reasons. These are as valuable as the accepted ones.

---

## Migration shapes

**Prompted classifier → one classifier node.** The direct swap. The prompt's enumerated options become `Choice.criteria`; its rating scale becomes `Score.criteria`; its yes/no becomes a `Noul`. Delete the parsing code — that is the point.

**Chain of LLM guards → one request, many questions.** Sequential guardrail calls that each ask one yes/no collapse into a single request with several `Noul`s, then a routing function. Only do this where the guards are genuinely independent.

**Sampling → full coverage.** Where cost forced you to check 1 in 100, check all of them and route the uncertain ones to the expensive path. This usually improves the product, not just the bill.

**Keyword rules → semantic questions.** Replace regex allowlists with a `Noul` plus a threshold. Keep the regex as a fast path if it is precise; use the model for the tail it cannot cover.

---

## Rollout

1. Run the decision model **in shadow** beside existing logic. Log both decisions; change nothing.
2. Compare on real traffic. Disagreements are your evaluation set — label them.
3. Tune thresholds against those labels, not against intuition.
4. Cut over the decisive bands first; keep humans or the LLM on the ambiguous middle.
5. Pin the model id and re-validate thresholds on every model change — calibration shifts between versions.
