# FAQ

## Why does this need installing? It doesn't. Why is there a `pyproject.toml`?

The skill is used by symlinking the repository into an agent's skills directory;
the scripts are invoked by path. `pyproject.toml` carries project metadata, the
dependency declaration, and the ruff and pytest configuration. `[tool.uv]
package = false` tells uv to resolve dependencies without installing the project.

## Why was my run refused as partial?

The parser refuses sample-limited runs unless `--allow-partial` is given. A run
capped at five samples validates a configuration; it does not measure a model.
Writing such a score into a card creates a citable claim the model does not
support.

This comes up often because `configuration-tester` in the `lm-eval-harness-skills`
group defaults to `--limit 5`. The right response is usually to re-run without a
limit. If the partial run genuinely needs recording, `--allow-partial` labels it
as partial in every section where a number appears, and the validator enforces
that the label survives.

## Why is `model.id` empty when the harness clearly named a model?

Two cases, both deliberate.

**A custom lm-eval model class.** lm-eval derives `model_name` from
`pretrained`, `model`, `path`, or `engine` in `model_args`. A custom model class
ignores those arguments, so any value there describes something other than what
ran — often a wrapper script's leftover default. The parser discards the name
and asks for `--model-id`.

**No identifying argument at all.** lm-eval then falls back to
`random_name_id()`, an eight-character nonce. That is not a model identity.

NeMo-Skills records no model identity anywhere, so `--model-id` is always
required there.

In every case a supplied identity is marked operator-supplied, and the card
states that it could not be verified against the run.

## Can I edit the generated block by hand?

No. It is regenerated on the next run, and the validator reports the edit as
`UNTRACED` because the content no longer matches the artifacts. To change what
the block says, change the renderer.

Hand-written prose *outside* the `### Automated benchmark results` subtree is
preserved and stays above the generated block.

## Why a visible heading rather than an HTML comment as the anchor?

The BPSW ingestion pipeline (`sync_and_classify_cards.py`) strips HTML and YAML
comments. A `<!-- eval:start -->` marker would vanish downstream, and every
re-run would append a second copy of the block instead of replacing the first.

## Why does re-running leave stale entries in `metrics:`?

Frontmatter entries are never deleted. The tool cannot distinguish an entry it
added from one a person added, and silently dropping someone's metric is worse
than carrying a superseded one. Prune by hand if it matters.

## Eval Factory wraps many harnesses. Is mine supported?

Probably. The adapter targets Eval Factory's *normalized* `results.yml` rather
than any one sub-framework, and iterates metric and score keys generically. It
is verified against `bigcode-evaluation-harness`, `lm-evaluation-harness` and
`simple_evals`, out of roughly 23.

The assumption that does not generalize is scale. Most harnesses report rates in
[0, 1], but some report perplexity, BLEU on a 0-100 scale, token counts or
latency. Values outside [0, 1] are marked `scale: "raw"`, rendered in the
harness's own units and footnoted, so they are never read as fractions.

If you run a harness that has not been verified, inspect the first bundle —
particularly the metric labels and whether anything that should be a rate was
marked raw.

## A benchmark is missing from the bundle.

An Eval Factory task can produce `run_config.yml` but no `results.yml` when
scoring fails. Those tasks are skipped with a warning rather than dropped
silently. Check stderr: a skipped task means a benchmark did not actually run.

## Does this work with agent cards?

No. The BPSW agent card template has no evaluation-results section, and there is
no agentic-evaluation harness output to draw from. Model cards only.

## How do I add support for another consumer, like drift detection?

Add a renderer alongside `scripts/render_card_sections.py` that reads the same
[eval bundle schema](../references/eval-bundle.schema.json). Do not re-parse raw
harness output, and do not reshape the model-card renderer's output — the two
audiences want different reductions of the same run.
