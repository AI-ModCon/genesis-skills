# AI Fingerprint Skill

**Generate comprehensive AI system fingerprints with architecture analysis and strand encoding**

## What It Does

The `ai-fingerprint` skill performs deep analysis of AI system codebases (LLM, RAG, Agentic applications) and produces:

1. **System Analysis JSON**: Comprehensive architectural analysis with security-relevant details
2. **Strand Fingerprint**: Compact string representation (e.g., `A1ITMX-S1N4NNED-NXNNXNN`)

## Why Use This?

- **Understand AI Systems**: Get a complete picture of how an AI application is architected
- **Security Foundation**: Provides the groundwork for security analysis tools
- **Compact Identification**: Strand fingerprints uniquely characterize systems
- **Reusable Output**: Analysis JSON can be used by multiple downstream tools

## Quick Start

```bash
# Basic usage - analyze an AI codebase
/ai-fingerprint ./path/to/ai-application

# Specify output directory
/ai-fingerprint ./my-app --output-dir ./fingerprints

# Focus on specific AI system type
/ai-fingerprint ./my-app --ai-system-type LLM
```

## What You Get

### System Analysis JSON

Complete architectural breakdown including:
- **AI System Type**: LLM, RAG, Agentic, or Hybrid
- **Architecture Overview**: Components, data flows, trust boundaries
- **LLM Integration**: Providers, prompt construction, response handling
- **RAG Components**: Vector stores, document processing, retrieval
- **Agent Framework**: Tools, autonomy, communication protocols
- **Security Analysis**: Input surfaces, auth/authz, data storage
- **Dependencies**: AI libraries and versions

### Strand Fingerprint

A compact encoding like: `A1ITMX-S1N4NNED-NXNNXNN`

Structure: `LLM(6)-AGENTIC(8)-RAG(7)`

- **LLM (6 chars)**: Provider, diversity, activity type, modalities, streaming
- **AGENTIC (8 chars)**: Topology, count, autonomy, tools, sandboxing, human gates, memory, communication
- **RAG (7 chars)**: Pattern, retrieval strategy, corpus type, updates, diversity, citations, vector DB

## Typical Workflow

```bash
# Step 1: Generate fingerprint
/ai-fingerprint ./my-ai-app

# Step 2: Use in security analysis
/battleprint ./my-ai-app  # Uses existing fingerprint

# Or view the strand cheatsheet
python visualizers/strand.py --cheatsheet
```

## Output Structure

```
ai_fingerprint_results/
└── <target_name>/
    ├── system_analysis.json    # Main output (with strand field)
    ├── file_scan.json          # File inventory
    ├── cwe_context.txt         # CWE reference
    └── strand_output.txt       # Strand generation details
```

## Dependencies

Requires the `battleprint_skill` Python utilities:
- `battleprint.analyzers.file_scanner`
- `battleprint.analyzers.cwe_loader`
- `battleprint.analyzers.json_validator`
- `visualizers/strand.py`

Expected location: `~/battleprint_skill/`

## Strand Cheatsheet

To see the full encoding cheatsheet:

```bash
cd ~/battleprint_skill
python visualizers/strand.py --cheatsheet
```

## Integration with Other Skills

The `ai-fingerprint` skill is designed as a **foundation** for security analysis:

- **battleprint**: Uses system_analysis.json for adversarial red/blue team analysis
- **agent-red-team**: Can leverage architecture insights for agent-specific attacks
- **Custom tools**: Any tool needing AI system understanding

## Examples

### Example 1: Basic LLM Application

```bash
/ai-fingerprint ./simple-chatbot
```

Output:
```
🎯 AI FINGERPRINT COMPLETE

Target: simple-chatbot
System Type: LLM
Strand: A1ITTY-S1N0NNEN-NNNNNNN

LLM Component: A1ITTY
  • Provider: API (OpenAI)
  • Models: 1 (gpt-4)
  • Activity: Inference
  • Input/Output: Text/Text
  • Streaming: Yes

Agentic Component: S1N0NNEN
  • Single agent, no tools, no autonomy

RAG Component: NNNNNNN
  • No RAG system present
```

### Example 2: Complex RAG System

```bash
/ai-fingerprint ./document-qa-system
```

Output:
```
🎯 AI FINGERPRINT COMPLETE

Target: document-qa-system
System Type: RAG
Strand: A2ITMN-S1N2POED-BDDSI1YC

RAG Component: BDDSI1YC
  • Pattern: Basic RAG
  • Retrieval: Dense (embeddings)
  • Corpus: Documents
  • Update: Static
  • Sources: 1
  • Citations: Yes
  • Vector DB: Chroma
```

### Example 3: Agentic System

```bash
/ai-fingerprint ./multi-agent-system
```

Output:
```
🎯 AI FINGERPRINT COMPLETE

Target: multi-agent-system  
System Type: Agentic
Strand: A3IMMY-M4F5CNSP-NNNNNNN

Agentic Component: M4F5CNSP
  • Topology: Multi-agent (flat)
  • Count: 4 agents
  • Autonomy: Fully autonomous
  • Tools: 5 tools available
  • Sandboxing: Container-based
  • Human Gates: None
  • Memory: Session-scoped
  • Communication: Protocol-based
```

## Best Practices

1. **Run on Clean Code**: Works best on organized codebases
2. **Check Dependencies**: Ensure battleprint_skill utilities are available
3. **Review Output**: Validate the system_analysis.json for accuracy
4. **Use Strand**: Reference the cheatsheet to interpret the fingerprint
5. **Save Results**: Keep fingerprints for comparison and tracking

## Troubleshooting

**"File scanner not found"**
- Ensure battleprint_skill is installed at `~/battleprint_skill/`
- Check that Python utilities are accessible

**"Invalid JSON output"**
- The skill will use json_validator to fix issues
- Ensure no markdown code blocks in output

**"Strand generation failed"**
- Verify system_analysis.json is valid JSON
- Check that visualizers/strand.py exists

**"No AI components detected"**
- The codebase might not be an AI system
- Check that AI-related files are present and readable

## Contributing

This skill is part of the AI security analysis toolkit. To enhance:

1. Improve system_analysis.md prompt for better detection
2. Extend strand encoding for new AI patterns
3. Add specialized analysis for emerging AI frameworks

## License

Part of the battleprint security analysis suite.
