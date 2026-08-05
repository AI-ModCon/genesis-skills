"""
Utility functions demonstrating common patterns for answer extraction and processing.
"""

import re
from typing import Dict, Any, List


def get_answer(doc: Dict[str, Any]) -> str:
    """
    Extract the target answer from document.

    For GSM8K, answers are formatted as "#### 42" where 42 is the numeric answer.
    """
    answer = doc["answer"]
    # Extract the number after ####
    match = re.search(r"####\s*(-?\d+(?:,\d+)*(?:\.\d+)?)", answer)
    if match:
        # Remove commas from numbers like "1,000"
        return match.group(1).replace(",", "")
    return answer


def extract_numeric_answer(response: str) -> str:
    """
    Extract numeric answer from free-form model output using regex patterns.

    This function tries multiple common patterns to find numeric answers:
    1. "The answer is X"
    2. "= X"
    3. "Answer: X"
    4. Just a number at the end

    Args:
        response: The model's generated text

    Returns:
        Extracted numeric answer as string, or empty string if not found
    """
    if not response:
        return ""

    # Normalize response
    response = response.strip()

    # Pattern 1: "the answer is X" or "answer is X" (case insensitive)
    match = re.search(r'(?:the\s+)?answer\s+is[:\s]+(-?\d+(?:,\d+)*(?:\.\d+)?)',
                     response, re.IGNORECASE)
    if match:
        return match.group(1).replace(",", "")

    # Pattern 2: "= X" at the end or followed by explanation
    match = re.search(r'=\s*(-?\d+(?:,\d+)*(?:\.\d+)?)', response)
    if match:
        return match.group(1).replace(",", "")

    # Pattern 3: "Answer: X" at start of line
    match = re.search(r'^Answer:\s*(-?\d+(?:,\d+)*(?:\.\d+)?)', response, re.MULTILINE)
    if match:
        return match.group(1).replace(",", "")

    # Pattern 4: Look for the last number in the response
    # (this is a fallback and may not always be correct)
    numbers = re.findall(r'-?\d+(?:,\d+)*(?:\.\d+)?', response)
    if numbers:
        return numbers[-1].replace(",", "")

    # If no pattern matches, return the original response
    return response


def normalize_number(value: str) -> str:
    """
    Normalize numeric strings for comparison.

    - Remove commas: "1,000" → "1000"
    - Remove trailing zeros from decimals: "42.00" → "42"
    - Handle negative signs

    Args:
        value: String representation of a number

    Returns:
        Normalized string
    """
    if not value:
        return value

    # Remove commas
    value = value.replace(",", "")

    try:
        # Try to parse as number and normalize
        if "." in value:
            num = float(value)
            # Remove trailing zeros from decimals
            if num == int(num):
                return str(int(num))
            return str(num)
        else:
            # Integer
            return str(int(value))
    except (ValueError, TypeError):
        # If it's not a valid number, return as-is
        return value


def process_numeric_results(doc: Dict[str, Any], results: List) -> Dict[str, float]:
    """
    Process results for numeric comparison.

    Args:
        doc: The document/question dict
        results: List of filtered model responses

    Returns:
        Dictionary with metric values
    """
    if not results or len(results) == 0:
        return {"exact_match": 0.0}

    # Get the filtered response (after regex extraction and normalization)
    prediction = results[0]

    # Get the target answer
    target = get_answer(doc)

    # Normalize both for comparison
    prediction = normalize_number(str(prediction))
    target = normalize_number(str(target))

    # Compare
    is_correct = prediction == target

    return {"exact_match": 1.0 if is_correct else 0.0}


# ============================================================================
# Additional pattern examples
# ============================================================================

def extract_choice_from_letter(response: str, choices: List[str] = None) -> str:
    """
    Extract answer choice from responses like "The answer is A" or "B)"

    Args:
        response: Model output
        choices: Optional list of choices (e.g., ["A", "B", "C", "D"])

    Returns:
        Extracted letter or full response if not found
    """
    if not response:
        return ""

    # Try to find single capital letter that represents a choice
    match = re.search(r'\b([A-D])\b', response.upper())
    if match:
        return match.group(1)

    # Try to find "(A)" or "A)" format
    match = re.search(r'\(?([A-D])\)', response.upper())
    if match:
        return match.group(1)

    return response


def extract_yes_no(response: str) -> str:
    """
    Extract yes/no answer from free-form text.

    Args:
        response: Model output

    Returns:
        "yes" or "no" if found, otherwise original response
    """
    response_lower = response.lower().strip()

    # Check for explicit yes/no
    if re.search(r'\byes\b', response_lower):
        return "yes"
    if re.search(r'\bno\b', response_lower):
        return "no"

    # Check for affirmative/negative patterns
    if re.search(r'\b(true|correct|affirmative)\b', response_lower):
        return "yes"
    if re.search(r'\b(false|incorrect|negative)\b', response_lower):
        return "no"

    return response


def extract_code_block(response: str, language: str = None) -> str:
    """
    Extract code from markdown code blocks.

    Args:
        response: Model output potentially containing ```python ... ```
        language: Optional language specifier (e.g., "python")

    Returns:
        Extracted code or empty string
    """
    if not response:
        return ""

    # Pattern for ```language\ncode\n```
    if language:
        pattern = f"```{language}\\s*\\n(.*?)```"
    else:
        pattern = r"```(?:\w+)?\s*\n(.*?)```"

    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return response


# ============================================================================
# Dataset preprocessing examples
# ============================================================================

def preprocess_docs(dataset):
    """
    Preprocess the dataset before evaluation.

    Common use cases:
    1. Filter out invalid or problematic samples
    2. Add computed fields
    3. Reformat data structures
    4. Combine multiple fields

    Args:
        dataset: HuggingFace dataset object

    Returns:
        Processed dataset (can be a list of dicts or modified dataset)
    """
    processed = []

    for doc in dataset:
        # Example 1: Filter out samples with missing data
        if not doc.get("question") or not doc.get("correct_answer"):
            continue

        # Example 2: Add computed fields
        # Create indexed choices for multiple choice
        if "distractor1" in doc and "distractor2" in doc and "distractor3" in doc:
            choices = [
                doc["correct_answer"],
                doc["distractor1"],
                doc["distractor2"],
                doc["distractor3"]
            ]
            # Find which index has the correct answer (after potential shuffling)
            answer_idx = 0  # In this case, always first
        else:
            # Assume choices field exists
            choices = doc.get("choices", [])
            answer_idx = doc.get("answer", 0)

        # Example 3: Create new document with standardized fields
        processed_doc = {
            "question": doc["question"],
            "choices": choices,
            "answer_idx": answer_idx,
            "original_doc": doc,  # Keep original for reference
        }

        # Example 4: Filter by length or other criteria
        if len(processed_doc["question"]) < 10:  # Too short
            continue

        processed.append(processed_doc)

    return processed


def shuffle_choices(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shuffle answer choices to avoid position bias.

    This is useful when the correct answer is always in the same position.

    Args:
        doc: Document with 'choices' and 'answer_idx' fields

    Returns:
        Modified document with shuffled choices and updated answer_idx
    """
    import random

    if "choices" not in doc or "answer_idx" not in doc:
        return doc

    choices = doc["choices"]
    correct_answer = choices[doc["answer_idx"]]

    # Create indexed pairs
    indexed_choices = list(enumerate(choices))

    # Shuffle
    random.shuffle(indexed_choices)

    # Extract shuffled choices and find new correct index
    shuffled_choices = [choice for _, choice in indexed_choices]
    new_answer_idx = shuffled_choices.index(correct_answer)

    # Return modified doc
    return {
        **doc,
        "choices": shuffled_choices,
        "answer_idx": new_answer_idx,
    }


def combine_fields(doc: Dict[str, Any], fields: List[str], separator: str = "\n") -> str:
    """
    Combine multiple document fields into a single string.

    Useful for creating context from multiple fields.

    Args:
        doc: Document dictionary
        fields: List of field names to combine
        separator: String to join fields with

    Returns:
        Combined string
    """
    parts = []
    for field in fields:
        if field in doc and doc[field]:
            parts.append(str(doc[field]))
    return separator.join(parts)


def filter_by_length(dataset, field: str, min_length: int = 0, max_length: int = float('inf')):
    """
    Filter dataset by length of a specific field.

    Args:
        dataset: Dataset to filter
        field: Field name to check length
        min_length: Minimum length (inclusive)
        max_length: Maximum length (inclusive)

    Returns:
        Filtered dataset
    """
    filtered = []
    for doc in dataset:
        if field not in doc:
            continue

        length = len(str(doc[field]))
        if min_length <= length <= max_length:
            filtered.append(doc)

    return filtered


# ============================================================================
# Functions for lambda_and_preprocessing.yaml example
# ============================================================================

def format_choices(doc: Dict[str, Any]) -> List[str]:
    """
    Format answer choices with letter labels (A, B, C, D).

    Args:
        doc: Document with 'choices' field

    Returns:
        List of formatted choices
    """
    choices = doc.get('choices', [])
    return [f"{chr(65+i)}) {choice}" for i, choice in enumerate(choices)]


def extract_first_letter(text: str) -> str:
    """
    Extract the first letter from text if it's A, B, C, or D.

    Used as a simple filter for multiple-choice responses.

    Args:
        text: Model output

    Returns:
        First letter if valid choice, empty string otherwise
    """
    if not text:
        return ""
    first_char = text[0].upper()
    return first_char if first_char in 'ABCD' else ""


def process_accuracy(doc: Dict[str, Any], results: List) -> Dict[str, float]:
    """
    Calculate accuracy for multiple-choice task.

    Args:
        doc: Document with 'answer_idx' field
        results: List containing the filtered model response

    Returns:
        Dictionary with 'acc' metric
    """
    if not results:
        return {"acc": 0.0}

    prediction = results[0]
    target = str(doc.get('answer_idx', ''))

    return {"acc": 1.0 if prediction == target else 0.0}
