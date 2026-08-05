#!/usr/bin/env python3
"""
Example analysis script for multiple-choice datasets.
Adapt this template for your specific dataset structure.
"""

import json
from collections import Counter, defaultdict
from datasets import load_dataset
import sys


def load_data(dataset_path, dataset_name=None, split='test'):
    """Load the dataset for analysis."""
    try:
        if dataset_name:
            dataset = load_dataset(dataset_path, dataset_name, split=split)
        else:
            dataset = load_dataset(dataset_path, split=split)
        return dataset
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print(f"Path: {dataset_path}, Name: {dataset_name}, Split: {split}")
        sys.exit(1)


def analyze_structure(dataset):
    """Analyze the basic structure of the dataset."""
    print(f"Total samples: {len(dataset)}")
    print(f"\nAvailable fields: {dataset.column_names}")

    # Show first example
    print("\n--- First Example ---")
    first_item = dataset[0]
    for key, value in first_item.items():
        value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
        print(f"  {key}: {value_str}")


def analyze_multiple_choice_structure(dataset, question_field, choices_field, answer_field):
    """Analyze multiple choice specific structure."""
    print("\n--- Multiple Choice Analysis ---")

    # Check number of choices
    num_choices = []
    answer_types = Counter()
    answer_values = Counter()

    for i, item in enumerate(dataset):
        choices = item.get(choices_field, [])
        num_choices.append(len(choices))

        answer = item.get(answer_field)
        answer_types[type(answer).__name__] += 1

        # Try to understand answer format
        if isinstance(answer, int):
            answer_values['int_index'] += 1
        elif isinstance(answer, str):
            if len(answer) == 1 and answer.isalpha():
                answer_values['letter'] += 1
            elif answer.isdigit():
                answer_values['string_digit'] += 1
            else:
                answer_values['text'] += 1

    choice_counts = Counter(num_choices)
    print(f"\nNumber of choices per question:")
    for count, freq in sorted(choice_counts.items()):
        print(f"  {count} choices: {freq} questions")

    print(f"\nAnswer type distribution:")
    for atype, count in answer_types.items():
        print(f"  {atype}: {count}")

    print(f"\nAnswer format distribution:")
    for fmt, count in answer_values.items():
        print(f"  {fmt}: {count}")

    # Sample some answers
    print(f"\nSample answers (first 10):")
    for i in range(min(10, len(dataset))):
        answer = dataset[i].get(answer_field)
        print(f"  Sample {i}: {answer} (type: {type(answer).__name__})")


def analyze_text_fields(dataset, question_field):
    """Analyze text field characteristics."""
    print("\n--- Question Text Analysis ---")

    lengths = []
    has_special_chars = defaultdict(int)

    for item in dataset:
        text = str(item.get(question_field, ''))
        lengths.append(len(text))

        # Check for special characters
        if '\n' in text:
            has_special_chars['newline'] += 1
        if '\t' in text:
            has_special_chars['tab'] += 1
        if '"' in text or "'" in text:
            has_special_chars['quotes'] += 1
        if '\\' in text:
            has_special_chars['backslash'] += 1

    print(f"Question length statistics:")
    print(f"  Min: {min(lengths)}")
    print(f"  Max: {max(lengths)}")
    print(f"  Mean: {sum(lengths)/len(lengths):.1f}")
    print(f"  Median: {sorted(lengths)[len(lengths)//2]}")

    if has_special_chars:
        print(f"\nSpecial character occurrences:")
        for char_type, count in has_special_chars.items():
            print(f"  {char_type}: {count} samples ({100*count/len(dataset):.1f}%)")


def check_data_quality(dataset, required_fields):
    """Check for missing or malformed data."""
    print("\n--- Data Quality Check ---")

    issues = defaultdict(int)

    for i, item in enumerate(dataset):
        for field in required_fields:
            if field not in item or item[field] is None:
                issues[f'missing_{field}'] += 1
            elif isinstance(item[field], str) and len(item[field].strip()) == 0:
                issues[f'empty_{field}'] += 1

    if issues:
        print("Issues found:")
        for issue, count in issues.items():
            print(f"  {issue}: {count} samples")
    else:
        print("No data quality issues found!")


def main():
    # CONFIGURATION - Update these for your dataset
    DATASET_PATH = "your_dataset_name"  # e.g., "sciq" or "rajpurkar/squad"
    DATASET_NAME = None  # e.g., "main" or None if no config needed
    SPLIT = "test"  # or "validation", "train"

    # Field names in your dataset
    QUESTION_FIELD = "question"
    CHOICES_FIELD = "choices"
    ANSWER_FIELD = "answer"

    print("="*60)
    print(f"Multiple Choice Dataset Analysis")
    print(f"Dataset: {DATASET_PATH}")
    print("="*60)

    # Load data
    dataset = load_data(DATASET_PATH, DATASET_NAME, SPLIT)

    # Run analyses
    analyze_structure(dataset)
    analyze_multiple_choice_structure(dataset, QUESTION_FIELD, CHOICES_FIELD, ANSWER_FIELD)
    analyze_text_fields(dataset, QUESTION_FIELD)
    check_data_quality(dataset, [QUESTION_FIELD, CHOICES_FIELD, ANSWER_FIELD])

    print("\n" + "="*60)
    print("Analysis Complete")
    print("="*60)


if __name__ == "__main__":
    main()
