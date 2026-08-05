---
name: data-exploration
description: Writes python scripts to ingest the user provided data and perform analysis needed to determine key configuration components. Use this skill after the configuration-planner skill completes.
---

# Steps

1. Read the configuration plan in `tasks/{benchmark_name}/plan.md` to understand the initial plan for the evaluation.

2. Determine what data analysis steps will be needed to fully define the configuration. Use the **Data Analysis Checklist** below to guide your exploration.

3. Write Python scripts to implement the planned analysis. Save all scripts in `tasks/{benchmark_name}/scratch/`. Scripts should be modular and reusable, not just one-off commands. See `assets/analyze_multiple_choice.py` and `assets/analyze_generative_qa.py` for example templates that can be adapted.

4. Run the analysis scripts and analyze the results. Document findings systematically.

5. Update `tasks/{benchmark_name}/plan.md` to incorporate new information from the analysis, focusing on a concrete plan for the `process_docs`, `doc_to_text`, `doc_to_target`, output parsing, and `process_results` implementations. Add a **Decision Log** section documenting key findings and choices.

6. Verify analysis completeness using the **Data Analysis Checklist** below. Track checklist progress in `plan.md`.

7. Provide a concise checkpoint summary. Ask the user for concurrence before proceeding to implementation.

CRITICAL: Do not create the YAML file or `utils.py` at this stage. Only modify `plan.md` and add analysis artifacts under `tasks/{benchmark_name}/scratch/`.

# Data Analysis Checklist

Use this checklist to systematically explore the data. Copy this checklist into `plan.md` and track progress there.

## Data Quality & Structure
- [ ] **Null/missing values**: Check for null, empty, or missing fields in key columns
- [ ] **Field consistency**: Verify all samples have expected fields with consistent types
- [ ] **Record count**: Confirm number of samples matches expectations
- [ ] **Split distribution**: Check size of train/val/test splits

## Input Data (Questions/Prompts)
- [ ] **Format variations**: Identify different question formats or templates
- [ ] **Length distribution**: Min/max/median length of questions
- [ ] **Special characters**: Check for problematic characters (quotes, newlines, Unicode)
- [ ] **Encoding issues**: Verify text encoding is correct

## Target Data (Ground Truth Answers)
- [ ] **Answer format**: Document the format(s) of correct answers
- [ ] **Multiple correct answers**: Check if multiple valid answers exist per question
- [ ] **Answer variations**: Identify synonyms, case variations, punctuation differences
- [ ] **Numeric answers**: If applicable, check for formatting (1,000 vs 1000, decimals, units)
- [ ] **List/structured answers**: If answers are lists/JSON, verify structure consistency

## Multiple Choice Specific (if applicable)
- [ ] **Number of choices**: Verify all questions have same number of options (or document variations)
- [ ] **Choice labels**: Check if options use consistent labels (A/B/C, 0/1/2, etc.)
- [ ] **Correct answer encoding**: Verify how correct answer is indicated (index, letter, text)
- [ ] **Distractor quality**: Sample some incorrect options to understand patterns

## Edge Cases & Special Handling
- [ ] **Empty answers**: Check for questions with empty or very short answers
- [ ] **Long answers**: Identify extremely long answers that might need truncation
- [ ] **Ambiguous cases**: Flag questions that might have unclear correct answers
- [ ] **Context dependencies**: Check if questions require external context or images
- [ ] **Code/math/special formatting**: Identify if answers contain code, LaTeX, or special notation

## Metric Implementation
- [ ] **Exact match feasibility**: Can answers be compared with exact string match?
- [ ] **Normalization needs**: Document what normalization is needed (case, whitespace, punctuation)
- [ ] **Parsing complexity**: Estimate complexity of extracting answer from model output
- [ ] **Metric appropriateness**: Verify planned metrics match the task (e.g., BLEU for translation, accuracy for MC)

# Analysis Script Template

When writing analysis scripts, follow this structure:

```python
#!/usr/bin/env python3
"""
Analysis: <What this script analyzes>
Purpose: <Why this analysis is needed>
"""

import json
from collections import Counter
from datasets import load_dataset
# Add other imports as needed

def load_data():
    """Load the dataset for analysis."""
    # Implementation
    pass

def analyze_field_types():
    """Check field presence and types across all samples."""
    # Implementation
    pass

def analyze_answer_formats():
    """Analyze the format and variations in answers."""
    # Implementation
    pass

def check_edge_cases():
    """Identify edge cases and special formatting needs."""
    # Implementation
    pass

def main():
    print("="*60)
    print("Data Analysis for <benchmark_name>")
    print("="*60)
    
    data = load_data()
    
    print("\n1. Field Types and Consistency")
    analyze_field_types()
    
    print("\n2. Answer Format Analysis")
    analyze_answer_formats()
    
    print("\n3. Edge Cases")
    check_edge_cases()
    
    print("\n" + "="*60)
    print("Analysis Complete")
    print("="*60)

if __name__ == "__main__":
    main()
```

# Decision Log Format

When updating `plan.md`, append a section like:

```markdown
## Data Exploration Decision Log

**Date**: <date>

**Key Findings**:
- Finding 1: <observation>
- Finding 2: <observation>

**Decisions Made**:
- Decision 1: <choice> - **Why**: <rationale>
- Decision 2: <choice> - **Why**: <rationale>

**Implementation Impact**:
- `doc_to_target`: <specific change needed>
- Output parsing: <specific change needed>
- Metrics: <specific change needed>

**Edge Cases Identified**:
- Edge case 1: <description> - **Handling**: <approach>

**Assumptions**:
- Assumption 1: <assumption> - **Risk**: <if wrong, what breaks?>
```

