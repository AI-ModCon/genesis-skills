# Requirements and Version Compatibility

This document outlines version requirements and compatibility considerations for lm-evaluation-harness configuration development.

## Minimum Requirements

### lm-evaluation-harness Version
- **Minimum version**: v0.4.0
- **Recommended version**: Latest stable release (check [releases](https://github.com/EleutherAI/lm-evaluation-harness/releases))
- **Breaking changes**: Major version bumps may require YAML config updates

### Python Version
- **Minimum**: Python 3.8
- **Recommended**: Python 3.10 or 3.11

### Core Dependencies
These are installed with lm-evaluation-harness:
- `datasets` (HuggingFace datasets library)
- `transformers` (for HF models)
- `torch` or `jax` (depending on model backend)
- `evaluate` (for some built-in metrics)
- `pyyaml` (for config parsing)
- `jinja2` (for template rendering)

## Version-Specific Features

### Features in v0.4.x+
- YAML-based task configuration
- `!function` directive for calling Python functions from YAML
- Jinja2 templating in prompts (with conditionals, loops, filters)
- Direct field name references for simple cases
- `fewshot_config` for flexible few-shot configuration

### Deprecated Features (avoid using)
- Python-only task definitions (pre-v0.4.0 style)
- Old-style `Task` class inheritance

## Common Package Requirements

### For Custom Metrics
If implementing custom metrics beyond exact match/accuracy:
```bash
pip install scikit-learn  # For F1, precision, recall
pip install rouge-score   # For ROUGE
pip install bert-score    # For BERTScore
pip install sacrebleu     # For BLEU
```

### For Data Processing
```bash
pip install pandas        # For data analysis
pip install numpy         # For numerical operations
```

### For LLM-as-Judge
```bash
pip install anthropic     # For Claude models
pip install openai        # For OpenAI models
```

### For Specific Datasets
Some datasets may require additional packages:
```bash
pip install pillow        # For image datasets
pip install soundfile     # For audio datasets
pip install jsonlines     # For JSONL format
```

## Checking Your Version

### Check lm-eval version
```bash
lm_eval --version
# or
python -c "import lm_eval; print(lm_eval.__version__)"
```

### Check if a feature is available
```python
import lm_eval
from lm_eval.api.task import ConfigurableTask

# Check for function support
hasattr(ConfigurableTask, 'config_to_dict')
```

## Handling Version Compatibility

### Strategy 1: Target Latest Stable
- Use latest features
- Document minimum required version in README
- Easier to maintain

### Strategy 2: Maximum Compatibility
- Avoid bleeding-edge features
- Test on older versions
- More users can run your task

### Strategy 3: Version Detection
Add version checks in `utils.py`:
```python
import lm_eval

def check_version():
    """Verify lm-eval version is compatible."""
    from packaging import version
    min_version = "0.4.0"
    current = lm_eval.__version__
    
    if version.parse(current) < version.parse(min_version):
        raise RuntimeError(
            f"This task requires lm-eval >= {min_version}, "
            f"but found {current}"
        )
```

## Installation Instructions

### Standard Installation
```bash
git clone https://github.com/EleutherAI/lm-evaluation-harness.git
cd lm-evaluation-harness
pip install -e ".[dev]"
```

### With Optional Dependencies
```bash
# For specific model types
pip install -e ".[anthropic]"  # Claude models
pip install -e ".[openai]"     # OpenAI models
pip install -e ".[vllm]"       # vLLM inference
pip install -e ".[math]"       # Math evaluation tasks
```

## Troubleshooting Version Issues

### "YAML directive not supported"
- Update to lm-eval v0.4.0+
- Check directive syntax: `!function` not `!Function`

### "Module not found"
- Install missing dependency: `pip install <package>`
- Check if feature requires optional dependencies

### "Unexpected keyword argument"
- API may have changed between versions
- Check changelog for breaking changes
- Review similar tasks in the current version

### "Task YAML format invalid"
- YAML schema may have changed
- Compare with working examples in current version
- Check for deprecated fields

## Documenting Requirements

When creating a new task, add a comment at the top of the YAML:
```yaml
# Task: my_benchmark
# Requires: lm-eval >= 0.4.0
# Optional dependencies: scikit-learn (for F1 metric)
# Dataset: my_dataset from HuggingFace Hub
```

And in your README:
```markdown
## Requirements
- lm-evaluation-harness >= 0.4.0
- scikit-learn (for custom metrics)
- Dataset available at: https://huggingface.co/datasets/my_dataset
```

## Best Practices

1. **Test on target version**: Don't assume features work without testing
2. **Document dependencies**: List any non-standard packages in comments
3. **Use stable APIs**: Avoid undocumented or internal APIs that may change
4. **Check examples**: Look at recent tasks for current best practices
5. **Pin versions for reproducibility**: In research, document exact versions used
