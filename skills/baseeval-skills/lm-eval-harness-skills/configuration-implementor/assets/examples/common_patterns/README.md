# Common Patterns and Edge Cases

This directory contains examples demonstrating advanced patterns and edge cases in lm-evaluation-harness configurations.

## Examples

### regex_extraction.yaml
**Use when**: Model outputs are verbose and you need to extract specific answers using patterns.

**Demonstrates**:
- Using regex to extract numeric answers from free-form text
- Multiple fallback patterns for robustness
- Normalization of numeric strings for comparison
- Custom filter functions

**Common use cases**:
- Math problems where model explains reasoning before giving answer
- QA tasks where answer is embedded in explanation
- Any task where output format varies

**Key takeaway**: Build multiple regex patterns with fallbacks, since model outputs can be unpredictable.

---

### functions_and_preprocessing.yaml
**Use when**: You need to choose between templates, field names, and functions.

**Demonstrates**:
- When to use Jinja2 templates vs `!function` vs simple field names
- `process_docs` for filtering and restructuring dataset
- Creating simple utility functions in utils.py
- Adding computed fields to documents

**When to use each approach**:
- **Use Jinja2 template** for:
  - Simple field access with formatting: `"Question: {{question}}\n"`
  - String interpolation: `"Context: {{context}}\nQ: {{question}}"`
  - Conditional text: `"{% if context %}Context: {{context}}\n{% endif %}Q: {{question}}"`

- **Use field name** for:
  - Direct field access with no transformation: `doc_to_target: "answer"`
  - When the field already has the exact format needed

- **Use !function** for:
  - Multi-step logic
  - List transformations (e.g., formatting choices)
  - Conditional logic beyond simple templates
  - Error handling
  - Reusable operations
  - Code that needs comments/documentation

**Common use cases**:
- Reformatting field names
- Creating choice labels (A/B/C/D)
- Complex string manipulations
- Data validation and filtering

---

## Pattern Decision Guide

### Choosing the Right Approach

#### For Answer Extraction

| Model Output Style | Recommended Approach | Example |
|-------------------|---------------------|---------|
| Predictable format | Template + target field | `doc_to_target: "answer"` |
| Multiple patterns | Regex with fallbacks | See `extract_numeric_answer()` |
| Always structured | Simple function | `!function utils.extract_answer` |
| Highly variable | Custom filter function | Full function with error handling |

#### For Data Preprocessing

| Need | Approach | Example |
|------|----------|---------|
| Filter invalid samples | `process_docs` | Remove null/empty fields |
| Add computed fields | `process_docs` | Add `answer_idx` from choices |
| Shuffle for bias | `process_docs` | Randomize choice order |
| Simple field rename | Template in YAML | `doc_to_text: "{{q}}"` |

#### For Prompt Construction

| Complexity | Approach | Example |
|-----------|----------|---------|
| Simple template | Jinja2 in YAML | `"Q: {{question}}\nA:"` |
| Conditional content | Jinja2 conditionals | `"{% if context %}Context: {{context}}\n{% endif %}Q: {{question}}"` |
| Complex logic | `doc_to_text` function | Multiple conditions, formatting |

---

## Common Edge Cases

### Empty or None Values
**Problem**: Model outputs empty string or None
**Solution**: 
```python
def safe_extract(text):
    if not text:
        return ""  # or appropriate default
    # ... extraction logic
```

### Unicode and Special Characters
**Problem**: Quotes, newlines, or unicode break parsing
**Solution**:
- Use double quotes in YAML for escape sequences: `until: ["\n"]`
- Normalize unicode: `text.encode('ascii', 'ignore').decode()`
- Handle quotes: `text.replace('"', '')`

### Case Sensitivity
**Problem**: "Yes" vs "yes" vs "YES"
**Solution**:
```python
def normalize_case(text):
    return text.strip().lower()
```

### Number Formatting
**Problem**: "1,000" vs "1000" vs "1000.0"
**Solution**: See `normalize_number()` in utils.py

### Multiple Valid Answers
**Problem**: ["cat", "feline", "kitty"] all correct
**Solution**:
```python
def check_answer(pred, targets):
    return any(pred.lower() == t.lower() for t in targets)
```

### Parsing Failures
**Problem**: Regex doesn't match, extraction fails
**Solution**:
- Always have a fallback: return original text
- Log failures for debugging
- Test with edge cases

---

## Anti-Patterns to Avoid

### ❌ Don't: Try to do complex logic in YAML
```yaml
# This won't work - YAML doesn't support inline Python logic
doc_to_text: "{{'\n'.join([f'{k}: {v}' for k, v in doc.items() if k != 'id'])}}\nAnswer:"
```

**✅ Do**: Use a function for complex logic
```python
def format_doc(doc):
    """Format document as prompt."""
    lines = [f"{k}: {v}" for k, v in doc.items() if k != 'id']
    return "\n".join(lines) + "\nAnswer:"
```

Then in YAML:
```yaml
doc_to_text: !function utils.format_doc
```

### ❌ Don't: Silent failures
```python
def extract(text):
    match = re.search(pattern, text)
    return match.group(1)  # Crashes if no match!
```

**✅ Do**: Handle failures gracefully
```python
def extract(text):
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return text  # Fallback to original
```

### ❌ Don't: Assume data is clean
```python
answer_idx = doc['choices'].index(doc['answer'])  # Crashes if answer not in choices!
```

**✅ Do**: Validate assumptions
```python
try:
    answer_idx = doc['choices'].index(doc['answer'])
except ValueError:
    # Handle case where answer not in choices
    answer_idx = 0  # or skip this sample
```

---

## Testing Your Patterns

Always test with:
1. **Happy path**: Normal, well-formed inputs
2. **Empty values**: `""`, `None`, `[]`
3. **Edge cases**: Very long/short text, special characters
4. **Malformed input**: Unexpected formats
5. **Boundary conditions**: Min/max values

Example test:
```python
# Test numeric extraction
test_cases = [
    ("The answer is 42", "42"),
    ("42", "42"),
    ("= 42", "42"),
    ("forty-two", "forty-two"),  # Should return as-is
    ("", ""),
    ("No numbers here", "No numbers here"),
]

for input_text, expected in test_cases:
    result = extract_numeric_answer(input_text)
    assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
```

---

## When to Ask for Help

If you're unsure whether to use template vs. function:
- Start simple (Jinja2 template for formatting, field name for direct access)
- If you need logic or transformations, use !function
- If it's reusable across tasks, put in utils.py
- If it's still unclear, look at similar existing tasks

Remember: **Clarity > Cleverness**. A readable function is better than trying to force logic into templates.
