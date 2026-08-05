# Troubleshooting Guide

This guide documents common failure modes when creating lm-evaluation-harness configurations and how to recover from them.

## Common Errors During Testing

### "Task not found" or "No tasks matched"

**Symptoms**: 
```
Error: Task 'my_task' not found
```

**Causes**:
- Task name doesn't match the YAML filename (without .yaml extension)
- `include_path` points to wrong directory
- YAML file has syntax errors preventing it from loading
- Task is in a subdirectory but not properly referenced

**Solutions**:
1. Verify task name matches YAML filename: `my_task.yaml` → task name is `my_task`
2. Check `include_path` points to parent directory of task folder
3. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('path/to/task.yaml'))"`
4. For nested tasks, ensure `group` field is set correctly in YAML
5. Check for typos in `--tasks` argument

**Prevention**: Always test with `--include_path` pointing to the correct directory.

---

### Metrics return None or NaN

**Symptoms**:
```json
{
  "accuracy": null,
  "my_metric": NaN
}
```

**Causes**:
- `process_results` function returns wrong structure
- Filter removes all samples before metrics are computed
- Metric function receives unexpected input format
- Division by zero in metric calculation

**Solutions**:
1. Check `process_results` returns a dict with metric names as keys
2. Verify filter doesn't eliminate all valid samples
3. Add defensive checks in custom metric functions:
   ```python
   def my_metric(items):
       if not items:
           return {"my_metric": 0.0}  # or appropriate default
       # ... metric calculation
   ```
4. Print debug info in `process_results` to see what data structure is being received

**Prevention**: Test `process_results` and filter functions independently before full evaluation.

---

### Empty or malformed model outputs

**Symptoms**:
- Model generates empty strings
- All outputs are truncated
- Outputs contain only partial responses

**Causes**:
- `until` token stops generation too early
- `max_gen_toks` is too small
- Prompt is malformed (e.g., missing instruction)
- Model doesn't understand the task format

**Solutions**:
1. Review `generation_kwargs`:
   ```yaml
   generation_kwargs:
     max_gen_toks: 256  # Increase if needed
     until: ["\n\n"]    # Use double quotes for escape sequences!
     do_sample: false
   ```
2. Inspect prompts using `display_sample_results.py` to verify formatting
3. Check if `doc_to_text` produces valid prompts
4. Test with a few-shot example to help model understand format
5. Verify the prompt template includes clear instructions

**Prevention**: Always inspect sample prompts before running full evaluation.

---

### "Filter returned empty results"

**Symptoms**:
```
Warning: Filter removed all samples for task 'my_task'
```

**Causes**:
- Filter function is too restrictive
- Filter expects different input format than provided
- All samples fail the filter condition

**Solutions**:
1. Review filter logic in `utils.py` - add debug prints
2. Check what `filtered_resps` looks like before filtering
3. Temporarily disable filter to see unfiltered results
4. Verify filter handles edge cases (None, empty strings, etc.)

**Prevention**: Test filter with diverse sample inputs including edge cases.

---

### YAML parsing errors

**Symptoms**:
```
yaml.scanner.ScannerError: while scanning a simple key
```

**Causes**:
- Incorrect indentation (mixing tabs and spaces)
- Unquoted strings with special characters
- Missing quotes around escape sequences (like `\n`)

**Solutions**:
1. Use **spaces only** for indentation (2 or 4 spaces consistently)
2. Quote strings containing special YAML characters: `: { } [ ] , & * # ? | - < > = ! % @ \`
3. Use double quotes for escape sequences: `until: ["\n"]` not `until: ['\n']`
4. Validate YAML: `python -c "import yaml; yaml.safe_load(open('task.yaml'))"`
5. Use a YAML linter: `yamllint task.yaml`

**Prevention**: Follow the patterns in working example configurations.

---

### Template variables not replaced (e.g., "{{doc.question}}")

**Symptoms**:
- Prompts contain literal `{{doc.question}}` instead of actual question text
- Error: `'dict' object has no attribute 'question'`

**Causes**:
- Jinja2 template syntax errors
- Field name doesn't exist in document
- Using wrong template engine syntax

**Solutions**:
1. Verify field names match dataset: print `doc.keys()` in `doc_to_text`
2. Check template syntax - use `{{doc['field']}}` for dict keys with special chars
3. Test template rendering separately:
   ```python
   from jinja2 import Template
   template = Template("{{doc.question}}")
   print(template.render(doc=sample_doc))
   ```
4. Use `!function` instead of template if logic is complex

**Prevention**: Test templates with sample documents before full evaluation.

---

### Import errors in utils.py

**Symptoms**:
```
ImportError: cannot import name 'my_function' from 'utils'
```

**Causes**:
- Function not defined in `utils.py`
- Circular import issues
- Python path not set correctly
- Syntax error in `utils.py` prevents import

**Solutions**:
1. Verify function exists and is defined at module level (not nested)
2. Check for syntax errors: `python -c "import utils"`
3. Ensure `utils.py` is in the same directory as the YAML file
4. Check function name spelling matches exactly

**Prevention**: Test import separately: `python -c "from utils import my_function"`

---

## Data Loading Issues

### HuggingFace dataset not found

**Symptoms**:
```
DatasetNotFoundError: Dataset 'my_dataset' doesn't exist on the Hub
```

**Solutions**:
1. Verify dataset name at https://huggingface.co/datasets
2. Check if dataset requires authentication: `huggingface-cli login`
3. For private datasets, ensure you have access permissions
4. Verify spelling and case (datasets are case-sensitive)

---

### Wrong split name

**Symptoms**:
```
ValueError: Split name 'test' does not exist
```

**Solutions**:
1. Check available splits: `load_dataset("dataset_name", split=None)` in Python
2. Common variations: `test` vs `testing`, `validation` vs `val` vs `dev`
3. Some datasets only have `train` split

---

### Dataset configuration missing

**Symptoms**:
```
ValueError: Config name is missing
```

**Solutions**:
1. Check dataset page for required configurations
2. Set `dataset_name: <config>` in YAML
3. List available configs: `datasets.get_dataset_config_names("dataset_name")`

---

## Performance Issues

### Evaluation is too slow

**Causes**:
- Processing entire dataset
- Inefficient `process_docs` function
- Model loading issues

**Solutions**:
1. Use `--limit` flag for testing: `--limit 10`
2. Optimize `process_docs` - avoid redundant operations
3. Cache heavy computations
4. Use faster model for initial testing

---

### Out of memory errors

**Causes**:
- Batch size too large
- Model too large for GPU
- Memory leak in custom functions

**Solutions**:
1. Reduce batch size in model_args: `batch_size=1`
2. Use smaller model for testing
3. Check custom functions for memory leaks
4. Use `dtype=float16` for model loading

---

## Debugging Strategies

### Strategy 1: Isolate the problem

1. Test with `--limit 1` to process just one sample
2. Add debug prints to custom functions
3. Test each component independently (filter, metric, etc.)

### Strategy 2: Compare with working examples

1. Find a similar task in `assets/examples/`
2. Compare YAML structure field by field
3. Test the example task to ensure your environment works

### Strategy 3: Enable verbose logging

```bash
export LMEVAL_LOG_LEVEL=DEBUG
lm_eval --model hf --tasks my_task ...
```

This shows:
- Task loading process
- Document processing
- Prompt construction
- Model calls
- Filtering and metric computation

### Strategy 4: Inspect intermediate outputs

1. Use `--log_samples` to save all prompts and responses
2. Use `display_sample_results.py` to review them
3. Check if prompts look correct
4. Verify model outputs are parsed correctly
5. Confirm metrics are calculated as expected

---

## When to Ask for Help

Ask the user for guidance when:

1. **After 3 failed fix attempts** - you might be missing context about the task requirements
2. **Ambiguous evaluation semantics** - unclear what "correct" means
3. **Data quality issues** - dataset has significant problems that affect validity
4. **Performance tradeoffs** - multiple valid approaches with unclear preferences
5. **Missing information** - need clarification on task specifications

Don't waste time iterating endlessly on a fundamental misunderstanding - ask early if something is unclear.
