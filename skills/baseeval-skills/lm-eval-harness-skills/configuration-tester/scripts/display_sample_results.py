#!/usr/bin/env python3
"""
Display lm-evaluation-harness results in a human-readable format.
Works with any evaluation format by auto-detecting structure.

Usage:
    python display_sample_results.py <jsonl_file>
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import textwrap
import glob
import argparse

TRUNCATE_LEN = 10000

def parse_jsonl_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse JSONL file and return list of sample dictionaries."""
    samples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


def wrap_text(text: str, width: int = 95, indent: str = "   ") -> str:
    """Wrap text to specified width with indentation."""
    if not text:
        return indent

    text = str(text)
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append(indent)
            continue

        if len(paragraph) <= width - len(indent):
            lines.append(indent + paragraph)
        else:
            words = paragraph.split()
            current_line = indent
            for word in words:
                if len(current_line) + len(word) + 1 > width:
                    lines.append(current_line)
                    current_line = indent + word
                else:
                    current_line += (" " if current_line != indent else "") + word
            if current_line.strip():
                lines.append(current_line)

    return '\n'.join(lines)


def truncate_if_long(text: str, max_length: int = 5000) -> str:
    """Truncate text if it exceeds max_length."""
    text = str(text)
    if len(text) > max_length:
        return text[:max_length] + "... [TRUNCATED DUE TO LENGTH]"
    return text


def is_multiple_choice_logprob(sample: Dict[str, Any]) -> bool:
    """Check if this is multiple-choice format with log probabilities."""
    arguments = sample.get('arguments', {})
    if len(arguments) > 1:
        # Check if all keys follow gen_args_N pattern
        return all(k.startswith('gen_args_') for k in arguments.keys())
    return False


def extract_choice_texts(arguments: Dict[str, Any]) -> List[str]:
    """Extract answer choice texts from arguments."""
    choices = []
    for key in sorted(arguments.keys()):
        if key.startswith('gen_args_'):
            # Look for arg_1 which typically contains the answer choice
            arg_dict = arguments[key]
            if isinstance(arg_dict, dict) and 'arg_1' in arg_dict:
                choices.append(str(arg_dict['arg_1']).strip())
    return choices


def extract_llm_input(arguments: Dict[str, Any]) -> Optional[str]:
    """Extract the actual LLM input prompt from arguments."""
    # For multiple-choice with log probs, arg_0 typically contains the base prompt
    # We'll use the first gen_args entry
    for key in sorted(arguments.keys()):
        if key.startswith('gen_args_'):
            arg_dict = arguments[key]
            if isinstance(arg_dict, dict) and 'arg_0' in arg_dict:
                return str(arg_dict['arg_0'])
    return None


def get_predicted_choice_idx(filtered_resps: List) -> Optional[int]:
    """Get the index of the predicted choice based on highest score."""
    if not filtered_resps:
        return None

    try:
        scores = []
        for resp in filtered_resps:
            if isinstance(resp, list) and len(resp) > 0:
                score = float(resp[0])
                scores.append(score)
            else:
                scores.append(float('-inf'))

        if scores:
            return scores.index(max(scores))
    except (ValueError, TypeError):
        return None

    return None


def display_dict_fields(data: Dict[str, Any], title: str, exclude_keys: set = None, width: int = 95):
    """Display dictionary fields in a readable format."""
    if not data:
        return

    exclude_keys = exclude_keys or set()

    print(f"\n{title}:")
    for key, value in data.items():
        if key in exclude_keys:
            continue

        # Format the value based on its type
        if isinstance(value, (dict, list)):
            value_str = truncate_if_long(json.dumps(value, indent=2), TRUNCATE_LEN)
        else:
            value_str = truncate_if_long(str(value), TRUNCATE_LEN)

        print(textwrap.fill(f"{key}: {value_str}", width=width,
                             initial_indent='\t',
                             subsequent_indent='\t'))
        print('\n')


def display_sample(sample: Dict[str, Any], sample_num: int, total_samples: int, judge_data_list: Optional[List] = None, width: int = 95):
    """Display a single sample based on its structure."""
    doc_id = sample.get('doc_id', 'Unknown')

    print("=" * 100)
    print(f"SAMPLE {sample_num}/{total_samples} (Doc ID: {doc_id})")
    print("=" * 100)

    # Check if this is multiple-choice with log probabilities
    if is_multiple_choice_logprob(sample):
        display_multiple_choice_sample(sample, width=width)
    else:
        display_generic_sample(sample, width=width)

    # Display LLM judge results if available
    if judge_data_list:
        for judge_name, judge_data in judge_data_list:
            display_judge_results(judge_name, judge_data, width=width)

    print("\n")


def display_multiple_choice_sample(sample: Dict[str, Any], width: int = 95):
    """Display multiple-choice format with log probabilities."""
    doc = sample.get('doc', {})
    arguments = sample.get('arguments', {})
    filtered_resps = sample.get('filtered_resps', [])
    target = sample.get('target', None)

    # Display document content
    display_dict_fields(doc, "📝 INPUT/QUESTION DATA", width=width)

    # Extract and display the actual LLM input (prompt)
    llm_input = extract_llm_input(arguments)
    if llm_input:
        print("\n🔤 ACTUAL LLM INPUT (Prompt):")
        print(wrap_text(truncate_if_long(llm_input, TRUNCATE_LEN), width=width))

    # Extract and display answer choices
    choices = extract_choice_texts(arguments)
    if choices:
        predicted_idx = get_predicted_choice_idx(filtered_resps)

        # Try to convert target to int if it's a string
        try:
            target_idx = int(target) if target is not None else None
        except (ValueError, TypeError):
            target_idx = None

        is_correct = (predicted_idx is not None and
                     target_idx is not None and
                     predicted_idx == target_idx)

        print("\n📋 ANSWER CHOICES:")
        for i, choice in enumerate(choices):
            marker = ""
            if i == predicted_idx and i == target_idx:
                marker = " ✅ [CORRECT - Model predicted this]"
            elif i == predicted_idx:
                marker = " ❌ [INCORRECT - Model predicted this]"
            elif i == target_idx:
                marker = " ✓ [Correct answer]"

            # Display log probability if available
            log_prob_str = ""
            if i < len(filtered_resps) and filtered_resps[i]:
                try:
                    score = filtered_resps[i][0]
                    log_prob_str = f" (log_prob: {score})"
                except (IndexError, TypeError):
                    pass

            choice_display = truncate_if_long(choice, 80)
            print(f"   [{i}] {choice_display}{log_prob_str}{marker}")

        print("\n📊 RESULTS:")
        print(f"   Predicted Index:   {predicted_idx}")
        print(f"   Target Index:      {target_idx}")
        print(f"   Status:            {'✅ CORRECT' if is_correct else '❌ INCORRECT'}")
    else:
        # Fallback if we can't extract choices
        print("\n⚠️  Could not extract answer choices")
        display_dict_fields(arguments, "📋 ARGUMENTS (RAW)", width=width)

    # Display metrics
    display_metrics(sample)


def display_generic_sample(sample: Dict[str, Any], width: int = 95):
    """Display sample in generic format."""
    doc = sample.get('doc', {})
    target = sample.get('target', None)
    resps = sample.get('resps', [])
    filtered_resps = sample.get('filtered_resps', [])
    arguments = sample.get('arguments', {})

    # Display document/input
    display_dict_fields(doc, "📝 INPUT/QUESTION DATA", width=width)

    # Try to extract and display the actual LLM input if available
    llm_input = extract_llm_input(arguments)
    if llm_input:
        print("\n🔤 ACTUAL LLM INPUT (Prompt):")
        print(wrap_text(truncate_if_long(llm_input, TRUNCATE_LEN), width=width))

    # Display target/expected output
    if target is not None:
        print("\n✓ TARGET/EXPECTED OUTPUT:")
        print(wrap_text(truncate_if_long(str(target), TRUNCATE_LEN), width=width))

    # Display model responses
    if resps:
        print("\n🤖 MODEL RESPONSE(S):")
        for i, resp in enumerate(resps[:5]):  # Limit to first 5 responses
            resp_str = truncate_if_long(str(resp), TRUNCATE_LEN)
            if len(resps) > 1:
                print(f"   Response {i}:")
                print(wrap_text(resp_str, width=width))
            else:
                print(wrap_text(resp_str, width=width))

    # Display filtered responses if different from resps
    if filtered_resps and filtered_resps != resps:
        print("\n🔍 FILTERED RESPONSE(S):")
        for i, resp in enumerate(filtered_resps[:5]):
            resp_str = truncate_if_long(str(resp), TRUNCATE_LEN)
            if len(filtered_resps) > 1:
                print(f"   Filtered {i}:")
                print(wrap_text(resp_str, width=width))
            else:
                print(wrap_text(resp_str, width=width))

    # Display metrics
    display_metrics(sample)


def display_metrics(sample: Dict[str, Any]):
    """Display all metrics for a sample."""
    # Extract metric names from the 'metrics' field if present
    metric_names = sample.get('metrics', [])

    # Include metadata fields that are useful to display
    metadata_fields = ['metrics', 'filter']

    # Build complete list of fields to display
    fields_to_display = []

    # Add metadata fields first
    for field in metadata_fields:
        if field in sample:
            fields_to_display.append(field)

    # Add actual metric fields
    if isinstance(metric_names, list):
        for metric in metric_names:
            if metric in sample:
                fields_to_display.append(metric)

    if not fields_to_display:
        return

    print("\n📊 METRICS:")
    for field in fields_to_display:
        if 'llm_judge' in field:
            continue
        value = sample[field]
        if isinstance(value, list):
            value_str = ', '.join(str(v) for v in value)
        else:
            value_str = str(value)

        print(f"   {field:20} {value_str}")


def display_judge_results(judge_name: str, judge_data: Dict[str, Any], width: int = 95):
    """Display LLM judge scores and explanation."""
    print(f"\n⚖️  LLM JUDGE EVALUATION: {judge_name}")

    # Check for errors first
    if judge_data.get('error'):
        print(f"   ❌ Error: {judge_data['error']}")
        return

    # Display overall score
    overall_score = judge_data.get('score')
    if overall_score is not None:
        print(f"   Overall Score:      {overall_score}")

    # Display parsed judgment if available
    judgment_parsed = judge_data.get('judgment_parsed')
    if judgment_parsed and isinstance(judgment_parsed, dict):
        # Separate numeric (scores) from non-numeric (explanations) fields
        score_fields = {}
        explanation_fields = {}

        for key, value in judgment_parsed.items():
            if isinstance(value, (int, float)):
                score_fields[key] = value
            else:
                explanation_fields[key] = value

        # Display scores
        if score_fields:
            print("   Scores:")
            for key, value in score_fields.items():
                print(f"      {key:20} {value}")

        # Display explanations/text fields
        if explanation_fields:
            print("\n   Details:")
            for key, value in explanation_fields.items():
                print(f"   {key}:")
                print(wrap_text(truncate_if_long(str(value), TRUNCATE_LEN), width=width))
    elif judge_data.get('judgment_raw'):
        # Fall back to raw judgment if parsed not available
        print("\n   Raw Judgment:")
        print(wrap_text(truncate_if_long(str(judge_data['judgment_raw']), TRUNCATE_LEN), width=width))


def display_summary(samples: List[Dict[str, Any]]):
    """Display summary statistics."""
    if not samples:
        return

    total = len(samples)

    print("=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)
    print(f"Total Samples:       {total}")

    # Determine format type
    if samples and is_multiple_choice_logprob(samples[0]):
        print(f"Format Type:         Multiple-choice with log probabilities")
    else:
        print(f"Format Type:         Generic/Other")

    # Collect all metric names from the 'metrics' field across all samples
    metric_fields = set()
    for sample in samples:
        sample_metrics = sample.get('metrics', [])
        if isinstance(sample_metrics, list):
            metric_fields.update(sample_metrics)

    # Calculate statistics for numeric metrics
    print("\n📊 AGGREGATE METRICS:")
    for metric in sorted(metric_fields):
        values = []
        for sample in samples:
            if metric in sample:
                value = sample[metric]
                # Handle different value types
                if isinstance(value, (int, float)):
                    values.append(float(value))
                elif isinstance(value, list) and len(value) > 0:
                    # For list values, use first element
                    try:
                        values.append(float(value[0]))
                    except (ValueError, TypeError, IndexError):
                        pass

        if values:
            avg = sum(values) / len(values)
            # Count how many were 1.0 (for accuracy-like metrics)
            correct_count = sum(1 for v in values if v == 1.0)

            if correct_count > 0 and correct_count <= len(values):
                # Likely an accuracy metric
                print(f"   {metric:25} avg: {avg:.4f}  ({correct_count}/{len(values)} = {100*correct_count/len(values):.1f}%)")
            else:
                print(f"   {metric:25} avg: {avg:.4f}  (n={len(values)})")

    print("=" * 100)


def parse_inputs():
    parser = argparse.ArgumentParser(
        description="Display lm-evaluation-harness sample results in a human-readable format."
    )
    parser.add_argument("jsonl_file", help="Path to a samples_*.jsonl file")
    parser.add_argument(
        "--no-pager",
        action="store_true",
        help="Do not pause for interactive input between samples.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=95,
        help="Width for text wrapping (default: 95)",
    )
    parser.add_argument(
        "--sample-ids",
        type=str,
        help="Comma-separated list of sample IDs to display (e.g., '0,5,10')",
    )
    return parser.parse_args()

def examine_outputs(file_path, no_pager=False, width=95, sample_ids=None):

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"\n📂 Loading results from: {file_path}\n")

    samples = parse_jsonl_file(file_path)

    # Filter samples by IDs if specified
    if sample_ids:
        try:
            ids_to_display = [int(x.strip()) for x in sample_ids.split(',')]
            samples = [s for s in samples if s.get('doc_id') in ids_to_display]
            print(f"Filtering to {len(samples)} samples with IDs: {ids_to_display}\n")
        except ValueError:
            print(f"Warning: Could not parse sample IDs '{sample_ids}', displaying all samples\n")

    # Try to find and load accompanying judge file(s)
    # Extract datetime and task from samples filename
    # Pattern: samples_{task}_{datetime}.jsonl
    # Judge pattern: llm_judge_{task}_{judge_name}_{datetime}.jsonl
    file_name = Path(file_path).name
    judge_lookup = {}  # Maps idx -> list of (judge_name, judge_data)

    if file_name.startswith('samples_'):
        # Extract the datetime part (last part before .jsonl with 'T' in it)
        parts = file_name.replace('samples_', '').replace('.jsonl', '').split('_')
        # Find datetime pattern (must contain 'T' for timestamp)
        datetime_parts = [p for p in parts if 'T' in p]
        if datetime_parts:
            # Should be just one part with the datetime
            datetime_str = datetime_parts[-1]  # Take the last one if multiple
            # Extract task name (everything before datetime)
            task_name = '_'.join([p for p in parts if 'T' not in p])

            # Build pattern to find matching judge files
            dir_path = Path(file_path).parent
            judge_pattern = str(dir_path / f"llm_judge_*{datetime_str}.jsonl")
            judge_files = glob.glob(judge_pattern)

            for judge_file in judge_files:
                print(f"📂 Loading judge results from: {judge_file}\n")

                # Extract judge name from filename
                # Pattern: llm_judge_{task}_{judge_name}_{datetime}.jsonl
                judge_file_name = Path(judge_file).name
                judge_file_parts = judge_file_name.replace('llm_judge_', '').replace('.jsonl', '')
                # Remove task name and datetime to get judge name
                judge_name_full = judge_file_parts.replace(task_name + '_', '').replace('_' + datetime_str, '')

                judge_samples = parse_jsonl_file(judge_file)
                # Create lookup dictionary by idx, storing list of judges
                for judge in judge_samples:
                    if 'idx' in judge:
                        idx = judge['idx']
                        if idx not in judge_lookup:
                            judge_lookup[idx] = []
                        judge_lookup[idx].append((judge_name_full, judge))

    if not samples:
        print("Error: No samples found in file")
        sys.exit(1)

    total_samples = len(samples)
    print(f"Total samples: {total_samples}\n")
    if judge_lookup:
        print(f"Total judge evaluations: {len(judge_lookup)}\n")

    # Display each sample
    for i, sample in enumerate(samples, 1):
        # Get corresponding judge data by doc_id (which should match idx)
        doc_id = sample.get('doc_id')
        judge_data_list = judge_lookup.get(doc_id) if doc_id is not None else None

        display_sample(sample, i, total_samples, judge_data_list, width=width)

        # Optional: pause after each sample for large files
        if not no_pager and total_samples > 10 and i < total_samples:
            response = input("Press Enter to continue to next sample (or 'q' to skip to summary): ")
            if response.lower() == 'q':
                print("\nSkipping to summary...\n")
                break

    # Display summary
    display_summary(samples)

def main():
    args = parse_inputs()
    examine_outputs(
        args.jsonl_file,
        no_pager=args.no_pager,
        width=args.width,
        sample_ids=args.sample_ids
    )
    

if __name__ == "__main__":
    main()
