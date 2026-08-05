#!/usr/bin/env python3
"""
Example analysis script for generative QA datasets (e.g., open-ended questions).
Adapt this template for your specific dataset structure.
"""

import json
import re
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
        sys.exit(1)


def analyze_structure(dataset):
    """Analyze the basic structure of the dataset."""
    print(f"Total samples: {len(dataset)}")
    print(f"\nAvailable fields: {dataset.column_names}")

    # Show first example
    print("\n--- First Example ---")
    first_item = dataset[0]
    for key, value in first_item.items():
        value_str = str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
        print(f"  {key}:")
        print(f"    {value_str}")


def analyze_answer_formats(dataset, answer_field):
    """Analyze the format and variations in answers."""
    print("\n--- Answer Format Analysis ---")

    answer_lengths = []
    answer_types = Counter()
    answer_patterns = defaultdict(int)

    # Categorize answers
    numeric_only = 0
    contains_number = 0
    multiple_sentences = 0
    contains_code = 0

    sample_answers = []

    for i, item in enumerate(dataset):
        answer = item.get(answer_field)

        # Handle different answer field structures
        if isinstance(answer, dict):
            # If answer is a dict (e.g., {"text": [...], "answer_start": [...]})
            if 'text' in answer and isinstance(answer['text'], list):
                answer_text = answer['text'][0] if answer['text'] else ""
            elif 'text' in answer:
                answer_text = str(answer['text'])
            else:
                answer_text = str(answer)
        elif isinstance(answer, list):
            # Multiple possible answers
            answer_text = str(answer[0]) if answer else ""
            if len(answer) > 1:
                answer_patterns['multiple_answers'] += 1
        else:
            answer_text = str(answer)

        answer_lengths.append(len(answer_text))

        # Pattern detection
        if re.match(r'^\d+(\.\d+)?$', answer_text.strip()):
            numeric_only += 1
        if re.search(r'\d', answer_text):
            contains_number += 1
        if len(re.findall(r'[.!?]+', answer_text)) > 1:
            multiple_sentences += 1
        if any(kw in answer_text.lower() for kw in ['def ', 'function', 'import ', '```']):
            contains_code += 1

        # Collect diverse samples
        if i < 5 or i % (len(dataset) // 10) == 0:
            sample_answers.append((i, answer_text[:100]))

    # Length statistics
    print(f"\nAnswer length statistics (characters):")
    print(f"  Min: {min(answer_lengths)}")
    print(f"  Max: {max(answer_lengths)}")
    print(f"  Mean: {sum(answer_lengths)/len(answer_lengths):.1f}")
    print(f"  Median: {sorted(answer_lengths)[len(answer_lengths)//2]}")

    # Answer patterns
    print(f"\nAnswer pattern distribution:")
    print(f"  Numeric only: {numeric_only} ({100*numeric_only/len(dataset):.1f}%)")
    print(f"  Contains numbers: {contains_number} ({100*contains_number/len(dataset):.1f}%)")
    print(f"  Multiple sentences: {multiple_sentences} ({100*multiple_sentences/len(dataset):.1f}%)")
    print(f"  Contains code: {contains_code} ({100*contains_code/len(dataset):.1f}%)")

    if answer_patterns:
        print(f"\nSpecial structures:")
        for pattern, count in answer_patterns.items():
            print(f"  {pattern}: {count}")

    # Sample answers
    print(f"\nSample answers:")
    for idx, answer in sample_answers[:10]:
        print(f"  [{idx}] {answer}...")


def analyze_question_text(dataset, question_field):
    """Analyze question characteristics."""
    print("\n--- Question Analysis ---")

    lengths = []
    question_types = Counter()
    has_context = 0

    for item in dataset:
        question = str(item.get(question_field, ''))
        lengths.append(len(question))

        # Classify question type by first word
        first_word = question.strip().split()[0].lower() if question.strip() else ""
        question_types[first_word] += 1

        # Check if there's a context field
        if 'context' in item or 'passage' in item:
            has_context += 1

    print(f"Question length statistics:")
    print(f"  Min: {min(lengths) if lengths else 0}")
    print(f"  Max: {max(lengths) if lengths else 0}")
    print(f"  Mean: {sum(lengths)/len(lengths):.1f}" if lengths else 0)

    print(f"\nMost common question starters:")
    for word, count in question_types.most_common(10):
        print(f"  '{word}': {count}")

    print(f"\nQuestions with context: {has_context} ({100*has_context/len(dataset):.1f}%)")


def analyze_extraction_complexity(dataset, answer_field):
    """Analyze how complex it will be to extract answers from model outputs."""
    print("\n--- Answer Extraction Complexity ---")

    # Check for variations in answer formatting
    needs_normalization = defaultdict(int)

    for item in dataset:
        answer = item.get(answer_field)

        # Convert to string for analysis
        if isinstance(answer, dict) and 'text' in answer:
            answer_text = answer['text'][0] if isinstance(answer['text'], list) else answer['text']
        elif isinstance(answer, list):
            answer_text = answer[0] if answer else ""
        else:
            answer_text = str(answer)

        answer_text = str(answer_text)

        # Check what normalization might be needed
        if answer_text != answer_text.strip():
            needs_normalization['whitespace'] += 1
        if answer_text != answer_text.lower() and not any(c.isupper() for c in answer_text if c.isalpha()):
            needs_normalization['case'] += 1
        if any(p in answer_text for p in ['.', ',', '!', '?']):
            needs_normalization['punctuation'] += 1
        if 'the ' in answer_text.lower() or 'a ' in answer_text.lower():
            needs_normalization['articles'] += 1

    print("\nNormalization likely needed:")
    for norm_type, count in needs_normalization.items():
        print(f"  {norm_type}: {count} samples ({100*count/len(dataset):.1f}%)")

    print("\nRecommendations:")
    if needs_normalization['whitespace'] > len(dataset) * 0.1:
        print("  - Strip whitespace from answers")
    if needs_normalization['case'] > len(dataset) * 0.1:
        print("  - Consider case-insensitive comparison")
    if needs_normalization['punctuation'] > len(dataset) * 0.3:
        print("  - Consider removing punctuation")
    if needs_normalization['articles'] > len(dataset) * 0.2:
        print("  - Consider removing articles (a, an, the)")


def check_edge_cases(dataset, question_field, answer_field):
    """Identify potential edge cases."""
    print("\n--- Edge Cases ---")

    edge_cases = defaultdict(list)

    for i, item in enumerate(dataset):
        question = str(item.get(question_field, ''))
        answer = item.get(answer_field)

        if isinstance(answer, dict) and 'text' in answer:
            answer_text = answer['text'][0] if isinstance(answer['text'], list) else answer['text']
        elif isinstance(answer, list):
            answer_text = answer[0] if answer else ""
        else:
            answer_text = str(answer)

        answer_text = str(answer_text)

        # Identify edge cases
        if len(answer_text.strip()) == 0:
            edge_cases['empty_answer'].append(i)
        if len(answer_text) > 500:
            edge_cases['very_long_answer'].append(i)
        if len(question) < 10:
            edge_cases['very_short_question'].append(i)
        if '"' in question or "'" in question:
            edge_cases['quoted_content'].append(i)

    for case_type, indices in edge_cases.items():
        print(f"\n{case_type}: {len(indices)} samples")
        if indices:
            print(f"  Example indices: {indices[:5]}")


def main():
    # CONFIGURATION - Update these for your dataset
    DATASET_PATH = "your_dataset_name"  # e.g., "gsm8k" or "squad"
    DATASET_NAME = None  # e.g., "main" or None
    SPLIT = "test"

    QUESTION_FIELD = "question"
    ANSWER_FIELD = "answer"

    print("="*60)
    print(f"Generative QA Dataset Analysis")
    print(f"Dataset: {DATASET_PATH}")
    print("="*60)

    dataset = load_data(DATASET_PATH, DATASET_NAME, SPLIT)

    analyze_structure(dataset)
    analyze_question_text(dataset, QUESTION_FIELD)
    analyze_answer_formats(dataset, ANSWER_FIELD)
    analyze_extraction_complexity(dataset, ANSWER_FIELD)
    check_edge_cases(dataset, QUESTION_FIELD, ANSWER_FIELD)

    print("\n" + "="*60)
    print("Analysis Complete")
    print("="*60)


if __name__ == "__main__":
    main()
