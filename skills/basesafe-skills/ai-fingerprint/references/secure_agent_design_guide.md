# Secure Agent System Design Guide

## Introduction

This is a design guide for building agentic AI systems that are secure, flexible, and capable. It synthesizes lessons from analyzing production frameworks, real-world CVEs, and security research into a concrete architectural blueprint.

**The core tension**: Agents are powerful because they can act autonomously, use tools, retrieve information, and coordinate with other agents. Agents are dangerous for exactly the same reasons.

**The design philosophy**: Capability within constraints. We don't prevent agents from being useful—we prevent them from being dangerous. Every security boundary is explicit, every permission is granted, every action is auditable.

This guide presents a security-first architecture proven to address the most critical attack vectors:
- Prompt injection and tool call injection
- State poisoning and memory corruption
- Vector database poisoning and retrieval injection
- Credential accumulation and privilege escalation
- Multi-agent amplification attacks
- Cost bombs and resource exhaustion
- Data exfiltration via tools or retrieval

**Target audience**: Architects and engineers building production agent systems where security, reliability, and auditability matter as much as capability.

---

## The Five Pillars

Every secure agent system is built on five foundational pillars:

1. **Trust Architecture** - Where are the security boundaries? What requires validation?
2. **Agent Topology & Coordination** - How are agents organized? How do they communicate safely?
3. **Execution Model** - What can agents do? What constraints govern their actions?
4. **State & Memory Management** - How is state protected from poisoning?
5. **Observability & Resilience** - How do we monitor and recover safely?

---

## Pillar 1: Trust Architecture

### Zero-Trust Model

**Principle**: Every boundary is a security perimeter. Nothing is trusted by default.

The system has five trust boundaries where validation occurs:

```
User Input → [Validation] → Agent Context
Tool Results → [Validation] → Agent Context  
Retrieval Results → [Validation] → Agent Context
Agent Output → [Validation] → User/Tools
Data Sources → [Validation] → Vector Database
```

Each boundary enforces:
- **Validation**: Is this content safe?
- **Logging**: Record for audit trail
- **Rate limiting**: Prevent abuse
- **Sandboxing**: Isolate execution

### Input Validation

**All external input passes through strict validation before reaching any agent.**

**User Input:**
- Schema validation for structured inputs (not just regex)
- Content-type verification for files
- Size limits enforced at ingestion
- Allowlist approach: reject by default

**Tool Results:**
- Validate return values match expected schema
- Scan for injection patterns (commands disguised as data)
- Size limits per tool output
- Timeout if tool takes too long

**Retrieval Results:**
- Treat retrieved documents as untrusted input
- Content filtering for injection patterns:
  - "Ignore previous instructions"
  - "Your new goal is"
  - Hidden markdown/HTML instructions
- Structural validation (must match expected format)
- Semantic validation (does this answer the query?)
- Source attribution logged

**Critical Rule**: No special treatment for any input source. Retrieved content from your own vector database is just as untrusted as user input from the public internet.

### Permission Model

**Every action requires explicit permission grants.**

**Tool Permissions:**
- Permissions are scoped: read-only vs read-write, specific paths vs filesystem-wide
- Per-invocation permissions (not per-session)
- No inherited or cascading permissions
- Human approval required for state-changing operations outside sandbox

**Retrieval Permissions:**
- Agents have read-only access to vector databases
- Query permissions scoped to specific document collections
- No agent can write to vector database
- Cross-collection queries require elevated permission

**Resource Permissions:**
- Explicit budget for tokens, cost, time
- Explicit limits on iterations, tool calls, retrievals
- Limits enforced at coordinator level, not delegated to agents

### Autonomy Boundaries

**Default autonomy level: Guided (not autonomous).**

**Standard Flow:**
```
Agent proposes action
  ↓
System validates
  ↓
Human approves
  ↓
Execute in sandbox
  ↓
Validate result
  ↓
Return to agent
```

**Multi-Tier Approval:**
- Read-only operations: Limited autonomy (auto-approve with logging)
- Write operations: Require human gate
- Destructive operations: Require elevated approval
- Cross-boundary operations: Require explicit authorization

**Forbidden:**
- "Run until complete" mode without bounds
- Auto-approval based on "trust scores"
- Cascading permissions that expand over time

### Sandboxing: The Non-Negotiable

**All execution happens in containers, not processes.**

**Container Properties:**
- No network access by default
- Read-only filesystem except explicit mount points
- Resource limits: CPU, memory, time
- No access to credentials or API keys
- Ephemeral: destroyed after each invocation

**Tool Execution:**
- Each tool invocation gets fresh container
- Tool results serialized, scanned, validated before returning to agent
- Failed sandbox = failed tool call (fail secure)

**Data Connector Execution:**
- Each connector runs in isolated container
- Network access only to specific data source
- No filesystem access except designated input paths
- Output validated before indexing pipeline

**Why Container-Level:**
- Process-level isolation can be escaped
- Container = stronger boundary
- Network isolation prevents callback attacks
- Resource limits prevent DoS

### Access Control for Knowledge Base

**Vector databases are append-only for agents.**

**Access Model:**
```
┌─────────────────────────────────────┐
│  Vector DB Write Access             │
├─────────────────────────────────────┤
│  ✓ Admin (with approval)            │
│  ✓ Ingestion Pipeline (validated)   │
│  ✗ Agents (READ-ONLY)                │
│  ✗ Tools (no access)                 │
│  ✗ External APIs (no direct access)  │
└─────────────────────────────────────┘
```

**Ingestion Pipeline:**
- All writes go through separate, validated pipeline
- Content scanning before embedding
- Size limits (prevent DoS via massive docs)
- Provenance tracking (who, when, from where)
- Human approval in production

**Why Read-Only Agents:**
- Prevents agents from poisoning their own knowledge base
- Prevents compromised tools from injecting malicious documents
- Prevents attack amplification via self-modification
- Maintains audit trail (only pipeline writes)

### Embedding Validation

**Embeddings are validated before indexing and checked on retrieval.**

**Indexing Pipeline:**
1. Generate embedding from validated text
2. Range validation (embeddings within expected bounds)
3. Similarity sanity check (similar to semantically related text)
4. Anomaly detection (flag outliers from cluster centroids)
5. Store with cryptographic signature and metadata

**Retrieval Validation:**
- Re-generate embedding from stored source text
- Compare to stored embedding (detect tampering)
- If mismatch > threshold, reject and alert

**Metadata Stored:**
```json
{
  "embedding": [...],
  "source_text": "Original text",
  "source_document_id": "doc_123",
  "chunk_id": "chunk_5",
  "indexed_timestamp": "2026-05-21T10:30:00Z",
  "embedding_model": "text-embedding-3-large",
  "signature": "sha256:...",
  "validation_status": "verified"
}
```

### Data Connector Security

**Each connector is an attack surface. 100+ connectors = 100+ risks.**

**Connector Isolation:**
- Sandboxed execution (one container per connector)
- No network except to specific data source
- No filesystem except designated paths
- Output validated before indexing

**Connector Allowlisting:**
- Default: No connectors enabled
- User explicitly enables each connector
- Scoped permissions: "web scraper can access example.com only"
- No wildcard connectors without elevated approval

**Ingestion Rate Limits:**
- Maximum documents per hour
- Maximum storage per data source
- Maximum connectors running concurrently
- Prevents connector abuse as DoS vector

---

## Pillar 2: Agent Topology & Coordination

### Hierarchical Architecture

**The system uses a hierarchical topology with strict communication boundaries.**

```
        ┌─────────────┐
        │ Coordinator │
        └──────┬──────┘
               │
      ┌────────┼────────┐
      │        │        │
   ┌──┴──┐  ┌─┴──┐  ┌──┴──┐
   │Wkr 1│  │Wkr2│  │Wkr3 │
   └─────┘  └────┘  └─────┘
```

**Properties:**
- Single coordinator at top
- Specialized workers below (2-10 workers)
- No peer-to-peer communication between workers
- All coordination flows through coordinator
- Workers cannot spawn sub-agents

**Why Hierarchical:**
- Attack surface reduction: Workers can't compromise each other
- Clear chain of custody: Every action traces to coordinator
- Single point of monitoring and control
- Cost enforcement at coordinator level

**Why NOT Mesh/Swarm:**
- Mesh creates N² communication paths = N² attack surfaces
- Swarm consensus can be poisoned by compromised agents
- Distributed coordination makes auditing impossible
- Multi-agent amplification attacks become trivial

### Communication Protocol

**Internal communication uses structured messages, not natural language.**

**Message Structure:**
```json
{
  "from": "coordinator",
  "to": "worker_1",
  "type": "TASK_ASSIGNMENT",
  "task_id": "task_123",
  "action": "retrieve_information",
  "parameters": {
    "query": "...",
    "scope": "approved_docs_only"
  },
  "constraints": {
    "max_retrievals": 3,
    "timeout_ms": 5000
  }
}
```

**Why Structured Messages:**
- Typed schemas prevent prompt injection between agents
- Easier to validate than natural language
- Supports automated security checks
- Clear contract between agents

**External Protocol:**
- MCP (Model Context Protocol) for tool communication
- Standardized, auditable, widely supported
- No A2A for external frameworks (interoperability increases attack surface)

### Centralized Retrieval Service

**Retrieval is not per-agent. It's a centralized service controlled by the coordinator.**

```
┌─────────────────┐
│   Coordinator   │
└────────┬────────┘
         │
    ┌────┴─────────┐
    │   Retrieval  │  ← Single service
    │   Service    │  ← Centralized validation
    └────┬─────────┘
         │
    ┌────┴─────────┐
    │  Vector DB   │
    └──────────────┘
```

**Retrieval Flow:**
1. Agent requests retrieval from coordinator
2. Coordinator validates query
3. Retrieval service queries vector DB
4. Results filtered and validated
5. Coordinator returns approved results to agent

**Why Centralized:**
- Single validation point (one place to secure)
- Complete audit trail (every retrieval logged)
- Access control enforcement (coordinator mediates)
- Rate limiting (prevent retrieval amplification)
- Cost control (coordinator enforces budget)

**Why NOT Per-Agent:**
- N agents = N implementations = N vulnerabilities
- Workers could poison each other via retrieved content
- No global retrieval limits
- Audit trail fragmented across agents

### Memory Isolation

**Each agent has private memory. Sharing requires coordinator mediation.**

**Agent Memory Scope:**
```
Coordinator Memory:
  - System state
  - Task assignments
  - Worker status
  - Aggregate budgets

Worker Memory (Agent-Local):
  - Assigned task context
  - Tool results
  - Retrieved documents
  - Intermediate reasoning

Shared Memory: NONE
```

**Cross-Agent Information Flow:**
- Worker cannot read another worker's memory
- Coordinator has read-only access to worker memory
- If workers need to share information:
  1. Worker sends result to coordinator
  2. Coordinator validates result
  3. Coordinator decides if safe to share
  4. Coordinator sends to other worker

**Why Agent-Local:**
- Prevents lateral movement between compromised agents
- Contains poisoned data to single agent
- Clear information flow boundaries
- Simplified security model

---

## Pillar 3: Execution Model

### Reasoning Pattern: Plan-Execute-Reflect

**Agents use explicit planning before execution, not reactive loops.**

**Flow:**
```
1. PLAN
   └─ Agent produces complete plan upfront
   └─ Plan validated against constraints
   └─ Human approves plan

2. EXECUTE
   └─ Each step executed with validation
   └─ Results checked before proceeding
   └─ Coordinator enforces plan sequence

3. REFLECT
   └─ Between steps, not during
   └─ Reflection isolated from execution
   └─ Can suggest modifications (requires approval)
```

**Why Plan-Execute-Reflect:**
- Plan is auditable artifact (security review before execution)
- Cost predictable (no unbounded loops)
- Prompt injection resistant (malicious outputs can't hijack mid-execution)
- Human can review and modify plan before execution

**Why NOT ReAct:**
- ReAct loops can be hijacked by malicious tool outputs
- Unbounded iteration = unbounded cost
- Hard to audit (decisions made dynamically)
- Easier for attacker to exploit via action-observation cycles

### Planning Constraints

**Plans have hard limits to prevent unbounded execution.**

**Limits:**
- Maximum plan depth: 10 steps
- Maximum branch factor: 3 (conditional branching)
- Maximum retries per step: 3
- No dynamic replanning without human approval

**Plan Structure:**
- Linear with conditional branches (not graph-based)
- Each step has clear success/failure criteria
- Explicit termination conditions

**Why Linear:**
- Graph-based plans create exponential search spaces
- Adaptive replanning can be hijacked
- Simple plans are auditable

### Tool Execution Model

**Tools execute synchronously, one at a time.**

**Execution:**
- Agent calls tool
- Coordinator validates call
- Tool executes in sandbox
- Result validated
- Return to agent
- Next tool (no parallelism)

**Why Synchronous:**
- Async creates race conditions
- Parallel calls enable timing attacks
- Synchronous is deterministic and auditable
- Performance cost acceptable for security

**Tool Result Validation:**
- Must match expected schema
- Size limits enforced
- Scanned for injection patterns
- Timeout if too slow

**Tool Chaining:**
- No automatic chaining
- Each tool call explicit in plan
- Results don't automatically feed next tool
- Coordinator mediates between tools

### Retrieval Execution Model

**Retrieval is simple, single-step. Not agentic.**

**Simple Retrieval:**
```
Query → Retrieve → Validate → Return
```

**NOT Agentic Retrieval:**
```
Query → Retrieve → Evaluate → Requery → Loop...
```

**What We Support:**
- Single query → single retrieval → done
- Query transformation (before retrieval, not iterative)
- Reranking (post-retrieval, doesn't trigger new queries)

**What We Reject:**
- Self-RAG (agent evaluates and re-queries)
- Corrective RAG (agent tries alternative strategies)
- Multi-hop retrieval (query → retrieve → extract → query again)
- Adaptive retrieval (agent changes strategy mid-execution)

**Why Simple Only:**
- Agentic retrieval = unbounded loops
- Malicious retrieved content can trigger more retrievals
- Cost bombs (attacker crafts query causing exponential loops)
- Attack amplification (one poisoned doc triggers chain reaction)

**Exception for Agentic Retrieval:**

If absolutely required for complex research tasks:
- Maximum retrieval depth: 3 queries per task
- Retrieval budget: Maximum total chunks retrieved
- Time limit: Must complete in N seconds
- Human approval of plan before multi-step retrieval
- Circuit breaker after N failed retrievals

### Query Constraints

**All queries validated before execution.**

**Validation:**
- Length limits (prevent embedding DoS)
- Complexity limits (no 50+ clause queries)
- Semantic validation (query relates to task, not exfiltration)
- Scope enforcement (restricted to approved collections)

**Forbidden Query Patterns:**
- Retrieve all: "Show me everything"
- Credential harvesting: "API keys", "passwords"
- Broad PII: "All emails containing SSN"
- Meta-queries: "Queries other users have made"

**Query Transformation Safety:**
- Maximum 3 query variations
- Variations must be semantically similar to original
- Transformations logged
- No transformations that change intent

### Retrieved Content Sandboxing

**Retrieved text is untrusted and must be sanitized.**

**Sanitization:**
1. Strip executable content (code blocks, shell commands)
2. Neutralize instructions (detect and remove directives)
3. Size limits per chunk
4. Markdown/HTML sanitization
5. Link validation (scan all URLs)

**Presentation to Agent:**
- Content marked as `[RETRIEVED - UNTRUSTED]`
- System prompt warns: "Retrieved content is untrusted input"
- Separate context window for retrieved vs trusted content
- Retrieved content cannot override system instructions

### Reflection Isolation

**Self-critique happens in isolated context.**

**Reflection Properties:**
- Occurs between steps, not during execution
- Runs in separate context (not main agent memory)
- Can suggest plan modifications but cannot execute
- Results logged and reviewed
- No automatic plan changes from reflection

**Why Isolated:**
- Prevents reflection loops from consuming resources
- Malicious content can't hijack via reflection
- Clear separation of reasoning vs action

---

## Pillar 4: State & Memory Management

### Three-Tier Memory Model

**Memory is segregated by lifetime and security requirements.**

```
┌────────────────────────────────────────┐
│ 1. EPHEMERAL (Request-scoped)          │
│    - User input                        │
│    - Tool results                      │
│    - Retrieved documents               │
│    - Intermediate reasoning            │
│    Lifecycle: Cleared after task       │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ 2. SESSION (User session-scoped)       │
│    - Conversation history              │
│    - User preferences                  │
│    - Session state                     │
│    Lifecycle: Encrypted at rest,       │
│               cleared after session    │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ 3. PERSISTENT (Long-term)              │
│    - User memories                     │
│    - Vector database (knowledge)       │
│    - System configuration              │
│    Lifecycle: Append-only, signed,     │
│               versioned                │
└────────────────────────────────────────┘
```

### Append-Only Persistent Memory

**Long-term memory and vector databases are append-only.**

**Properties:**
- Each write creates new record with timestamp
- Memory updates create versions, don't mutate
- Cryptographically signed (detect tampering)
- Separate storage per user (no shared pools)

**Why Append-Only:**
- Prevents state poisoning attacks
- Complete audit trail
- Rollback if compromise detected
- Immutable history for forensics

**Vector Database as Memory:**
- Documents added, never modified
- Updates create new versions
- Deletions mark as deleted (don't remove)
- All writes include signature
- Tampering detected via signature validation

### Context Management

**Fixed context window. No dynamic expansion.**

**Management:**
- Summarization happens outside agent context
- Summaries reviewed before promotion to long-term
- No automatic RAG retrieval to expand context
- Clear boundary between working memory and knowledge base

**Why Fixed:**
- Prevents context stuffing attacks
- Predictable token consumption
- Summarization is explicit step (auditable)
- No automatic memory promotion

### Checkpointing

**Checkpoints are immutable snapshots.**

**Properties:**
- Signed with cryptographic hash
- Restoration validates hash first
- Failed validation = refuse to restore (fail secure)
- Checkpoints stored append-only

**Why Immutable:**
- Prevents checkpoint poisoning
- Rollback is trustworthy
- Forensics can trace state evolution

### Memory Scope Enforcement

**Memory boundaries enforced by architecture.**

```
Coordinator:
  - Read-only access to worker memory
  - Cannot modify worker state
  - Aggregates, doesn't share

Workers:
  - Agent-local memory only
  - Cannot read other workers
  - Retrieved content stays local

Vector DB:
  - Accessed via retrieval service only
  - No direct agent access
  - Writes via ingestion pipeline only
```

**Cross-Agent Sharing:**
- Requires explicit coordinator mediation
- Content validated before sharing
- Logged in audit trail
- Shared content re-validated at recipient

### Chunking Integrity

**Document chunking is deterministic and verifiable.**

**Requirements:**
- Chunking strategy must be deterministic
- Same document → same chunks (always)
- Chunks include hash of source document
- Chunk provenance tracked

**Metadata Per Chunk:**
```json
{
  "chunk_id": "chunk_5",
  "source_document_id": "doc_123",
  "source_hash": "sha256:...",
  "chunk_sequence": 5,
  "total_chunks": 12,
  "chunking_strategy": "recursive_v2",
  "indexed_timestamp": "2026-05-21T10:30:00Z"
}
```

**Why Deterministic:**
- Detect manipulation (different chunks = tampering)
- Reproducible (can regenerate and compare)
- Audit trail (know how document was chunked)

---

## Pillar 5: Observability & Resilience

### Structured Logging

**Three log streams capture different aspects.**

**1. Audit Log** (Human-Readable):
- Decisions made
- Approvals granted/denied
- Permission changes
- Resource limit changes
- Human gates triggered

**2. Trace Log** (Machine-Readable):
- All tool calls with parameters
- All retrievals with queries
- Agent messages
- State transitions
- Timing information

**3. Security Log** (Anomaly Detection):
- Failed validations
- Permission denials
- Circuit breaker trips
- Content filtering events
- Unusual patterns

**Log Properties:**
- Append-only
- Tamper-evident
- Sensitive data redacted (credentials, PII)

### Retrieval Audit Trail

**Every retrieval logged with full context.**

```json
{
  "timestamp": "2026-05-21T10:30:00Z",
  "agent_id": "worker_1",
  "task_id": "task_123",
  "query": "API security best practices",
  "query_hash": "sha256:...",
  "results_count": 5,
  "chunks_retrieved": ["chunk_1", "chunk_2", ...],
  "relevance_scores": [0.92, 0.87, 0.81, ...],
  "validation_passed": true,
  "content_filtered": false,
  "response_time_ms": 145
}
```

**Anomaly Detection:**
- Unusually broad queries (exfiltration attempts?)
- Repeated failures (attack attempts?)
- Expensive queries (cost bomb?)
- Unusual document collections accessed

### OpenTelemetry Tracing

**Distributed tracing across all components.**

**Properties:**
- Every operation has trace ID
- Parent-child relationships preserved
- Spans include: duration, resources, errors
- Coordinator and workers traced
- Retrieval service traced

**What We Trace:**
- Token usage per agent
- Tool invocation counts and timing
- Retrieval queries and latencies
- Memory allocations
- Cost accumulation

### Circuit Breakers

**Automatic cutoffs when behavior becomes abnormal.**

**Conditions:**
```
Tool Execution:
  - After N consecutive failures → break
  - After M total failures in window → break
  - Manual reset required

Retrieval:
  - Too many retrievals (>N per minute) → break
  - Too expensive (cost exceeds budget) → break
  - Too slow (queries >5 seconds) → break
  - High filtering rate (>50% filtered) → break

Agent:
  - Too many errors → break
  - Budget exceeded → break
  - Time limit exceeded → break
```

**When Circuit Breaks:**
1. Stop agent immediately
2. Log incident with full context
3. Alert human operator
4. Require manual reset (investigate first)

**Why Manual Reset:**
- Automatic recovery allows attacker to retry
- Forces investigation
- Prevents cascading failures

### Content Filtering Telemetry

**Track what's being filtered and why.**

**Metrics:**
- Filtering rate per agent
- Filtering rate per document collection
- Common patterns triggering filters
- False positive rate (manual review)

**Alerts:**
- High filtering rate (>10% of retrievals) → poisoned DB?
- Specific agent repeatedly filtered → compromised?
- Specific collection triggering filters → investigate source

### Vector Database Health Monitoring

**Continuous validation of knowledge base integrity.**

**Health Checks:**
- Index integrity: Do embeddings match source text?
- Document provenance: All docs have valid attribution?
- Anomalous clusters: Embeddings outside expected distribution?
- Access patterns: Unusual queries?
- Write patterns: Documents added without validation?

**Red Flags:**
- Document added bypassing ingestion pipeline
- Embedding cluster far from known data
- Many filtered results from specific collection
- Queries that seem to map vector space (reconnaissance)

### Error Handling: Fail Secure

**On error, halt and request intervention. Never fail open.**

**Behavior:**
- Validation error → halt, log, alert
- Tool error → halt, log, alert
- Retrieval error → halt, log, alert
- Budget exceeded → halt, log, alert

**No Automatic Fallbacks:**
- No "try less secure mode"
- No "skip validation this time"
- No "auto-approve on error"

**Retry Policy:**
- Maximum 3 retries for transient errors
- Exponential backoff with jitter
- No retries for validation failures (fail immediately)
- Retry budget enforced

---

## The Trade-Offs

Building a secure agent system requires accepting explicit trade-offs. We optimize for security and auditability at the expense of convenience and performance.

### Security Over Convenience

**We Choose:**
- Explicit tool permissions (user grants each tool)
- Plan approval before execution (human reviews)
- No "just run it" mode

**We Accept:**
- Slower iteration for developers
- More friction for end users
- Extra approval steps

**Why:** Convenience features like auto-approval are exactly how attacks succeed.

### Simplicity Over Flexibility

**We Choose:**
- Hierarchical topology (not mesh/swarm)
- Linear plans (not complex graphs)
- Synchronous execution (not async)
- Simple retrieval (not agentic)

**We Accept:**
- Cannot support certain multi-agent patterns
- Cannot optimize for maximum throughput
- Cannot implement advanced agentic RAG

**Why:** Complexity creates exponentially larger attack surfaces. Simple systems are auditable.

### Constraints Over Autonomy

**We Choose:**
- Maximum plan depth (10 steps)
- Maximum workers (10)
- Maximum retrievals (bounded per task)
- No auto-replanning

**We Accept:**
- Cannot support fully autonomous agents
- Cannot handle unbounded problems
- Cannot implement self-learning systems

**Why:** Unbounded autonomy is unbounded risk. Constraints enable safety.

### Isolation Over Performance

**We Choose:**
- Container-level sandboxing
- Agent-local memory
- Centralized retrieval service
- No result caching

**We Accept:**
- Higher latency per operation
- Higher resource overhead
- Lower throughput

**Why:** Shared state creates side channels and race conditions. Isolation prevents lateral movement.

### Immutability Over Flexibility

**We Choose:**
- Append-only memory
- Append-only vector DB
- Immutable checkpoints
- Versioned state

**We Accept:**
- Cannot edit history
- Higher storage costs
- Cannot optimize for compaction

**Why:** Mutable state enables poisoning. Immutability enables forensics and rollback.

### Security Over Retrieval Quality

**We Choose:**
- Filter retrieved content (even if reduces quality)
- Block suspicious queries (even if legitimate)
- Centralized retrieval (even if slower)
- Read-only agents (even if limits learning)

**We Accept:**
- Some legitimate queries blocked
- Some useful results filtered
- Cannot implement agent-controlled indexing

**Why:** Retrieval is a prime attack vector. Quality matters less than security.

---

## What We Explicitly Reject

Certain patterns are security anti-patterns. We reject them entirely.

### ❌ Deserialization of Untrusted Data

**Examples:**
- Python pickle from tool output
- JSON deserialization without schema validation
- Loading arbitrary objects from retrieved documents

**Attack:** Remote code execution via crafted payloads

**Alternative:** Structured data only (validated JSON schemas, Pydantic models)

### ❌ Code Execution Without Sandbox

**Examples:**
- `eval()`, `exec()` on tool results
- Running agent-generated code directly
- Shell command execution without container

**Attack:** Arbitrary code execution

**Alternative:** Predefined tool library in containers only

### ❌ Natural Language Agent-to-Agent Communication

**Examples:**
- Agents passing free-text messages
- Worker A sends string to Worker B
- Conversational multi-agent

**Attack:** Prompt injection between agents

**Alternative:** Structured message schemas only

### ❌ Auto-Approval Based on Trust Scores

**Examples:**
- ML model decides if tool call is "safe"
- Automatic permission escalation
- "Smart" approval systems

**Attack:** Adversarial examples fool classifier

**Alternative:** Explicit allowlists, human approval

### ❌ Shared Tool State

**Examples:**
- Tools maintaining state across invocations
- Global variables in tool code
- Persistent connections

**Attack:** State poisoning, side channels

**Alternative:** Stateless tools, state in memory tier

### ❌ Developer Mode Bypasses in Production

**Examples:**
- `--unsafe`, `--skip-validation`, `--trust-all` flags
- Debug modes that disable security
- Testing backdoors

**Attack:** Bypasses enable attacks

**Alternative:** Separate dev/prod deployments, no bypasses

### ❌ Unlimited Autonomy

**Examples:**
- "Run until complete" without bounds
- No iteration limits
- No cost caps

**Attack:** Cost bombs, infinite loops

**Alternative:** Explicit limits on iterations, time, cost

### ❌ Agent-Controlled Indexing

**Examples:**
- Agent decides what to add to vector DB
- Agent learns from conversation and auto-indexes
- Agent modifies knowledge base

**Attack:** Self-poisoning, knowledge base corruption

**Alternative:** Separate ingestion pipeline with human approval

### ❌ Unvalidated Retrieval

**Examples:**
- Retrieve and immediately add to context
- No filtering on retrieved content
- Trust vector DB implicitly

**Attack:** Retrieval injection

**Alternative:** Validate all results before agent sees them

### ❌ Vector DB Access via Tools

**Examples:**
- Agent uses "vector_db_query" tool
- Direct DB access from worker
- Tools that can write to DB

**Attack:** Bypasses centralized controls

**Alternative:** Retrieval only via coordinator service

### ❌ Shared Vector DB for Multi-Tenant

**Examples:**
- All users query same DB
- User data mixed in single index
- Cross-user retrieval possible

**Attack:** Information leakage across users

**Alternative:** Separate vector DB per user/tenant

### ❌ RAG Over Untrusted Data Sources

**Examples:**
- "Scrape and index any website"
- User-provided URLs auto-indexed
- No validation of source trustworthiness

**Attack:** Attacker-controlled content enters knowledge base

**Alternative:** Curated, approved data sources only

---

## Implementation Checklist

When building a secure agent system, validate against this checklist.

### Trust Architecture

- [ ] Input validation for user input, tool results, retrieval results
- [ ] Permission model: scoped, per-invocation, explicit approval
- [ ] Container-level sandboxing for all execution
- [ ] Vector DB write access control (agents read-only)
- [ ] Embedding validation and anomaly detection
- [ ] Data connector sandboxing
- [ ] Ingestion pipeline with human approval
- [ ] Query validation and constraints
- [ ] Retrieved content filtering and sanitization

### Topology & Coordination

- [ ] Hierarchical architecture (coordinator + workers)
- [ ] No peer-to-peer worker communication
- [ ] Structured message passing (typed schemas)
- [ ] Centralized retrieval service
- [ ] Agent-local memory (no shared memory)
- [ ] Coordinator mediates all information flow
- [ ] MCP for external tool communication

### Execution Model

- [ ] Plan-Execute-Reflect pattern
- [ ] Plan approval before execution
- [ ] Planning constraints (max depth, branches)
- [ ] Synchronous tool execution
- [ ] Simple retrieval only (not agentic)
- [ ] Query constraints and validation
- [ ] Retrieved content sandboxing
- [ ] Reflection isolation
- [ ] Maximum iterations, time, cost limits

### State & Memory

- [ ] Three-tier memory model (ephemeral, session, persistent)
- [ ] Append-only persistent memory
- [ ] Append-only vector database
- [ ] Cryptographic signatures on embeddings
- [ ] Provenance metadata for all documents
- [ ] Deterministic chunking
- [ ] Immutable checkpoints
- [ ] Agent-local memory isolation
- [ ] Fixed context window

### Observability & Resilience

- [ ] Structured logging (audit, trace, security)
- [ ] OpenTelemetry tracing
- [ ] Retrieval audit trail
- [ ] Content filtering telemetry
- [ ] Circuit breakers (tools, retrieval, agent)
- [ ] Vector DB health monitoring
- [ ] Fail-secure error handling
- [ ] Manual reset on circuit break
- [ ] Anomaly detection on logs

---

## Architecture Diagram

```
                    ┌──────────────────────────────┐
                    │     COORDINATOR AGENT        │
                    │  ┌────────────────────────┐  │
                    │  │ • Plan validation      │  │
                    │  │ • Permission control   │  │
                    │  │ • Budget enforcement   │  │
                    │  │ • Audit logging        │  │
                    │  └────────────────────────┘  │
                    └──────┬──────────────┬────────┘
                           │              │
        ┌──────────────────┴───┐    ┌────┴─────────────────┐
        │                      │    │                      │
   ┌────▼─────┐         ┌─────▼────┐         ┌──────────▼─┐
   │ Worker 1 │         │ Worker 2 │         │  Retrieval │
   │          │         │          │         │  Service   │
   │ • Local  │         │ • Local  │         │            │
   │   memory │         │   memory │         │ • Query    │
   │ • Task   │         │ • Task   │         │   validate │
   │   exec   │         │   exec   │         │ • Result   │
   └────┬─────┘         └─────┬────┘         │   filter   │
        │                     │              └──────┬──────┘
        │ Tool calls          │ Tool calls          │
        │ (via coordinator)   │ (via coordinator)   │ READ-ONLY
        ↓                     ↓                     ↓
   ┌─────────────────────────────────────────────────────┐
   │             SANDBOXED TOOLS                         │
   │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
   │  │Container1│  │Container2│  │Container3│         │
   │  │          │  │          │  │          │         │
   │  │• Network │  │• Network │  │• Network │         │
   │  │  isolated│  │  isolated│  │  isolated│         │
   │  │• Read-   │  │• Read-   │  │• Read-   │         │
   │  │  only FS │  │  only FS │  │  only FS │         │
   │  │• Resource│  │• Resource│  │• Resource│         │
   │  │  limits  │  │  limits  │  │  limits  │         │
   │  └──────────┘  └──────────┘  └──────────┘         │
   └─────────────────────────────────────────────────────┘
                                         │
                                         │
                                    ┌────▼──────┐
                                    │  VECTOR   │
                                    │  DATABASE │
                                    │           │
                                    │ • Append  │
                                    │   only    │
                                    │ • Signed  │
                                    │ • Metadata│
                                    └────▲──────┘
                                         │
                                         │ WRITE ACCESS
                                         │ (validated)
                                         │
                                  ┌──────┴──────────┐
                                  │   INGESTION     │
                                  │   PIPELINE      │
                                  │                 │
                                  │ • Validate docs │
                                  │ • Scan content  │
                                  │ • Chunk         │
                                  │ • Embed         │
                                  │ • Sign          │
                                  │ • Human approve │
                                  └─────────────────┘
```

**Key Security Properties:**
1. Workers isolated (cannot compromise each other)
2. All tools sandboxed (container-level)
3. Retrieval centralized (single validation point)
4. Vector DB append-only (agents read-only)
5. Coordinator controls all flows (single audit point)

---

## Deployment Guidance

### Development Environment

**Characteristics:**
- Loose constraints for rapid iteration
- Verbose logging and debugging
- Sandboxing can be relaxed (but still recommended)
- Human approval gates can be simplified

**Still Required:**
- Input validation (even in dev)
- Separate vector DB per developer
- No production credentials
- Audit logging (for debugging)

### Staging Environment

**Characteristics:**
- Production-like constraints
- All security features enabled
- Test with production data (anonymized)
- Human approval gates functional

**Validation:**
- Penetration testing
- Red team exercises
- Load testing with security enabled
- Audit log review

### Production Environment

**Characteristics:**
- All security features mandatory
- No bypasses, no debug modes
- Human approval gates enforced
- Monitoring and alerting active

**Requirements:**
- Container orchestration (Kubernetes, ECS)
- Secrets management (Vault, AWS Secrets Manager)
- Audit log retention (6-12 months)
- Incident response plan
- Regular security reviews

### Multi-Tenant Considerations

**Isolation:**
- Separate vector DB per tenant
- No cross-tenant retrieval
- Tenant-scoped permissions
- Separate audit logs

**Resource Limits:**
- Per-tenant budgets
- Per-tenant rate limits
- Per-tenant storage quotas

---

## Measuring Security Posture

How do you know if your agent system is secure?

### Security Metrics

**Attack Surface:**
- Number of trust boundaries (fewer is better)
- Number of tools enabled (fewer is better)
- Number of data connectors (fewer is better)
- Number of permission exceptions (zero is best)

**Validation Coverage:**
- % of inputs validated (target: 100%)
- % of tool results validated (target: 100%)
- % of retrieval results validated (target: 100%)
- % of writes going through validation pipeline (target: 100%)

**Audit Coverage:**
- % of operations logged (target: 100%)
- % of logs with trace IDs (target: 100%)
- % of anomalies detected (depends on baseline)

**Isolation Effectiveness:**
- Number of sandboxing bypasses (target: 0)
- Number of cross-agent information leaks (target: 0)
- Number of permission escalations (target: 0)

### Testing Posture

**Red Team Exercises:**
- Prompt injection attempts (should fail)
- Tool call injection (should be blocked)
- Vector DB poisoning (should be detected)
- Retrieval injection (should be filtered)
- Cost bomb attacks (should trip circuit breakers)

**Penetration Testing:**
- Container escape attempts (should fail)
- Permission bypass attempts (should be blocked)
- Cross-tenant access (should be prevented)
- Data exfiltration attempts (should be detected)

---

## Common Pitfalls

### Pitfall 1: "Agents Are Different From Users"

**Mistake:** Treating agent-generated content as more trustworthy than user input.

**Reality:** Agents can be compromised via prompt injection. Agent output is untrusted input.

**Fix:** Validate agent output like user input.

### Pitfall 2: "Retrieved Content Is Our Data"

**Mistake:** Trusting vector DB results because "we control the database."

**Reality:** Attackers can poison the DB via compromised connectors, supply chain attacks, or insider threats.

**Fix:** Validate all retrieved content. Treat as untrusted input.

### Pitfall 3: "Sandboxing Is Slow"

**Mistake:** Skipping sandboxing for performance.

**Reality:** One unsandboxed tool execution = RCE vulnerability.

**Fix:** Accept the latency. Security > speed.

### Pitfall 4: "We'll Add Security Later"

**Mistake:** Building without security, planning to retrofit.

**Reality:** Retrofitting security is 10x harder than building it in.

**Fix:** Security-first architecture from day one.

### Pitfall 5: "Simple Retrieval Is Too Limiting"

**Mistake:** Implementing agentic retrieval for better quality.

**Reality:** Agentic retrieval creates unbounded loops and attack amplification.

**Fix:** Accept single-step retrieval. Quality < security.

### Pitfall 6: "Users Won't Accept Approval Gates"

**Mistake:** Auto-approving to reduce friction.

**Reality:** One unauthorized action = security breach.

**Fix:** Educate users on why approval matters. Convenience < security.

### Pitfall 7: "No One Will Attack Our Internal System"

**Mistake:** Relaxing security for internal-only systems.

**Reality:** Most breaches start with internal access (phishing, insider threats).

**Fix:** Same security standards for internal and external systems.

---

## Conclusion

Building secure agent systems requires accepting that **not all capabilities are compatible with security**.

We cannot have:
- Fully autonomous agents AND security
- Unbounded retrieval AND security
- Agent-controlled indexing AND security
- Shared state AND security
- Zero friction AND security

The architecture in this guide makes explicit choices:
- **Security over convenience**: Users grant permissions, approve plans
- **Simplicity over flexibility**: Hierarchical topology, linear plans
- **Constraints over autonomy**: Bounded iterations, costs, retrievals
- **Isolation over performance**: Containers, agent-local memory, centralized retrieval
- **Immutability over flexibility**: Append-only memory and vector DB

These trade-offs are not limitations—they are the foundation of trustworthy agent systems.

**The goal is not to prevent agents from being useful. The goal is to prevent them from being dangerous.**

Every boundary is explicit.  
Every permission is granted.  
Every action is auditable.  
Every failure is secure.

This is how you build agent systems you can trust in production.
