#!/usr/bin/env python3
"""
AI Fingerprint - Streamlined utility for AI system analysis

A single script that does everything the ai-fingerprint skill needs:
- Quick file scanning for AI-related files
- Strand fingerprint generation
- JSON manipulation

Usage:
    ai_fingerprint.py scan <dir> [--output <file>]
    ai_fingerprint.py strand <system_analysis.json>
    ai_fingerprint.py embed <system_analysis.json>
    ai_fingerprint.py cheatsheet
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


# ============================================================================
# FILE SCANNER
# ============================================================================

AI_KEYWORDS = [
    'llm', 'openai', 'anthropic', 'claude', 'gpt', 'prompt', 'agent',
    'langchain', 'langgraph', 'embedding', 'vector', 'rag', 'retrieval',
    'pinecone', 'chroma', 'faiss', 'ollama', 'huggingface', 'transformers'
]

CODE_EXTS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java', '.rb', '.rs'}
CONFIG_EXTS = {'.json', '.yaml', '.yml', '.toml', '.env', '.config'}
SKIP_DIRS = {'node_modules', '__pycache__', '.git', '.venv', 'venv', 'dist', 'build'}


def scan_for_ai_files(target_dir: str, max_files: int = 5000) -> Dict:
    """Quick scan for AI-related files."""
    target_path = Path(target_dir).resolve()
    ai_files = []
    config_files = []
    entry_files = []

    file_count = 0

    for root, dirs, filenames in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in filenames:
            if file_count >= max_files:
                break

            file_path = Path(root) / filename
            ext = file_path.suffix.lower()
            name_lower = filename.lower()

            try:
                stat = file_path.stat()

                file_info = {
                    'path': str(file_path.relative_to(target_path)),
                    'name': filename,
                    'size': stat.st_size
                }

                # Categorize files
                is_ai = any(kw in name_lower or kw in str(file_path).lower()
                           for kw in AI_KEYWORDS)
                is_config = ext in CONFIG_EXTS
                is_entry = name_lower in {'main.py', 'app.py', 'index.js', 'server.py',
                                         'main.go', 'index.ts', '__init__.py'}

                if is_ai:
                    ai_files.append(file_info)
                elif is_config:
                    config_files.append(file_info)
                elif is_entry:
                    entry_files.append(file_info)

                file_count += 1

            except (PermissionError, OSError):
                continue

        if file_count >= max_files:
            break

    return {
        'target': str(target_path),
        'scanned_files': file_count,
        'ai_related_files': ai_files,
        'config_files': config_files,
        'entry_files': entry_files,
        'summary': {
            'ai_files': len(ai_files),
            'configs': len(config_files),
            'entries': len(entry_files)
        }
    }


# ============================================================================
# STRAND GENERATOR
# ============================================================================

def show_cheatsheet():
    """Display strand encoding reference."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                     AI FINGERPRINT STRAND ENCODING                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ Format: LLM(6) - AGENTIC(8) - RAG(7)                                      ║
║ Example: A1ITMX-S1N4NNED-NXNNXNN                                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ LLM Component (6 positions)                                               ║
║ ──────────────────────────────────────────────────────────────────────────║
║ 1. Provider:    A=API | L=Local | H=Hybrid | X=Unknown                   ║
║ 2. Diversity:   1-9=count | M=Many(10+) | X=Unknown                      ║
║ 3. Activity:    I=Inference | F=Finetune | T=Training | X=Unknown        ║
║ 4. Input:       T=Text | M=Multimodal | X=Unknown                        ║
║ 5. Output:      T=Text | S=Structured | C=Code | M=Mixed | X=Unknown     ║
║ 6. Streaming:   Y=Yes | N=No | X=Unknown                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ AGENTIC Component (8 positions)                                           ║
║ ──────────────────────────────────────────────────────────────────────────║
║ 1. Topology:    S=Single | M=Multi | H=Hierarchical | X=Hybrid           ║
║ 2. Count:       1-9=count | *=10+ | X=Unknown                            ║
║ 3. Autonomy:    F=Full | S=Semi | N=None | X=Unknown                     ║
║ 4. Tools:       N=None | 1-9=count | *=10+ | X=Unknown                   ║
║ 5. Sandbox:     N=None | P=Process | C=Container | X=Unknown             ║
║ 6. Human Gates: N=None | O=Optional | R=Required | M=Multi-tier          ║
║ 7. Memory:      E=Ephemeral | S=Session | P=Persistent | F=Filesystem    ║
║ 8. Protocol:    D=Direct | M=MCP | A=A2A | C=Custom | N=None             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ RAG Component (7 positions)                                               ║
║ ──────────────────────────────────────────────────────────────────────────║
║ 1. Pattern:     N=None | B=Basic | A=Advanced | G=Agentic | M=Multimodal ║
║ 2. Retrieval:   D=Dense | S=Sparse | H=Hybrid | T=Tool | N=None          ║
║ 3. Corpus:      D=Docs | T=Tools | X=Mixed | O=Domain | N=None           ║
║ 4. Updates:     S=Static | I=Incremental | R=Realtime | N=None           ║
║ 5. Sources:     1-9=count | M=Many(10+) | N=None                         ║
║ 6. Citations:   Y=Yes | N=No                                             ║
║ 7. Vector DB:   N=None | C=Chroma | M=Milvus | P=Postgres | F=FAISS |    ║
║                 O=Other | X=Unknown                                       ║
╚═══════════════════════════════════════════════════════════════════════════╝
""")


def encode_llm(data: Dict) -> str:
    """Encode LLM component (6 chars)."""
    llm = data.get("llm_analysis", {})

    # 1. Provider deployment
    api_or_local = llm.get("inference_details", {}).get("api_or_local", "").lower()
    p1 = ("H" if "hybrid" in api_or_local or "both" in api_or_local else
          "A" if "api" in api_or_local else
          "L" if "local" in api_or_local else "X")

    # 2. Provider diversity
    models = llm.get("inference_details", {}).get("models_used", [])
    count = len(models) if models else 1
    p2 = "M" if count >= 10 else str(min(count, 9))

    # 3. Activity type
    p3 = ("T" if llm.get("is_training_llm") else
          "F" if llm.get("is_finetuning_llm") else
          "I" if llm.get("is_using_llm_inference") else "X")

    # 4. Input modality
    input_mod = llm.get("input_modality", [])
    p4 = ("M" if len(input_mod) > 1 else
          "T" if any("text" in str(m).lower() for m in input_mod) else "X")

    # 5. Output modality
    output_mod = llm.get("output_modality", [])
    p5 = ("M" if len(output_mod) > 2 else
          "S" if any("structured" in str(m).lower() for m in output_mod) else
          "C" if any("code" in str(m).lower() for m in output_mod) else
          "T" if any("text" in str(m).lower() for m in output_mod) else "X")

    # 6. Streaming
    streaming = data.get("agentic_analysis", {}).get("interface", {}).get("streaming_support")
    p6 = "Y" if streaming else "N" if streaming is False else "X"

    return f"{p1}{p2}{p3}{p4}{p5}{p6}"


def encode_agentic(data: Dict) -> str:
    """Encode Agentic component (8 chars)."""
    agentic = data.get("agentic_analysis", {})

    # 1. Topology
    topology = agentic.get("structural", {}).get("topology", "").lower()
    p1 = ("H" if "hierarchical" in topology else
          "M" if "multi" in topology else
          "S" if "single" in topology else "X")

    # 2. Agent count
    agent_count = str(agentic.get("structural", {}).get("effective_agent_count", "1"))
    if "dynamic" in agent_count.lower() or "-" in agent_count:
        p2 = "*"
    else:
        try:
            count = int(agent_count)
            p2 = "*" if count >= 10 else str(count)
        except ValueError:
            p2 = "1"

    # 3. Autonomy
    autonomy = agentic.get("control", {}).get("autonomy_level", "").lower()
    p3 = ("F" if "full" in autonomy else
          "S" if "semi" in autonomy else
          "N" if "none" in autonomy or "minimal" in autonomy else "X")

    # 4. Tools
    tools = agentic.get("capabilities", {}).get("tool_categories", [])
    tool_count = len(tools) if tools else 0
    p4 = "N" if tool_count == 0 else ("*" if tool_count >= 10 else str(tool_count))

    # 5. Sandboxing
    sandbox = agentic.get("capabilities", {}).get("sandboxing", "").lower()
    p5 = ("C" if "container" in sandbox or "docker" in sandbox else
          "P" if "process" in sandbox else "N")

    # 6. Human gates
    gates = agentic.get("control", {}).get("human_gates", [])
    if not gates or "none" in str(gates).lower():
        p6 = "N"
    elif any("multi" in str(g).lower() for g in gates):
        p6 = "M"
    elif any("required" in str(g).lower() for g in gates):
        p6 = "R"
    else:
        p6 = "O"

    # 7. Memory
    memory = agentic.get("memory", {}).get("long_term", "").lower()
    p7 = ("F" if "file" in memory else
          "P" if "persistent" in memory or "vector" in memory else
          "S" if "session" in memory else "E")

    # 8. Protocol
    comm = agentic.get("communication_protocols", {})
    mcp = comm.get("mcp_support", "").lower()
    p8 = ("M" if "full" in mcp or mcp == "yes" else
          "A" if comm.get("a2a_support", "").lower() == "yes" else
          "C" if "custom" in comm.get("primary_protocol", "").lower() else "D")

    return f"{p1}{p2}{p3}{p4}{p5}{p6}{p7}{p8}"


def encode_rag(data: Dict) -> str:
    """Encode RAG component (7 chars)."""
    rag = data.get("rag_analysis", {})

    # 1. RAG pattern
    pattern = rag.get("architecture_classification", {}).get("core_pattern", "").lower()
    p1 = ("N" if "not a rag" in pattern or "none" in pattern else
          "M" if "multimodal" in pattern else
          "G" if "agentic" in pattern else
          "A" if "advanced" in pattern else
          "B" if "basic" in pattern else "N")

    # 2. Retrieval strategy
    retrieval = rag.get("architecture_classification", {}).get("retrieval_strategy", {})
    primary = retrieval.get("primary", "").lower()
    p2 = ("H" if "hybrid" in primary else
          "D" if "dense" in primary else
          "S" if "sparse" in primary else
          "T" if "tool" in primary else "N")

    # 3. Corpus type
    sources = rag.get("document_processing", {}).get("ingestion", {}).get("data_sources", [])
    has_docs = any("document" in str(s).lower() or "pdf" in str(s).lower() for s in sources)
    has_tools = any("tool" in str(s).lower() for s in sources)
    p3 = ("X" if has_docs and has_tools else
          "T" if has_tools else
          "D" if has_docs else
          "N" if not sources else "O")

    # 4. Update strategy
    update = rag.get("architecture_classification", {}).get("indexing", {}).get("update_strategy", "").lower()
    p4 = ("R" if "real" in update else
          "I" if "incremental" in update else
          "S" if "static" in update or "batch" in update else "N")

    # 5. Source diversity
    p5 = "N" if not sources else ("M" if len(sources) >= 10 else str(len(sources)))

    # 6. Citations
    citation = rag.get("generation_pipeline", {}).get("output_enhancement", {}).get("citation_generation", False)
    p6 = "Y" if citation else "N"

    # 7. Vector DB
    vdb = rag.get("data_flow_architecture", {}).get("component_dependencies", {}).get("vector_database", "").lower()
    p7 = ("N" if not vdb or "none" in vdb or "n/a" in vdb else
          "C" if "chroma" in vdb else
          "M" if "milvus" in vdb else
          "P" if "postgres" in vdb else
          "F" if "faiss" in vdb else
          "O" if vdb else "X")

    return f"{p1}{p2}{p3}{p4}{p5}{p6}{p7}"


def generate_strand(data: Dict) -> str:
    """Generate complete strand fingerprint."""
    llm = encode_llm(data)
    agentic = encode_agentic(data)
    rag = encode_rag(data)
    return f"{llm}-{agentic}-{rag}"


# ============================================================================
# MAIN CLI
# ============================================================================

def cmd_scan(args):
    """Scan directory for AI-related files."""
    if len(args) < 1:
        print("Usage: ai_fingerprint.py scan <directory> [--output <file>]", file=sys.stderr)
        sys.exit(1)

    target_dir = args[0]
    output_file = args[args.index("--output") + 1] if "--output" in args else None

    if not os.path.isdir(target_dir):
        print(f"Error: Directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {target_dir} for AI-related files...", file=sys.stderr)
    results = scan_for_ai_files(target_dir)

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results written to: {output_file}", file=sys.stderr)
    else:
        print(json.dumps(results, indent=2))


def cmd_strand(args):
    """Generate strand from system_analysis.json."""
    if len(args) < 1:
        print("Usage: ai_fingerprint.py strand <system_analysis.json>", file=sys.stderr)
        sys.exit(1)

    json_file = args[0]

    if not os.path.exists(json_file):
        print(f"Error: File not found: {json_file}", file=sys.stderr)
        sys.exit(1)

    with open(json_file, 'r') as f:
        data = json.load(f)

    strand = generate_strand(data)

    system_name = Path(data.get("analysis_metadata", {}).get("codebase_path", json_file)).name

    print(f"\nSystem: {system_name}")
    print(f"Strand: {strand}\n")


def cmd_embed(args):
    """Generate strand and embed it in system_analysis.json."""
    if len(args) < 1:
        print("Usage: ai_fingerprint.py embed <system_analysis.json>", file=sys.stderr)
        sys.exit(1)

    json_file = args[0]

    if not os.path.exists(json_file):
        print(f"Error: File not found: {json_file}", file=sys.stderr)
        sys.exit(1)

    with open(json_file, 'r') as f:
        data = json.load(f)

    strand = generate_strand(data)
    data['strand'] = strand

    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)

    system_name = Path(data.get("analysis_metadata", {}).get("codebase_path", json_file)).name

    print(f"✓ Strand embedded in {json_file}")
    print(f"  System: {system_name}")
    print(f"  Strand: {strand}")


def main():
    if len(sys.argv) < 2:
        print("""
AI Fingerprint Tool - Streamlined utility for AI system analysis

Commands:
    scan <dir> [--output <file>]     Scan for AI-related files
    strand <system_analysis.json>     Generate strand fingerprint
    embed <system_analysis.json>      Generate and embed strand in JSON
    cheatsheet                        Show strand encoding reference

Examples:
    ai_fingerprint.py scan ./my-app --output scan.json
    ai_fingerprint.py strand system_analysis.json
    ai_fingerprint.py embed system_analysis.json
    ai_fingerprint.py cheatsheet
""")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "scan":
        cmd_scan(args)
    elif command == "strand":
        cmd_strand(args)
    elif command == "embed":
        cmd_embed(args)
    elif command == "cheatsheet":
        show_cheatsheet()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
