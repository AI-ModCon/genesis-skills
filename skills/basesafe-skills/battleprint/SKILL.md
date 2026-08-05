---
name: battleprint
description: Perform red and blue team adversarial analysis on AI systems. Use after ai-fingerprint to identify attack vectors and defense strategies for LLM/RAG/Agentic systems.
disable-model-invocation: true
user-invocable: true
allowed-tools: Bash(python *), Bash(cat *), Bash(cd *), Bash(python3 *), Read, Write, Agent
requires: ai-fingerprint
---

# Battleprint - Agentic Execution of Red and Blue Team Security Analysis

You are executing the **Battleprint** skill. This performs a red and blue team adversarial analysis sequence.

## Architecture Overview

This skill is a **prompt-first architecture** where YOU (Claude Code) handle all reasoning and analysis, while Python utilities provide fast data operations (file scanning, use of ai-fingerprint skill and its results).

## Your Task

Execute a 4-stage analysis process that produces:
1. **Red Stage 1**: Complete red team analysis of the target code base
2. **Blue Stage 1**: Complete blue team analysis of the target code base
3. **Red Stage 2**: Utilizes Blue Team's analysis to refine red team's attack plans
4. **Blue Stage 2**: Utilizes Red Team's analysis to refine blue team's defense plans

## Arguments

User provides: `$ARGUMENTS`

Expected format: `<target_dir>`

Examples:
- `/battleprint ./my-app` — analyze my-app directory
- `/battleprint /bob/fish` — analyze absolute path

## Required Skills                                        
  - `ai-fingerprint`: Generates file_scan.json and system_analysis.json                                                         
    - Invoke as: `/ai-fingerprint <target_dir>`
    - Or via Skill tool: `skill="ai-fingerprint", args="<target_dir>"`                                                          
    - Output location: `<parent>/ai_fingerprint_results/<target_name>/`  

## Execution Steps

### EXECUTION GUIDE - APPLIES TO ALL PHASES AND STEPS
**When executing bash or unix (e.g. ls, wc, cd, etc.) commands, never ever string them together into a single command.**
 - Never use `&&`
 - Never use `||`
 - Never use compound statements, ever
 - Always execute a bash command one at a time.
 - Always execute a unix command one-at-a-time, never compound them.

**When generating JSON, never ever output it directly. Always write python code that generates the json**
 - Never generate JSON directly, it's too difficult.
 - Always write the python code that generates the JSON.
 - Always use python code generator to generate JSON.
 - Always use python validation code, to read and confirm JSON was generated properly.
 - Take your time. Generate Python to output JSON. Generate Python to Validate JSON. 

### Phase 0: Setup and Check for AI-FingerPrint

```
User provided: $ARGUMENTS
```

**Parse and set paths:**
```bash
# Get absolute path of target
TARGET_DIR=$(cd "$ARGUMENTS" && pwd)
TARGET_BASE=$(dirname "$TARGET_DIR")
TARGET_NAME=$(basename "$TARGET_DIR")

# Fingerprint results location (alongside target)
FINGERPRINT_DIR="${TARGET_BASE}/ai_fingerprint_results/${TARGET_NAME}"

# Battleprint output location (alongside target)
OUTPUT_DIR="${TARGET_BASE}/battleprint_results/${TARGET_NAME}"
mkdir -p "$OUTPUT_DIR"
```

All subsequent references to paths use these variables.

**Verify fingerprint exists:**
1. Check if `$FINGERPRINT_DIR/system_analysis.json` exists
2. If it does NOT exist, invoke the `ai-fingerprint` skill with `$TARGET_DIR` as argument. Use a SEPARATE AGENT (via Agent tool) for this to prevent context bleed.
3. Read `$FINGERPRINT_DIR/file_scan.json` and `$FINGERPRINT_DIR/system_analysis.json` into the current context.

---

### Phase 1: Stage 1 Red and Blue

**Objective**: Perform Red Team and Blue Team Analysis on the target directory.

**Process:**

1. **Read the file scan results:**
```bash
cat "$FINGERPRINT_DIR/file_scan.json"
```

2. **Read the system analysis results:**
```bash
cat "$FINGERPRINT_DIR/system_analysis.json"
```

3. **Parallel Execute 2 Agents**
   
   Use the Agent tool to spawn two agents in parallel. Each Agent invocation is automatically in fresh context.
   
   a. Red Team Agent - use `${CLAUDE_SKILL_DIR}/prompts/red_team_stage1.md` with the fingerprint data
   b. Blue Team Agent - use `${CLAUDE_SKILL_DIR}/prompts/blue_team_stage1.md` with the fingerprint data
   
   Each agent should write its output to:
   - Red: `$OUTPUT_DIR/red_stage_1.json`
   - Blue: `$OUTPUT_DIR/blue_stage_1.json`

4. **Verify Stage 1 Complete**

Use Python's built-in JSON parser to check validity:
```bash
python3 -c "import json; json.load(open('$OUTPUT_DIR/red_stage_1.json'))" && echo "✓ Valid JSON" || echo "✗ Invalid JSON"
```
and 
```bash
python3 -c "import json; json.load(open('$OUTPUT_DIR/blue_stage_1.json'))" && echo "✓ Valid JSON" || echo "✗ Invalid JSON"
```
### Phase 2: Stage 2 Red and Blue

**Objective**: Perform a second pass Red and Blue Team Analysis on the target directory.

**Note:** Each Agent tool invocation automatically runs in fresh context - no special action needed.

**Red Team Agent (Stage 2)**
1. **Read the file scan results:**
```bash
cat "$FINGERPRINT_DIR/file_scan.json"
```

2. **Read the system analysis results:**
```bash
cat "$FINGERPRINT_DIR/system_analysis.json"
```

3. **Read blue team's plans:**
```bash
cat "$OUTPUT_DIR/blue_stage_1.json"
```

4. **Execute Red Team Stage 2**
   
   Use Agent tool with `${CLAUDE_SKILL_DIR}/prompts/red_team_stage2.md` and the above context.
   
   Write output to: `$OUTPUT_DIR/red_stage_2.json`

5. **Verify Stage 2 Complete**
```bash
python3 -c "import json; json.load(open('$OUTPUT_DIR/red_stage_2.json'))" && echo "✓ Valid JSON" || echo "✗ Invalid JSON"
```

**Blue Team Agent (Stage 2)**
1. **Read the file scan results:**
```bash
cat "$FINGERPRINT_DIR/file_scan.json"
```

2. **Read the system analysis results:**
```bash
cat "$FINGERPRINT_DIR/system_analysis.json"
```

3. **Read red team's plans:**
```bash
cat "$OUTPUT_DIR/red_stage_1.json"
```

4. **Execute Blue Team Stage 2**
   
   Use Agent tool with `${CLAUDE_SKILL_DIR}/prompts/blue_team_stage2.md` and the above context.
   
   Write output to: `$OUTPUT_DIR/blue_stage_2.json`

5. **Verify Stage 2 Complete**
```bash
python3 -c "import json; json.load(open('$OUTPUT_DIR/blue_stage_2.json'))" && echo "✓ Valid JSON" || echo "✗ Invalid JSON"
```

### Phase 3: Synthesis

Perform synthesis and provide final results:

1. Output a final_analysis.json with the top 8 exploits found in red_team 2. Did blue_team 2 have an answer for these?
2. Provide an analysis of the efficacy of this battleprint algorithm:
   a. Did the blue team improve from stage 1 to stage 2 (i.e. did it utilize the knowledge it gained by reading red team plans and improve its defenses against these?). If so, how?
   b. Did the red team improve from stage 1 to stage 2? If so, how?
3. Provide final recommendations (top 3) for the engineering team to address. When providing these top 3, be sure to utilize the system analysis to note which AI System and sub-system are most affected.
4. Provide a weakness indicator for each element in the strand. Use relative weakness (i.e. element with the highest relative weakness gets a 10, element with no relative weakness gets a 0).

**All output should be in 2 forms:**
1. JSON file: `$OUTPUT_DIR/final_analysis.json` (enables downstream processing)
2. Markdown file: `$OUTPUT_DIR/final_analysis.md` (allows for easy readability)

**Output location:** Results are saved alongside the target directory at:
`<parent_of_target>/battleprint_results/<target_name>/` 