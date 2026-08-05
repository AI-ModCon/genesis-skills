
# Benchmark Summary

Add a short description of the benchmark and what capability it measures.

**Example**: "GSM8K measures grade-school math problem solving with chain-of-thought reasoning."

---

# Configuration Details

## Basic Information

*Benchmark name:* Canonical task name to use in `tasks/{benchmark_name}/`

*Data source location:* 
- Dataset path or Hugging Face identifier: `dataset_path: "..."`
- Config/subset (if applicable): `dataset_name: "..."` or `null`
- Example: `dataset_path: "gsm8k"`, `dataset_name: "main"`

*Data splits:* 
List exact splits and their purpose:
- `test_split: "test"` - Primary evaluation split
- `validation_split: "validation"` or `null`
- `training_split: "train"` or `null`
- `fewshot_split: "train"` - Where to draw few-shot examples from (if applicable)

*Record schema:* 
Describe the structure of each data sample with field names and types:
- Input field(s): `question` (str), `context` (str), etc.
- Answer field(s): `answer` (str/int), `choices` (list), etc.
- Example: `{"question": str, "choices": [str, str, str, str], "answer": int}`

## Task Configuration

*Task output format:* Choose ONE:
- `output_type: generate_until` - For free-form text generation
- `output_type: loglikelihood` - For scoring likelihood of given completions
- `output_type: loglikelihood_rolling` - For perplexity/next-token prediction
- `output_type: multiple_choice` - For selecting best of fixed options

*Prompt template:* 
Describe the full prompt structure with concrete example:
```
<system instructions if any>

<few-shot examples if used>

Question: {{doc.question}}
<choices if multiple choice>

Answer:
```
**Example**: 
```
Question: If John has 5 apples and gives 2 away, how many does he have left?
A) 2
B) 3
C) 5
D) 7

Answer: Let's solve this step by step.
```

*Target extraction:* 
Explain exactly how `doc_to_target` derives the ground-truth answer:
- **Field access**: Which field(s) contain the answer? `doc['answer']`
- **Format**: String? Integer? List?
- **Transformations**: Any preprocessing needed?
- **Example**: `doc_to_target: "answer"` or `doc_to_target: "!function utils.extract_target"`

*Output post-processing:* 
Explain how model outputs should be parsed before comparison:
- **Parsing strategy**: regex / split / custom function
- **Normalization**: lowercase / strip whitespace / remove punctuation
- **Edge cases**: Empty outputs, malformed responses, multiple answers
- **Example**:
  ```python
  # Extract answer from "The answer is: 42"
  def extract_answer(output):
      match = re.search(r'answer is:?\s*(\d+)', output.lower())
      return match.group(1) if match else output.strip()
  ```

*Metrics / process_results:* 
List metrics and how they're computed:
- **Built-in metrics**: `exact_match`, `f1`, `acc`, etc.
- **Custom metrics**: Name and brief formula
- **Aggregation**: Mean, weighted, etc.
- **process_results structure**:
  ```python
  def process_results(doc, results):
      # results[0] contains the model output or list of outputs
      return {
          "acc": 1.0 if parsed_output == target else 0.0
      }
  ```

## Implementation Plan

*Custom code required:* 
Check all that apply and describe implementation:
- [ ] `process_docs`: <what transformation needed?>
- [ ] `doc_to_text`: <if template complex, describe>
- [ ] `doc_to_target`: <if needs custom extraction>
- [ ] `filter`: <what to filter and why?>
- [ ] Custom metrics in `utils.py`: <metric name and purpose>
- [ ] Helper functions: <list any utilities needed>

*Validation plan:* 
Describe testing approach:
1. Test with `--limit 5` first
2. Check prompts contain expected content
3. Verify model outputs parse correctly
4. Confirm metrics are in expected range (e.g., 0-1 for accuracy)
5. Spot-check at least 5 samples manually for correctness
6. Compare with baseline results if available

*Open questions / assumptions:* 
List any unresolved choices or assumptions:
- **Assumption**: <what you're assuming>
  - **Risk if wrong**: <what breaks?>
  - **Validation**: <how to verify?>

**Example**:
- **Assumption**: Answers are case-insensitive
  - **Risk if wrong**: Accuracy will be artificially low
  - **Validation**: Check if ground truth answers have consistent casing

---

# Definition of Done (Planner)

Before proceeding to data exploration, verify:
- [ ] All configuration fields above are filled out
- [ ] At least one concrete example of prompt and expected output shown
- [ ] Output parsing strategy is clearly defined
- [ ] Metric implementation approach is specified
- [ ] High-risk assumptions are documented with validation plans
- [ ] No unresolved questions that would change task semantics

---

# Verification Checklists

*This section will be updated by subsequent stages (data-exploration, testing)*

---

# Implementation Notes

*This section will be updated by subsequent stages (data-exploration, implementation, testing)*