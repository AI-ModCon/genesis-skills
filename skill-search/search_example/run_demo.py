#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Unified demo for full catalog loading and iterative skill search."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import urlparse, urlunparse

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    from langgraph.graph import END, StateGraph
except ImportError as exc:  # pragma: no cover - helpful runtime guidance
    raise SystemExit(
        "Missing example dependencies. Install them with `pip install -r search_example/requirements.txt`."
    ) from exc

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
SKILL_SEARCH_SCRIPT = WORKSPACE_ROOT / "skill-search" / "scripts" / "skill_search.py"
SKILL_SEARCH_PACKAGE = WORKSPACE_ROOT / "skill-search"
LOCAL_DEFAULT_CENTRAL_ROOT = WORKSPACE_ROOT / "skills"
DEFAULT_MODEL_ENDPOINT = "http://localhost:1234/v1"
DEFAULT_MODEL_NAME = "llama-3.2-1b-mlx"

# Make the skill_search package importable so we can reuse load_skill_body.
if str(SKILL_SEARCH_PACKAGE) not in sys.path:
    sys.path.insert(0, str(SKILL_SEARCH_PACKAGE))

from skill_search import load_skill_body  # noqa: E402
DEFAULT_TASKS = (
    "search scientific literature and organize bibliography citations",
    "draft a Slurm script for a four-GPU job",
    "validate Croissant metadata for an ML dataset",
)


class GraphState(TypedDict, total=False):
    task: str
    model_endpoint: str
    base_url: str
    model_name: str
    api_key: str
    use_llm: bool
    central_root: str
    my_skills_paths: list[str]
    search_top_k: int
    discovery_query: str
    discovery_reason: str
    discovery_tool_output: str
    skill_matches: list[dict[str, Any]]
    selected_skill: dict[str, Any]
    selected_skill_reason: str
    selected_skill_body_preview: str
    llm_raw_response: str
    instruction_status: str


def normalize_endpoint(endpoint: str, fallback_model: str) -> tuple[str, str]:
    """Allow either base URL or /v1/<model> URL forms."""

    parsed = urlparse(endpoint)
    path = parsed.path.rstrip("/")

    model_name = fallback_model
    base_path = path

    if "/v1/" in path:
        prefix, _, suffix = path.partition("/v1/")
        base_path = f"{prefix}/v1" if prefix else "/v1"
        if suffix.strip("/"):
            model_name = suffix.strip("/")
    elif path in ("", "/"):
        base_path = "/v1"
    elif path == "/v1":
        base_path = "/v1"

    base_url = urlunparse(
        parsed._replace(path=base_path, params="", query="", fragment="")
    ).rstrip("/")
    return base_url, model_name


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract a JSON object from model output."""

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate JSON object in model response.")
    return json.loads(candidate[start : end + 1])


def clamp_top_k(value: Any, *, default: int, max_value: int) -> int:
    """Clamp search result counts to the configured search limit."""

    try:
        top_k = int(value)
    except (TypeError, ValueError):
        top_k = default
    return max(1, min(top_k, max_value))


def parse_discovery_plan(
    raw_text: str, *, default_top_k: int, max_value: int
) -> tuple[str, str, int]:
    """Parse a structured discovery plan from model output."""

    parsed = extract_json_object(raw_text)
    query = str(parsed.get("query", "")).strip()
    if not query:
        raise ValueError("Discovery plan did not include a query.")

    reason = str(parsed.get("reason", "")).strip() or "Model returned a structured query."
    top_k = clamp_top_k(
        parsed.get("top_k", default_top_k),
        default=default_top_k,
        max_value=max_value,
    )
    return query, reason, top_k


def plan_discovery_query(
    llm: ChatOpenAI, task: str, *, default_top_k: int, max_value: int
) -> tuple[str, str, int, str]:
    """Ask the model for a structured discovery query when tool calls are absent."""

    messages = [
        SystemMessage(
            content=(
                "Rewrite the user task into a concise search query for a skill catalog. "
                "Return strict JSON only with keys: query, reason, top_k. "
                "The query should focus on the capability being requested, not on conversational filler. "
                f"Choose a top_k between 1 and {max_value}."
            )
        ),
        HumanMessage(content=f"Task:\n{task}\n\nRespond as JSON only."),
    ]
    response = llm.invoke(messages).content
    raw_text = response if isinstance(response, str) else str(response)
    query, reason, top_k = parse_discovery_plan(
        raw_text,
        default_top_k=default_top_k,
        max_value=max_value,
    )
    return query, reason, top_k, raw_text


def invoke_skill_search(
    *,
    central_root: Path,
    my_skills_paths: list[Path],
    load_all: bool = False,
    include_prompt: bool = False,
    query: str | None = None,
    top_k: int = 5,
    min_score: int = 1,
) -> dict[str, Any]:
    """Invoke the path-based skill_search script and parse its JSON output.

    This demo uses subprocess invocation to demonstrate the DOE deployment
    pattern. For agents that can import the skill_search package directly::

        from skill_search import search_payload, load_all_payload
        payload = search_payload(
            "validate Croissant metadata for an ML dataset",
            central_root="/path/to/skills",
        )

    See the skill_search package README for the full Python API.
    """

    command = [
        sys.executable,
        str(SKILL_SEARCH_SCRIPT),
        "--central-root",
        str(central_root.resolve()),
    ]
    for path in my_skills_paths:
        command.extend(["--my-skills-path", str(path.resolve())])

    if load_all:
        command.append("--load-all")
        if include_prompt:
            command.append("--include-prompt")
    else:
        if not query:
            raise ValueError("search mode requires a query")
        command.extend(
            [
                "--query",
                query,
                "--top-k",
                str(top_k),
                "--min-score",
                str(min_score),
            ]
        )

    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def describe_match(match: dict[str, Any]) -> str:
    """Summarize a skill discovery match."""

    matched_terms = ", ".join(match.get("matched_terms", [])) or "none"
    return f"score={match.get('score', 0)}; matched terms: {matched_terms}"


def load_skill_preview(skill_md_path: Path, preview_lines: int = 12) -> str:
    """Load and trim a skill body preview."""

    body = load_skill_body(skill_md_path)
    return "\n".join(body.splitlines()[:preview_lines])


def detect_model_availability(base_url: str, model_name: str, api_key: str) -> bool:
    """Detect whether the configured model endpoint is currently available."""

    try:
        llm = ChatOpenAI(
            base_url=base_url,
            model=model_name,
            api_key=api_key,
            temperature=0,
            timeout=5,
            max_retries=0,
        )
        llm.invoke([HumanMessage(content="Reply with OK only.")])
        return True
    except Exception:
        return False


def search_skills_node(state: GraphState) -> dict[str, Any]:
    """Search the skill catalog, with LLM assistance when available."""

    central_root = Path(state["central_root"])
    my_skills_paths = [Path(path) for path in state.get("my_skills_paths", [])]
    default_top_k = max(1, int(state["search_top_k"]))

    def run_catalog_search(query: str, top_k: int) -> dict[str, Any]:
        bounded_top_k = max(1, min(int(top_k), default_top_k))
        return invoke_skill_search(
            central_root=central_root,
            my_skills_paths=my_skills_paths,
            query=query,
            top_k=bounded_top_k,
        )

    if not state["use_llm"]:
        payload = run_catalog_search(state["task"], default_top_k)
        return {
            "discovery_query": state["task"],
            "discovery_reason": "Model endpoint unavailable, so heuristic search used the task text directly.",
            "discovery_tool_output": json.dumps(payload, indent=2),
            "skill_matches": payload["matches"],
            "llm_raw_response": "heuristic_mode",
        }

    llm = ChatOpenAI(
        base_url=state["base_url"],
        model=state["model_name"],
        api_key=state["api_key"],
        temperature=0,
        timeout=10,
        max_retries=0,
    )

    @tool
    def search_skill_catalog(query: str, top_k: int = 5) -> str:
        """Search the shared skill catalog and return ranked JSON results."""

        return json.dumps(run_catalog_search(query, top_k), indent=2)

    messages = [
        SystemMessage(
            content=(
                "You are a skill discovery assistant. Call the `search_skill_catalog` tool exactly once "
                "to search the shared catalog for the task. Choose a concise search query and a reasonable top_k. "
                "If tool calling is unavailable, return strict JSON only with keys: query, reason, top_k."
            )
        ),
        HumanMessage(content=f"Task:\n{state['task']}\n\nSearch the skill catalog before selecting a skill."),
    ]

    try:
        response = llm.bind_tools([search_skill_catalog]).invoke(messages)
        raw = response.content if isinstance(response.content, str) else str(response.content)
        tool_calls = getattr(response, "tool_calls", None) or []

        if tool_calls:
            first_call = tool_calls[0]
            tool_args = first_call.get("args", {}) or {}
            query = str(tool_args.get("query") or state["task"]).strip()
            top_k = clamp_top_k(
                tool_args.get("top_k", default_top_k),
                default=default_top_k,
                max_value=default_top_k,
            )
            payload = run_catalog_search(query, top_k)
            return {
                "discovery_query": query,
                "discovery_reason": "Model called the search tool.",
                "discovery_tool_output": json.dumps(payload, indent=2),
                "skill_matches": payload["matches"],
                "llm_raw_response": str(raw),
            }

        try:
            query, reason, top_k = parse_discovery_plan(
                raw,
                default_top_k=default_top_k,
                max_value=default_top_k,
            )
            payload = run_catalog_search(query, top_k)
            return {
                "discovery_query": query,
                "discovery_reason": (
                    "Model returned a structured discovery plan without tool calls. "
                    f"{reason}"
                ),
                "discovery_tool_output": json.dumps(payload, indent=2),
                "skill_matches": payload["matches"],
                "llm_raw_response": str(raw),
            }
        except Exception:
            query, reason, top_k, plan_raw = plan_discovery_query(
                llm,
                state["task"],
                default_top_k=default_top_k,
                max_value=default_top_k,
            )

        payload = run_catalog_search(query, top_k)
        return {
            "discovery_query": query,
            "discovery_reason": (
                "Model did not emit a discovery tool call, so a second JSON-only planning step "
                f"produced the search query. {reason}"
            ),
            "discovery_tool_output": json.dumps(payload, indent=2),
            "skill_matches": payload["matches"],
            "llm_raw_response": f"tool_phase: {raw}\nquery_phase: {plan_raw}",
        }
    except Exception as exc:  # noqa: BLE001
        payload = run_catalog_search(state["task"], default_top_k)
        return {
            "discovery_query": state["task"],
            "discovery_reason": (
                f"Model-assisted discovery failed ({exc.__class__.__name__}: {exc}). "
                "Falling back to heuristic search."
            ),
            "discovery_tool_output": json.dumps(payload, indent=2),
            "skill_matches": payload["matches"],
            "llm_raw_response": f"search_error: {exc}",
        }


def select_skill_node(state: GraphState) -> dict[str, Any]:
    """Select one skill from the search matches."""

    matches = state["skill_matches"]
    if not matches:
        return {
            "selected_skill": {},
            "selected_skill_reason": (
                f"No skills matched discovery query `{state['discovery_query']}`."
            ),
        }

    top_match = matches[0]
    if not state["use_llm"]:
        return {
            "selected_skill": top_match,
            "selected_skill_reason": (
                "Heuristic mode selected the top search result. "
                f"{describe_match(top_match)}."
            ),
        }

    candidate_lookup = {match["name"]: match for match in matches}
    candidate_block = "\n".join(
        f"- {match['name']}: {match['description']} ({describe_match(match)})"
        for match in matches
    )

    llm = ChatOpenAI(
        base_url=state["base_url"],
        model=state["model_name"],
        api_key=state["api_key"],
        temperature=0,
        timeout=10,
        max_retries=0,
    )
    messages = [
        SystemMessage(
            content=(
                "You are a skill router. Choose exactly one skill from the provided candidates. "
                "Return strict JSON only with keys: skill_name, reason."
            )
        ),
        HumanMessage(
            content=(
                f"Task:\n{state['task']}\n\n"
                f"Discovery query:\n{state['discovery_query']}\n\n"
                f"Skill candidates:\n{candidate_block}\n\n"
                "Respond as JSON only."
            )
        ),
    ]

    try:
        raw = llm.invoke(messages).content
        parsed = extract_json_object(raw if isinstance(raw, str) else str(raw))
        selected_name = str(parsed.get("skill_name", "")).strip()
        reason = str(parsed.get("reason", "Model-selected skill.")).strip()

        if selected_name not in candidate_lookup:
            return {
                "selected_skill": top_match,
                "selected_skill_reason": (
                    "Model response did not match a discovered skill. "
                    f"Fallback used the top search result. {describe_match(top_match)}."
                ),
                "llm_raw_response": str(raw),
            }

        selected_match = candidate_lookup[selected_name]
        return {
            "selected_skill": selected_match,
            "selected_skill_reason": f"{reason} {describe_match(selected_match)}.",
            "llm_raw_response": str(raw),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "selected_skill": top_match,
            "selected_skill_reason": (
                f"Model selection failed ({exc.__class__.__name__}: {exc}). "
                f"Fallback used the top search result. {describe_match(top_match)}."
            ),
            "llm_raw_response": f"selection_error: {exc}",
        }


def load_instructions_node(state: GraphState) -> dict[str, Any]:
    """Load the selected skill's instructions."""

    selected_skill = state["selected_skill"]
    if not selected_skill:
        return {
            "selected_skill_body_preview": "No skill body loaded.",
            "instruction_status": "No instructions loaded because no skill was selected.",
        }

    skill_md_path = Path(selected_skill["skill_md_path"]).resolve()
    preview = load_skill_preview(skill_md_path)

    return {
        "selected_skill_body_preview": preview,
        "instruction_status": (
            "Loaded skill instructions; the discovery demo does not execute "
            "skill-specific actions."
        ),
    }


def build_graph():
    """Build the iterative search graph."""

    graph = StateGraph(GraphState)
    graph.add_node("search_skills", search_skills_node)
    graph.add_node("select_skill", select_skill_node)
    graph.add_node("load_instructions", load_instructions_node)
    graph.set_entry_point("search_skills")
    graph.add_edge("search_skills", "select_skill")
    graph.add_edge("select_skill", "load_instructions")
    graph.add_edge("load_instructions", END)
    return graph.compile()


def print_full_catalog(payload: dict[str, Any]) -> None:
    """Print the full catalog sub-run."""

    print("=== Full Catalog Load ===")
    print(f"Catalog roots: {', '.join(payload['catalog_roots'])}")
    print(f"Discovered skills: {payload['count']}")
    for skill in payload["skills"]:
        print(f"- {skill['name']}: {skill['description']}")
        print(f"  Path: {skill['skill_md_path']}")
    print()


def print_task_result(index: int, task: str, final_state: GraphState) -> None:
    """Print one iterative discovery result."""

    print(f"--- Request {index}: {task}")
    print(f"Discovery query: {final_state['discovery_query']}")
    print(f"Discovery reason: {final_state['discovery_reason']}")

    matches = final_state.get("skill_matches", [])
    if matches:
        print("Top matches:")
        for match in matches:
            print(f"- {match['name']}: {describe_match(match)}")
    else:
        print("Top matches: none")

    selected_skill = final_state.get("selected_skill", {})
    if selected_skill:
        print(f"Selected skill: {selected_skill['name']}")
        print(f"Selected path: {selected_skill['skill_md_path']}")
        print(f"Selection reason: {final_state['selected_skill_reason']}")
        print("Instruction preview:")
        print(final_state["selected_skill_body_preview"] or "(empty)")
    else:
        print("Selected skill: none")
        print(f"Selection reason: {final_state['selected_skill_reason']}")

    print(f"Instruction status: {final_state['instruction_status']}")
    print()


def build_parser() -> argparse.ArgumentParser:
    """Build the example CLI parser."""

    parser = argparse.ArgumentParser(
        description="Unified demo for full skill loading and iterative skill search."
    )
    parser.add_argument(
        "--model-endpoint",
        default=DEFAULT_MODEL_ENDPOINT,
        help="OpenAI-compatible model endpoint. Supports base form or /v1/<model> form.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", "local"),
        help="API key for the model endpoint (default: OPENAI_API_KEY or 'local').",
    )
    parser.add_argument(
        "--central-root",
        type=Path,
        default=LOCAL_DEFAULT_CENTRAL_ROOT,
        help="Central skills root used by the example (default: <repository>/skills).",
    )
    parser.add_argument(
        "--my-skills-path",
        type=Path,
        action="append",
        default=[],
        help="Optional user-managed skills root. Repeat to add multiple roots.",
    )
    parser.add_argument(
        "--search-top-k",
        type=int,
        default=5,
        help="Maximum number of candidate skills to keep per iterative search.",
    )
    parser.add_argument(
        "--sample-task",
        action="append",
        default=[],
        help="Override the built-in demo tasks. Repeat to add multiple tasks.",
    )
    return parser


def main() -> None:
    """Run both the full-load and iterative discovery demos."""

    args = build_parser().parse_args()

    full_payload = invoke_skill_search(
        central_root=args.central_root,
        my_skills_paths=args.my_skills_path,
        load_all=True,
        include_prompt=True,
    )
    print_full_catalog(full_payload)

    print("=== Iterative Discovery ===")
    base_url, model_name = normalize_endpoint(args.model_endpoint, DEFAULT_MODEL_NAME)
    use_llm = detect_model_availability(base_url, model_name, args.api_key)
    if use_llm:
        print(f"Model endpoint available: {args.model_endpoint}")
    else:
        print(
            "Model endpoint unavailable; the iterative sub-run will fall back to heuristic search and selection."
        )
    print()

    app = build_graph()
    tasks = args.sample_task or list(DEFAULT_TASKS)
    for index, task in enumerate(tasks, start=1):
        final_state = app.invoke(
            {
                "task": task,
                "model_endpoint": args.model_endpoint,
                "base_url": base_url,
                "model_name": model_name,
                "api_key": args.api_key,
                "use_llm": use_llm,
                "central_root": str(args.central_root.resolve()),
                "my_skills_paths": [str(path.resolve()) for path in args.my_skills_path],
                "search_top_k": max(1, args.search_top_k),
            }
        )
        print_task_result(index, task, final_state)


if __name__ == "__main__":
    main()
