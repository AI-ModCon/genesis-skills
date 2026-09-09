
# Example Tasks

## Basic Examples
* `sciq`: example of `multiple_choice` output type with standard metrics and prompt formatting. **Start here for multiple-choice tasks.**
* `gsm8k`: example of free-form question answering and few-shot prompting (`gsm8k-cot.yaml`). **Start here for generative QA tasks.**
* `logiqa2`: example of multiple-choice question answering with both log-likelihood-based and generative evaluation methods.
* `wikitext`: example of a text completion task using `loglikelihood_rolling` output type and perplexity-based metrics.

## Advanced Examples
* `eq_bench`: example of calculating a custom metric in `utils.py`.
* `pisa`: example of implementing LLM-as-a-judge metrics.
* `common_patterns`: **examples of regex extraction, utility functions, templates vs functions, and data preprocessing patterns**. See this for edge cases and advanced techniques.