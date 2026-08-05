# Agent Framework Evaluation Dimensions - Comprehensive Guide

A detailed explanation of all 14 evaluation dimensions and their attributes.

---

## Table of Contents

1. [Structural](#1-structural---architecture--topology)
2. [Control](#2-control---flow--autonomy)
3. [Memory](#3-memory---state--persistence)
4. [Capabilities](#4-capabilities---actions--tools)
5. [Reasoning](#5-reasoning---planning--thinking)
6. [Interface](#6-interface---io-contract)
7. [Resilience](#7-resilience---error-handling)
8. [Boundaries](#8-boundaries---security--constraints)
9. [Models](#9-models---provider-configuration)
10. [Observability](#10-observability---inspection-hooks)
11. [Communication Protocols](#11-communication-protocols---standardized-interoperability)
12. [Requirements](#12-requirements---dependencies)
13. [Performance](#13-performance---characteristics)
14. [Data & Retrieval](#14-data--retrieval---rag-capabilities)

---

## 1. Structural - Architecture & Topology

**Question:** *How are agents organized and how do they communicate?*

### 1.1 topology

**What it measures:** The architectural pattern of agent organization.

**Possible values:**
- `single` - One agent operating independently
- `multi_hierarchical` - Multiple agents in manager-worker hierarchy
- `multi_mesh` - Multiple agents in peer-to-peer network
- `multi_chain` - Multiple agents in sequential pipeline
- `multi_swarm` - Multiple agents with emergent coordination
- `hybrid` - Combination of patterns

**Why it matters:** Determines scalability, coordination complexity, and failure modes.

**Examples:**
- **LangChain (single)**: One agent handles all tasks
- **CrewAI (multi_hierarchical)**: Manager delegates to specialized workers
- **AutoGen (multi_mesh)**: Agents communicate peer-to-peer
- **LangGraph (hybrid)**: Flexible graph allows various topologies

**Trade-offs:**
- Single: Simple but limited scalability
- Hierarchical: Clear coordination but single point of failure
- Mesh: Flexible but complex communication
- Hybrid: Maximum flexibility but harder to reason about

---

### 1.2 effective_agent_count

**What it measures:** The practical operational range of agents the framework supports.

**Possible values:**
- `1` - Single agent only
- `2-10`, `2-20` - Typical range for multi-agent systems
- `dynamic` - Scales to arbitrary count at runtime

**Why it matters:** Indicates the framework's design target and practical limits.

**Examples:**
- **LangChain (1)**: Designed for single-agent workflows
- **CrewAI (2-10)**: Optimized for small teams
- **AutoGen (2-20)**: Supports larger groups
- **LangGraph (dynamic)**: No inherent limit

**Trade-offs:**
- Fixed small count: Simpler coordination, less overhead
- Large range: More flexibility but higher complexity
- Dynamic: Ultimate flexibility but requires robust coordination

---

### 1.3 roles

**What it measures:** The types of specialized agent roles supported.

**Possible values:** List of role names (e.g., "supervisor", "worker", "tool_executor")

**Why it matters:** Role specialization enables division of labor and expertise.

**Examples:**
- **LangGraph**: supervisor, worker, tool_executor, human, custom
- **CrewAI**: manager, worker, custom_roles
- **AutoGen**: user_proxy, assistant, executor, custom
- **LangChain**: agent (single role)

**Trade-offs:**
- Many specialized roles: Better division of labor but more coordination overhead
- Few generic roles: Simpler but less specialization
- Custom roles: Maximum flexibility but requires more design work

---

### 1.4 communication_pattern

**What it measures:** How agents exchange messages and information.

**Possible values:**
- `direct` - Direct function calls (single agent)
- `point_to_point` - Direct agent-to-agent messages
- `broadcast` - One-to-many messaging
- `pubsub` - Publish-subscribe pattern
- `queue` - Message queue based
- `multiple` - Supports various patterns

**Why it matters:** Affects latency, coupling, and debugging complexity.

**Examples:**
- **LangChain (direct)**: No inter-agent communication
- **AutoGen (point_to_point)**: Agents directly message each other
- **Academy (pubsub)**: Decoupled publish-subscribe
- **LangGraph (multiple)**: Supports various patterns

**Trade-offs:**
- Direct: Fastest but tightly coupled
- Pubsub: Decoupled but harder to trace
- Queue: Reliable but adds latency

---

### 1.5 coordination

**What it measures:** How agent activities are synchronized and managed.

**Possible values:**
- `none` - No coordination needed (single agent)
- `centralized` - Central coordinator manages all agents
- `decentralized` - Agents self-coordinate
- `hybrid` - Mix of centralized and decentralized

**Why it matters:** Determines bottlenecks, fault tolerance, and scalability.

**Examples:**
- **CrewAI (centralized)**: Manager coordinates all workers
- **AutoGen (decentralized)**: Agents coordinate through conversation
- **LangGraph (hybrid)**: Supervisor nodes with autonomous subgraphs
- **LangChain (none)**: Single agent

**Trade-offs:**
- Centralized: Simple to reason about but single point of failure
- Decentralized: Resilient but emergent behavior harder to predict
- Hybrid: Flexible but complex to configure

---

## 2. Control - Flow & Autonomy

**Question:** *Who decides what happens next and how much freedom do agents have?*

### 2.1 autonomy_level

**What it measures:** The degree of independent decision-making agents possess.

**Possible values:**
- `fully_orchestrated` - Developer controls every step (e.g., traditional programming)
- `semi_autonomous` - Agent makes tactical decisions, human sets strategy
- `fully_autonomous` - Agent sets goals and plans independently
- `hybrid` - Varies by task or configuration

**Why it matters:** Determines how much oversight and intervention is needed.

**Examples:**
- **Semantic Kernel (fully_orchestrated)**: Developer explicitly controls flow
- **LangChain (semi_autonomous)**: Agent uses tools but follows defined chains
- **AutoGPT (fully_autonomous)**: Sets own subgoals and strategies
- **LangGraph (hybrid)**: Configurable per node in graph

**Trade-offs:**
- Fully orchestrated: Predictable but inflexible
- Semi-autonomous: Balanced control and flexibility
- Fully autonomous: Powerful but unpredictable, requires safety measures

---

### 2.2 human_gates

**What it measures:** Points where human approval is required or available.

**Possible values:**
- `none` - No human intervention points
- `optional` - Can add human checkpoints
- List of specific gates (e.g., ["approval_before_write", "confirm_send"])
- `configurable` - Can be configured per deployment

**Why it matters:** Critical for safety, compliance, and trust in high-stakes applications.

**Examples:**
- **Academy (none)**: Fully automated for distributed systems
- **LangChain (optional)**: Can add human-in-the-loop callbacks
- **AutoGen (user_proxy_agent)**: Built-in human proxy agent
- **LangGraph (configurable_per_node)**: Fine-grained control

**Trade-offs:**
- No gates: Fastest but highest risk
- Many gates: Safest but adds latency and labor
- Configurable: Flexible but requires design decisions

---

### 2.3 branching_logic

**What it measures:** Whether the framework supports conditional execution paths.

**Possible values:** `true` or `false`

**Why it matters:** Essential for handling different scenarios and error cases.

**Examples:**
- **All major frameworks (true)**: Support if/else, routing, conditional nodes
- Essential capability for practical agent systems

**Trade-offs:**
- With branching: Can handle diverse scenarios but harder to verify
- Without branching: Simpler to verify but limited to linear workflows

---

### 2.4 loop_support

**What it measures:** Whether agents can repeat actions or iterate on solutions.

**Possible values:** `true` or `false`

**Why it matters:** Required for refinement, retries, and iterative problem-solving.

**Examples:**
- **All major frameworks (true)**: Support while loops, retry loops, reflection loops
- Critical for agent autonomy and error recovery

**Trade-offs:**
- With loops: Can improve solutions but risk infinite loops
- Without loops: Safer but can't refine outputs

---

### 2.5 termination_strategy

**What it measures:** How the system decides when to stop execution.

**Possible values:**
- `max_iterations` - Stop after N steps
- `success_criteria` - Stop when goal is achieved
- `timeout` - Stop after time limit
- `manual` - Human decides when to stop
- `hybrid` - Combination of strategies

**Why it matters:** Prevents infinite execution and wasted resources.

**Examples:**
- **AutoGen (max_iterations)**: Stops after conversation limit
- **CrewAI (success_criteria)**: Stops when task complete
- **LangGraph (hybrid)**: Multiple termination conditions

**Trade-offs:**
- Max iterations: Safe but might stop too early or late
- Success criteria: Efficient but requires clear goal definition
- Timeout: Prevents runaway but arbitrary cutoff

---

## 3. Memory - State & Persistence

**Question:** *What does the agent remember and how long?*

### 3.1 short_term

**What it measures:** Memory available within a single session or task.

**Possible values:**
- `none` - No memory
- `conversation_only` - Just the current conversation history
- `session_scoped` - Shared across tasks in session
- `vector_db` - Semantic search over session data
- `graph_db` - Structured knowledge graph
- `relational_db` - SQL database
- `file_system` - File-based storage
- `custom` - Framework-specific implementation

**Why it matters:** Determines context window and task continuity.

**Examples:**
- **LangChain (conversation_only)**: Just chat history
- **LangGraph (conversation_only)**: State passed through graph
- **Semantic Kernel (session_scoped)**: Shared kernel context
- **AutoGPT (session_scoped)**: Working memory for current goal

**Trade-offs:**
- Conversation only: Simple but limited context
- Session scoped: More context but memory usage
- Database: Searchable but adds complexity

---

### 3.2 long_term

**What it measures:** Memory that persists across sessions and restarts.

**Possible values:** Same as short_term

**Why it matters:** Enables learning, personalization, and continuity.

**Examples:**
- **AutoGen (none)**: No persistence across runs
- **CrewAI (vector_db)**: Searchable knowledge base
- **Academy (file_system)**: Distributed file storage
- **LangGraph (custom)**: Pluggable persistence backends

**Trade-offs:**
- None: Fresh start each time, no learning
- Vector DB: Semantic search but requires embeddings
- File system: Simple but limited search
- Custom: Flexible but requires implementation

---

### 3.3 state_persistence

**What it measures:** Whether execution state survives crashes/restarts.

**Possible values:** `true` or `false`

**Why it matters:** Critical for long-running tasks and reliability.

**Examples:**
- **LangGraph (true)**: Checkpoint to database, resume later
- **Microsoft Agent Framework (true)**: Durable task execution
- **AutoGen (false)**: Must restart from beginning
- **LangChain (false)**: No built-in persistence

**Trade-offs:**
- With persistence: Resilient but adds storage overhead
- Without: Simpler but fragile to failures

---

### 3.4 context_management

**What it measures:** How the framework handles limited context windows.

**Possible values:**
- `none` - No management, will hit limits
- `windowing` - Sliding window (keep recent)
- `summarization` - LLM summarizes older context
- `compression` - Compress old messages
- `custom` - Framework-specific strategy
- `multiple` - Supports various strategies

**Why it matters:** Essential for long conversations and complex tasks.

**Examples:**
- **AutoGPT (summarization)**: Summarizes past actions
- **AutoGen (windowing)**: Keeps recent N messages
- **LlamaIndex (multiple)**: Various strategies available
- **LangGraph (multiple)**: Configurable per application

**Trade-offs:**
- Windowing: Fast but loses old context
- Summarization: Preserves key info but lossy and expensive
- Compression: Preserves detail but may not reduce enough

---

### 3.5 memory_scope

**What it measures:** Whether memory is local to each agent or shared.

**Possible values:**
- `agent_local` - Each agent has private memory
- `shared_across_agents` - Common memory pool
- `global` - System-wide shared state

**Why it matters:** Affects collaboration and information sharing.

**Examples:**
- **AutoGen (agent_local)**: Each agent has own memory
- **CrewAI (shared_across_agents)**: Team shares knowledge base
- **LangGraph (shared_across_agents)**: State shared in graph
- **Academy (agent_local)**: Federated, private state

**Trade-offs:**
- Agent local: Privacy and isolation but duplication
- Shared: Better collaboration but coupling and conflicts
- Global: Maximum sharing but consistency challenges

---

## 4. Capabilities - Actions & Tools

**Question:** *What can the agent actually DO?*

### 4.1 tool_support

**What it measures:** Whether agents can use external tools/functions.

**Possible values:** `true` or `false`

**Why it matters:** Tool use is fundamental to agent usefulness.

**Examples:**
- **All modern frameworks (true)**: Support function calling
- Essential capability for practical applications

**Trade-offs:**
- With tools: Powerful but security concerns
- Without tools: Safe but limited to text generation

---

### 4.2 tool_categories

**What it measures:** Types of tools/actions supported.

**Possible values:** List containing:
- `read` - Read files, databases, APIs
- `write` - Write files, modify state
- `compute` - Execute code, calculations
- `api` - Call external services
- `custom` - Framework-specific tools

**Why it matters:** Determines the action space available to agents.

**Examples:**
- **LangGraph**: read, write, api, compute, custom (comprehensive)
- **LlamaIndex**: read, api, compute, custom (data-focused)
- **AutoGen**: compute, api, custom (code execution focus)

**Trade-offs:**
- More categories: More capable but higher risk surface
- Restricted categories: Safer but less useful
- Custom tools: Flexible but requires development

---

### 4.3 execution_model

**What it measures:** How tool calls are executed relative to other operations.

**Possible values:**
- `sync` - Blocking, sequential execution
- `async` - Non-blocking, concurrent execution
- `streaming` - Real-time streaming results
- `hybrid` - Supports multiple modes

**Why it matters:** Affects latency, throughput, and user experience.

**Examples:**
- **LangChain (sync)**: Simple sequential execution
- **CrewAI (async)**: Concurrent task execution
- **LangGraph (hybrid)**: Configurable per workflow
- **LlamaIndex (async)**: Parallel data retrieval

**Trade-offs:**
- Sync: Simple to debug but slower
- Async: Faster but harder to reason about
- Streaming: Best UX but complex implementation

---

### 4.4 tool_chaining

**What it measures:** Whether agents can compose tools (use output of one as input to another).

**Possible values:** `true` or `false`

**Why it matters:** Essential for multi-step tasks and autonomy.

**Examples:**
- **All major frameworks (true)**: Support tool composition
- Key capability for complex workflows

**Trade-offs:**
- With chaining: Powerful but can compound errors
- Without chaining: Safer but limited to simple tasks

---

### 4.5 sandboxing

**What it measures:** Isolation level for tool execution.

**Possible values:**
- `none` - No isolation, full system access
- `process_isolation` - Separate process
- `container` - Docker/similar container
- `vm` - Full virtual machine
- `custom` - Framework-specific isolation

**Why it matters:** Critical for security when executing untrusted code.

**Examples:**
- **Most frameworks (none)**: No built-in sandboxing
- **AutoGen (container)**: Docker for code execution
- **Microsoft Agent Framework (container)**: Containerized tools
- **Academy (container)**: Isolated compute workers

**Trade-offs:**
- None: Fast but dangerous
- Process: Light isolation but can escape
- Container: Good balance of safety and performance
- VM: Maximum safety but slow

---

## 5. Reasoning - Planning & Thinking

**Question:** *HOW does the agent think and plan?*

### 5.1 pattern

**What it measures:** The cognitive pattern or thinking style the agent uses.

**Possible values:**
- `none` - No structured reasoning
- `react` - Reason-Act-Observe loop
- `cot` - Chain of Thought (step-by-step reasoning)
- `tot` - Tree of Thoughts (explore multiple paths)
- `plan_execute` - Plan first, then execute
- `custom` - Framework-specific pattern
- `multiple` - Supports various patterns

**Why it matters:** Different patterns suit different problem types.

**Examples:**
- **LangChain (react)**: Iterative reasoning and acting
- **AutoGPT (cot)**: Explicit step-by-step thinking
- **Semantic Kernel (plan_execute)**: Hierarchical planning
- **LangGraph (multiple)**: Configurable per application

**Trade-offs:**
- ReAct: Good for exploration but many LLM calls
- CoT: Explicit reasoning but verbose
- Plan-Execute: Efficient if plan is good but inflexible
- ToT: Thorough but very expensive

---

### 5.2 planning_strategy

**What it measures:** How the agent breaks down and organizes tasks.

**Possible values:**
- `none` - No planning, reactive only
- `linear` - Sequential plan (step 1, 2, 3...)
- `hierarchical` - Nested subgoals
- `graph` - DAG of dependent tasks
- `adaptive` - Replan based on results

**Why it matters:** Determines ability to handle complex, multi-step problems.

**Examples:**
- **AutoGen (linear)**: Simple sequential plans
- **CrewAI (hierarchical)**: Tasks with subtasks
- **LangGraph (graph)**: Complex dependencies
- **Academy (adaptive)**: Dynamic replanning

**Trade-offs:**
- Linear: Simple but inflexible
- Hierarchical: Good decomposition but rigid structure
- Graph: Flexible dependencies but complex to manage
- Adaptive: Handles uncertainty but expensive replanning

---

### 5.3 reflection

**What it measures:** Whether agents can critique and improve their own outputs.

**Possible values:** `true` or `false`

**Why it matters:** Improves output quality through self-correction.

**Examples:**
- **LangGraph (true)**: Self-critique nodes in graph
- **AutoGen (true)**: Multi-agent reflection
- **LlamaIndex (true)**: Query refinement loops
- **CrewAI (false)**: No built-in reflection
- **Semantic Kernel (false)**: No self-critique

**Trade-offs:**
- With reflection: Better quality but more LLM calls
- Without reflection: Faster but lower quality
- Can get stuck in reflection loops if not bounded

---

### 5.4 model_calls_per_task

**What it measures:** Typical number of LLM calls to complete a task.

**Possible values:**
- `1` - Single call
- `1-5` - Few calls
- `5-20` - Many calls
- `10-50` - Very many calls
- `variable` - Depends on task complexity

**Why it matters:** Directly affects cost and latency.

**Examples:**
- **Academy (0-1)**: Minimal LLM use, traditional compute
- **LangChain (1-5)**: Efficient, focused calls
- **AutoGen (5-20)**: Conversational, many turns
- **AutoGPT (10-50)**: Highly autonomous, expensive

**Trade-offs:**
- Fewer calls: Faster and cheaper but less capable
- More calls: More autonomous and thorough but expensive
- Variable: Flexible but unpredictable cost

---

### 5.5 search_strategy

**What it measures:** How agents explore solution spaces.

**Possible values:**
- `none` - No search, follow single path
- `greedy` - Take best option at each step
- `beam` - Keep top K options
- `mcts` - Monte Carlo Tree Search (explore randomly, exploit winners)

**Why it matters:** Affects quality vs. cost trade-off in exploration.

**Examples:**
- **Most frameworks (greedy)**: Simple best-first search
- **LangGraph (none)**: Graph defines path
- Future: ToT implementations would use beam or MCTS

**Trade-offs:**
- Greedy: Fast but can get stuck in local optima
- Beam: Better quality but K times more expensive
- MCTS: Best for complex spaces but very expensive

---

## 6. Interface - I/O Contract

**Question:** *What goes in and what comes out?*

### 6.1 input_modalities

**What it measures:** Types of input the agent can accept.

**Possible values:** List containing:
- `text` - Plain text, markdown
- `image` - Images, screenshots
- `audio` - Speech, sound
- `video` - Video content
- `file` - Document files (PDF, DOCX, etc.)
- `structured` - JSON, XML, databases

**Why it matters:** Determines applicability to different use cases.

**Examples:**
- **LangGraph**: text, structured, image (multimodal)
- **LangChain**: text, image (vision models)
- **AutoGen**: text only (traditional)
- **LlamaIndex**: text, structured (data-focused)

**Trade-offs:**
- Text only: Simple but limited applications
- Multimodal: More capable but requires model support
- Structured: Precise but requires formatting

---

### 6.2 output_modalities

**What it measures:** Types of output the agent produces.

**Possible values:** Same as input_modalities

**Why it matters:** Determines integration capabilities and use cases.

**Examples:**
- **Most frameworks**: text, structured (standard)
- **AutoGPT**: text, file (can write files)
- **LlamaIndex**: text, structured (data retrieval)

**Trade-offs:**
- Text only: Simple but requires parsing
- Structured: Easier integration but less flexible
- Files: Persistent but management overhead

---

### 6.3 streaming_support

**What it measures:** Whether output is delivered incrementally in real-time.

**Possible values:** `true` or `false`

**Why it matters:** Critical for responsive user experience.

**Examples:**
- **Most modern frameworks (true)**: Stream tokens as generated
- **AutoGen (false)**: Waits for complete messages
- Essential for chat applications

**Trade-offs:**
- With streaming: Better UX but more complex to implement
- Without streaming: Simpler but poor perceived latency

---

### 6.4 api_style

**What it measures:** How developers interact with the framework.

**Possible values:**
- `function_call` - Call functions/methods
- `message_passing` - Send/receive messages
- `rest` - HTTP REST API
- `grpc` - gRPC protocol
- `custom` - Framework-specific
- `multiple` - Supports various styles

**Why it matters:** Affects developer experience and integration patterns.

**Examples:**
- **LangChain (function_call)**: Python function calls
- **LangGraph (message_passing)**: Message-based graph
- **Microsoft Agent Framework (multiple)**: REST, gRPC, SDK
- **AutoGPT (function_call)**: Method-based API

**Trade-offs:**
- Function call: Familiar but tightly coupled
- Message passing: Decoupled but async complexity
- REST: Standard but network overhead
- gRPC: Fast but less universal

---

## 7. Resilience - Error Handling

**Question:** *What happens when things go wrong?*

### 7.1 retry_policy

**What it measures:** How the framework handles transient failures.

**Possible values:**
- `none` - No retries, fail immediately
- `fixed` - Retry with constant delay
- `exponential_backoff` - Increasing delays between retries
- `adaptive` - Adjust based on error type

**Why it matters:** Essential for reliability with unreliable services (LLM APIs).

**Examples:**
- **LangGraph (exponential_backoff)**: Best practice
- **Microsoft Agent Framework (exponential_backoff)**: Production-grade
- **AutoGen (fixed)**: Simple retry logic
- **Some frameworks (none)**: Fragile to transient errors

**Trade-offs:**
- None: Fast failure but not resilient
- Fixed: Simple but can overwhelm failing service
- Exponential: Respectful and effective but slower recovery
- Adaptive: Optimal but complex to implement

---

### 7.2 max_retries

**What it measures:** Maximum retry attempts before giving up.

**Possible values:** Number (e.g., 3, 5) or "configurable" or "unlimited"

**Why it matters:** Balances resilience vs. wasted resources.

**Examples:**
- **Most frameworks**: 3 (reasonable default)
- **Academy**: 5 (distributed systems need more)
- **LangGraph**: configurable (application-specific)

**Trade-offs:**
- Low number: Fail fast but less resilient
- High number: More resilient but can waste time/money
- Configurable: Flexible but requires tuning

---

### 7.3 fallback_strategy

**What it measures:** What to do when primary path fails.

**Possible values:**
- `none` - No fallback, report failure
- `degraded_mode` - Continue with reduced functionality
- `alternative_path` - Try different approach
- `fail_fast` - Stop immediately

**Why it matters:** Determines graceful degradation vs. hard failure.

**Examples:**
- **LangGraph (alternative_path)**: Route to fallback nodes
- **CrewAI (degraded_mode)**: Simplify task or reduce quality
- **AutoGen (fail_fast)**: Stop conversation on error
- **Microsoft Agent Framework (alternative_path)**: Fallback agents

**Trade-offs:**
- Fail fast: Clear failure but no recovery
- Degraded mode: Keep running but reduced quality
- Alternative path: Best effort but complex to design

---

### 7.4 checkpointing

**What it measures:** Ability to save state and resume after failure.

**Possible values:** `true` or `false`

**Why it matters:** Critical for long-running tasks and expensive operations.

**Examples:**
- **LangGraph (true)**: Save state to database, resume anywhere
- **Microsoft Agent Framework (true)**: Durable execution
- **AutoGPT (true)**: Save progress between runs
- **Most frameworks (false)**: Must restart from beginning

**Trade-offs:**
- With checkpointing: Resilient but storage overhead
- Without: Simpler but fragile to failures
- Essential for tasks >5 minutes

---

### 7.5 circuit_breaker

**What it measures:** Whether framework stops calling failing services.

**Possible values:** `true` or `false`

**Why it matters:** Prevents cascading failures and wasted resources.

**Examples:**
- **Microsoft Agent Framework (true)**: Enterprise-grade
- **Academy (true)**: Distributed systems best practice
- **Most frameworks (false)**: Will keep calling failing services

**Trade-offs:**
- With circuit breaker: Protects system but adds complexity
- Without: Simpler but can waste resources on dead services
- Important for production systems

---

## 8. Boundaries - Security & Constraints

**Question:** *What are the safety limits and controls?*

### 8.1 input_validation

**What it measures:** How rigorously inputs are checked for safety.

**Possible values:**
- `none` - No validation
- `basic` - Type checking, simple filters
- `advanced` - Pattern matching, sanitization
- `llm_based` - Use LLM to detect malicious inputs

**Why it matters:** First line of defense against prompt injection and abuse.

**Examples:**
- **Most frameworks (basic)**: Type checking only
- **Microsoft Agent Framework (advanced)**: Comprehensive validation
- **Academy (advanced)**: Security-focused
- Some research systems (llm_based): Experimental

**Trade-offs:**
- None: Fast but vulnerable
- Basic: Minimal overhead but limited protection
- Advanced: Better security but can reject valid inputs
- LLM-based: Most thorough but expensive and can be bypassed

---

### 8.2 output_filtering

**What it measures:** Post-processing to remove sensitive or harmful content.

**Possible values:**
- `none` - No filtering
- `basic` - Simple pattern matching
- `pii_detection` - Remove personal information
- `content_moderation` - Check for harmful content
- `custom` - Framework-specific filters

**Why it matters:** Prevents data leaks and harmful outputs.

**Examples:**
- **Microsoft Agent Framework (content_moderation)**: Azure Content Safety
- **LangGraph (custom)**: Pluggable filters
- **Most frameworks (none)**: No built-in filtering

**Trade-offs:**
- None: Fast but risky
- PII detection: Protects privacy but false positives
- Content moderation: Safer but censorship concerns
- Custom: Flexible but requires implementation

---

### 8.3 resource_limits

**What it measures:** Whether framework enforces compute/cost limits.

**Possible values:** `true` or `false`

**Why it matters:** Prevents runaway costs and resource exhaustion.

**Examples:**
- **Most frameworks (true)**: Some form of limiting
- **Some frameworks (false)**: No built-in limits
- Important for production and shared resources

**Trade-offs:**
- With limits: Safe but requires configuration
- Without limits: Flexible but dangerous
- Should always be present in production

---

### 8.4 permission_model

**What it measures:** Access control system for tools and resources.

**Possible values:**
- `none` - No access control
- `allowlist` - Explicitly list allowed actions
- `denylist` - Block specific actions
- `rbac` - Role-based access control
- `custom` - Framework-specific model

**Why it matters:** Prevents unauthorized actions and data access.

**Examples:**
- **Microsoft Agent Framework (rbac)**: Enterprise-grade access control
- **CrewAI (allowlist)**: Explicit tool permissions
- **AutoGPT (allowlist)**: User approves each tool
- **Many frameworks (none)**: No access control

**Trade-offs:**
- None: Simple but no security
- Allowlist: Secure but restrictive
- RBAC: Flexible and secure but complex
- Custom: Tailored but requires implementation

---

### 8.5 sandbox_scope

**What it measures:** What resources are isolated from the host system.

**Possible values:**
- `none` - No isolation
- `network_restricted` - Can't access network
- `filesystem_restricted` - Limited file access
- `full_isolation` - Complete sandboxing

**Why it matters:** Limits damage from compromised or malicious agents.

**Examples:**
- **Microsoft Agent Framework (full_isolation)**: Complete isolation
- **Academy (full_isolation)**: Security-focused
- **AutoGen (filesystem_restricted)**: Can't access arbitrary files
- **Most frameworks (none)**: No isolation

**Trade-offs:**
- None: Full capability but high risk
- Network restricted: Safer but can't call APIs
- Filesystem restricted: Can't access sensitive files
- Full isolation: Maximum safety but setup complexity

---

## 9. Models - Provider Configuration

**Question:** *What's under the hood and how flexible is it?*

### 9.1 supported_providers

**What it measures:** Which LLM API providers can be used.

**Possible values:** List of provider names:
- `openai` - OpenAI API
- `anthropic` - Claude API
- `azure` - Azure OpenAI
- `google` - Gemini API
- `huggingface` - HuggingFace models
- `local` - Local/self-hosted models
- `custom` - Custom providers

**Why it matters:** Determines vendor lock-in and model choice flexibility.

**Examples:**
- **LangChain**: openai, anthropic, azure, google, huggingface, local, custom (most flexible)
- **AutoGPT**: openai only (vendor lock-in)
- **Academy**: custom/none (traditional compute, not LLM-centric)

**Trade-offs:**
- Single provider: Simple but locked in
- Multiple providers: Flexible but more configuration
- Custom support: Maximum flexibility but implementation work

---

### 9.2 model_routing

**What it measures:** Ability to route different tasks to different models.

**Possible values:** `true` or `false`

**Why it matters:** Optimize cost vs. capability trade-off.

**Examples:**
- **LangGraph (true)**: Different models per node
- **Microsoft Agent Framework (true)**: Task-specific routing
- **AutoGPT (false)**: Single model for all tasks

**Trade-offs:**
- With routing: Optimal cost/quality but complexity
- Without routing: Simple but suboptimal
- Can save 10-100x cost for appropriate routing

---

### 9.3 fallback_models

**What it measures:** Can switch to backup model if primary fails.

**Possible values:** `true` or `false`

**Why it matters:** Resilience to provider outages.

**Examples:**
- **LangGraph (true)**: Cascade through model list
- **LangChain (true)**: Fallback configuration
- **AutoGPT (false)**: Single model only

**Trade-offs:**
- With fallback: Resilient but different behaviors
- Without fallback: Consistent but fragile
- Important for production systems

---

### 9.4 parameter_control

**What it measures:** Granularity of model parameter configuration.

**Possible values:**
- `none` - Uses defaults
- `basic` - Temperature, max tokens
- `advanced` - Full parameter control
- `per_task` - Different params per task

**Why it matters:** Optimization of quality, cost, and behavior.

**Examples:**
- **LangChain (advanced)**: Full control of all parameters
- **Semantic Kernel (advanced)**: Fine-grained tuning
- **AutoGen (basic)**: Limited parameter access
- **Academy (none)**: Not LLM-focused

**Trade-offs:**
- None: Simple but suboptimal
- Basic: Good enough for most cases
- Advanced: Optimal but overwhelming
- Per-task: Maximum flexibility but complex

---

### 9.5 provider_abstraction

**What it measures:** How well the framework abstracts provider differences.

**Possible values:**
- `none` - Direct provider APIs
- `single_provider` - Assumes one provider
- `multi_provider` - Works with multiple but different code
- `pluggable` - Unified interface, swap easily

**Why it matters:** Migration cost and flexibility.

**Examples:**
- **LangChain (pluggable)**: Unified interface for all providers
- **Microsoft Agent Framework (pluggable)**: Provider-agnostic
- **AutoGen (single_provider)**: Assumes OpenAI API
- **CrewAI (multi_provider)**: Multiple supported but different

**Trade-offs:**
- None/Single: Tightly coupled but simple
- Multi-provider: More flexible but still coupled
- Pluggable: Best flexibility but abstraction overhead

---

## 10. Observability - Inspection Hooks

**Question:** *What can you see and monitor?*

### 10.1 logging

**What it measures:** Quality and structure of log output.

**Possible values:**
- `none` - No logging
- `basic` - Print statements
- `structured` - JSON logs with context
- `custom` - Framework-specific logging

**Why it matters:** Essential for debugging and monitoring.

**Examples:**
- **LangGraph (structured)**: Detailed structured logs
- **Microsoft Agent Framework (structured)**: Production-grade logging
- **AutoGen (basic)**: Simple print-based logging
- Some frameworks (none): No built-in logging

**Trade-offs:**
- None: Clean but impossible to debug
- Basic: Simple but hard to parse
- Structured: Excellent for automation but verbose
- Custom: Tailored but requires integration

---

### 10.2 tracing

**What it measures:** Distributed tracing support for agent workflows.

**Possible values:**
- `none` - No tracing
- `basic` - Simple span tracking
- `opentelemetry` - Standard tracing protocol
- `custom` - Framework-specific tracing

**Why it matters:** Critical for understanding complex multi-agent flows.

**Examples:**
- **LangGraph (opentelemetry)**: Full OTel integration
- **Microsoft Agent Framework (opentelemetry)**: Production tracing
- **Semantic Kernel (opentelemetry)**: Full observability
- **AutoGen (none)**: No tracing support

**Trade-offs:**
- None: No visibility into execution flow
- Basic: Better than nothing but limited
- OpenTelemetry: Industry standard, rich tooling
- Custom: Optimized but proprietary

---

### 10.3 metrics

**What it measures:** Quantitative performance metrics collection.

**Possible values:** `true` or `false`

**Why it matters:** Required for performance monitoring and optimization.

**Examples:**
- **Most production frameworks (true)**: Collect metrics
- **Some experimental frameworks (false)**: No metrics
- Typically track: latency, token usage, error rates

**Trade-offs:**
- With metrics: Visibility but storage overhead
- Without metrics: Blind to performance issues
- Essential for production systems

---

### 10.4 debug_mode

**What it measures:** Enhanced debugging capabilities.

**Possible values:** `true` or `false`

**Why it matters:** Speeds up development and troubleshooting.

**Examples:**
- **All major frameworks (true)**: Support debug mode
- Typically enables: verbose logging, state inspection, breakpoints

**Trade-offs:**
- With debug mode: Great for development
- Must disable in production (performance and security)

---

### 10.5 telemetry_export

**What it measures:** Where observability data can be sent.

**Possible values:**
- `none` - No export
- List of targets: e.g., ["langsmith", "azure_monitor", "prometheus"]

**Why it matters:** Integration with monitoring infrastructure.

**Examples:**
- **LangGraph**: langsmith, custom
- **Microsoft Agent Framework**: azure_monitor, application_insights
- **Academy**: prometheus, custom
- **AutoGPT**: none

**Trade-offs:**
- None: Self-contained but isolated
- Specific targets: Integrated but coupled
- Custom: Flexible but requires implementation

---

## 11. Communication Protocols - Standardized Interoperability

**Question:** *Can agents from different frameworks work together?*

### 11.1 mcp_support

**What it measures:** Support for Model Context Protocol (agent-to-tool).

**Possible values:**
- `native` - Built-in, first-class support
- `adapter` - Via wrapper/adapter
- `community` - Community-maintained integration
- `planned` - Announced but not available
- `none` - Not supported

**Why it matters:** Standardized tool/resource access across frameworks.

**Examples:**
- **LangChain (community)**: Community adapters available
- **Microsoft Agent Framework (planned)**: Future support
- **CrewAI (none)**: Proprietary tool system

**MCP Details:**
- Purpose: Connect agents to tools/data sources
- Protocol: JSON-RPC 2.0 over HTTP/stdio
- Adoption: Claude, ChatGPT, VS Code, Cursor

**Trade-offs:**
- Native: Best integration but development cost
- Community: Available but not supported
- None: Framework-specific but no interop

---

### 11.2 a2a_support

**What it measures:** Support for Agent-to-Agent Protocol (multi-agent collaboration).

**Possible values:** Same as mcp_support

**Why it matters:** Enables cross-framework agent collaboration.

**Examples:**
- **Microsoft Agent Framework (native)**: Only framework with native A2A
- **LangGraph (adapter)**: Can be wrapped for A2A
- **Most frameworks (none)**: Proprietary protocols

**A2A Details:**
- Purpose: Agent discovery and collaboration
- Protocol: JSON-RPC 2.0 with task states
- Status: Linux Foundation, SDKs in 5 languages

**Trade-offs:**
- Native: True interoperability but complex
- Adapter: Partial compatibility
- None: Isolated ecosystem

---

### 11.3 primary_protocol

**What it measures:** Main internal communication mechanism.

**Possible values:**
- `mcp` - Uses MCP internally
- `a2a` - Uses A2A internally
- `http_rest` - RESTful HTTP
- `grpc` - gRPC protocol
- `websocket` - WebSocket based
- `custom` - Framework-specific

**Why it matters:** Indicates architecture and integration patterns.

**Examples:**
- **Microsoft Agent Framework (a2a)**: Built on A2A
- **Semantic Kernel (http_rest)**: REST-based
- **LangGraph (custom)**: Internal protocol
- **Academy (custom)**: PubSub-based

**Trade-offs:**
- Standard protocols: Interoperable but generic
- Custom: Optimized but isolated
- REST: Universal but verbose
- gRPC: Fast but less universal

---

### 11.4 transport_mechanisms

**What it measures:** Low-level transport protocols supported.

**Possible values:** List of transports:
- `http` - HTTP/HTTPS
- `stdio` - Standard input/output
- `sse` - Server-Sent Events
- `websocket` - WebSocket
- `grpc` - gRPC
- `pubsub` - Message queue/pub-sub

**Why it matters:** Deployment flexibility and performance characteristics.

**Examples:**
- **LangGraph**: http, sse, grpc (flexible)
- **AutoGen**: stdio (local only)
- **Academy**: pubsub, message_queue (distributed)

**Trade-offs:**
- HTTP: Universal but higher latency
- stdio: Fast but local only
- SSE: Good for streaming but one-way
- WebSocket: Bidirectional but connection management
- gRPC: Fast but requires setup

---

### 11.5 message_format

**What it measures:** Message serialization format.

**Possible values:**
- `json-rpc-2.0` - JSON-RPC 2.0 standard
- `rest` - REST JSON
- `grpc` - Protocol Buffers
- `graphql` - GraphQL queries
- `custom` - Framework-specific

**Why it matters:** Interoperability and debugging.

**Examples:**
- **Microsoft Agent Framework (json-rpc-2.0)**: Standard protocol
- **Semantic Kernel (rest)**: RESTful JSON
- **Most frameworks (custom)**: Proprietary format

**Trade-offs:**
- Standard formats: Interoperable but generic
- Custom: Optimized but requires documentation
- JSON-RPC: Structured but verbose
- Protobuf: Fast but binary (harder to debug)

---

### 11.6 interoperability

**What it measures:** Can communicate with agents from other frameworks.

**Possible values:** `true` or `false`

**Why it matters:** Determines ecosystem lock-in vs. openness.

**Examples:**
- **Microsoft Agent Framework (true)**: A2A enables interop
- **LangGraph (true)**: Flexible architecture
- **Academy (true)**: Federated design
- **Most frameworks (false)**: Isolated ecosystems

**Trade-offs:**
- Interoperable: Flexible but requires standards
- Isolated: Simpler but locked in
- Important for enterprise and multi-vendor scenarios

---

## 12. Requirements - Dependencies

**Question:** *What does it need to run?*

### 12.1 primary_language

**What it measures:** Programming language(s) the framework is built in.

**Possible values:** List of languages:
- `python` - Python
- `javascript` - JavaScript
- `typescript` - TypeScript
- `csharp` - C# / .NET
- `java` - Java
- `go` - Go
- `rust` - Rust

**Why it matters:** Determines developer skills and ecosystem integration.

**Examples:**
- **Most frameworks**: Python (AI/ML ecosystem)
- **Microsoft Agent Framework**: Python, C# (multi-language)
- **Semantic Kernel**: Python, C#, Java (enterprise)

**Trade-offs:**
- Python: Largest AI ecosystem but slower
- TypeScript: Good for web integration
- C#/Java: Enterprise integration
- Multi-language: Flexibility but maintenance burden

---

### 12.2 external_services

**What it measures:** Required external dependencies.

**Possible values:** List of services:
- `llm_api` - LLM provider API
- `vector_db` - Vector database
- `database` - SQL/NoSQL database
- `message_broker` - Message queue
- `docker` - Container runtime
- `distributed_storage` - Distributed file system

**Why it matters:** Operational complexity and cost.

**Examples:**
- **LangChain**: llm_api only (minimal)
- **LlamaIndex**: llm_api, vector_db (data-focused)
- **AutoGen**: llm_api, docker (code execution)
- **Academy**: message_broker, distributed_storage (complex)

**Trade-offs:**
- Fewer dependencies: Easier to deploy
- More dependencies: More capable but complex
- Must account for dependency costs and operations

---

### 12.3 min_memory_mb

**What it measures:** Minimum RAM required.

**Possible values:** Number in megabytes

**Why it matters:** Determines deployment options (serverless, edge, etc.).

**Examples:**
- **Most frameworks**: 256-512 MB (reasonable)
- **Microsoft Agent Framework**: 1024 MB (feature-rich)
- Important for constrained environments

**Trade-offs:**
- Low memory: Can run anywhere but limited features
- High memory: More features but limited deployment options

---

### 12.4 network_required

**What it measures:** Must have internet connectivity.

**Possible values:** `true` or `false`

**Why it matters:** Offline/airgapped deployment scenarios.

**Examples:**
- **All LLM-based frameworks (true)**: Need API access
- Hypothetical local-only: false
- Important for security-sensitive deployments

**Trade-offs:**
- Network required: Access to cloud LLMs but dependency
- Offline capable: Secure and reliable but limited models

---

### 12.5 platform_support

**What it measures:** Operating systems and environments supported.

**Possible values:** List of platforms:
- `linux` - Linux
- `macos` - macOS
- `windows` - Windows
- `cloud` - Cloud platforms
- `edge` - Edge devices

**Why it matters:** Deployment flexibility.

**Examples:**
- **Most frameworks**: linux, macos, windows, cloud (cross-platform)
- **Academy**: linux, cloud, edge (distributed focus)
- Python frameworks generally cross-platform

**Trade-offs:**
- More platforms: Wider applicability but testing burden
- Limited platforms: Simpler but restricted deployment

---

## 13. Performance - Characteristics

**Question:** *How does it perform?*

### 13.1 latency_category

**What it measures:** Typical response time.

**Possible values:**
- `low` - Sub-second responses
- `medium` - 1-5 seconds
- `high` - >5 seconds
- `variable` - Depends on task

**Why it matters:** User experience and use case fit.

**Examples:**
- **Microsoft Agent Framework (low)**: Optimized execution
- **Semantic Kernel (low)**: Efficient orchestration
- **Most frameworks (medium)**: Multiple LLM calls
- **AutoGPT (high)**: Many sequential calls

**Trade-offs:**
- Low latency: Better UX but less capable
- High latency: More thorough but poor UX
- Variable: Flexible but unpredictable

---

### 13.2 throughput_category

**What it measures:** Tasks completed per unit time.

**Possible values:**
- `low` - <10 tasks/hour
- `medium` - 10-100 tasks/hour
- `high` - >100 tasks/hour
- `variable` - Depends on parallelization

**Why it matters:** Batch processing and scaling capabilities.

**Examples:**
- **LangGraph (high)**: Parallel execution
- **Microsoft Agent Framework (high)**: Concurrent tasks
- **AutoGen (low)**: Sequential conversations

**Trade-offs:**
- High throughput: Good for batch but resource intensive
- Low throughput: Simpler but slow for scale
- Depends on parallelization and async support

---

### 13.3 token_efficiency

**What it measures:** Tokens used per task.

**Possible values:**
- `low` - Wasteful, many unnecessary tokens
- `medium` - Reasonable efficiency
- `high` - Optimized, minimal tokens
- `variable` - Depends on task

**Why it matters:** Direct impact on cost.

**Examples:**
- **Academy (high)**: Minimal LLM use
- **Microsoft Agent Framework (high)**: Optimized prompts
- **AutoGPT (low)**: Many verbose calls
- **CrewAI (low)**: Conversational overhead

**Trade-offs:**
- High efficiency: Cheaper but may sacrifice capability
- Low efficiency: More capable but expensive
- 10x difference common between frameworks

---

### 13.4 cost_category

**What it measures:** Typical cost per task.

**Possible values:**
- `low` - <$0.01 per task
- `medium` - $0.01-$0.10 per task
- `high` - >$0.10 per task
- `variable` - Depends on configuration

**Why it matters:** Economic viability at scale.

**Examples:**
- **Academy (low)**: Traditional compute, minimal LLM
- **Most frameworks (medium)**: Reasonable LLM usage
- **AutoGPT (high)**: Many expensive calls
- **CrewAI (high)**: Multiple agents, many calls

**Trade-offs:**
- Low cost: Economical at scale but limited AI capability
- High cost: Maximum capability but not scalable
- Must balance cost vs. value delivered

---

### 13.5 benchmarked

**What it measures:** Has published performance benchmarks.

**Possible values:** `true` or `false`

**Why it matters:** Objective performance data vs. estimates.

**Examples:**
- **LangGraph (true)**: Published benchmarks
- **Microsoft Agent Framework (true)**: Performance data available
- **Academy (true)**: Research benchmarks
- **Most frameworks (false)**: No public benchmarks

**Trade-offs:**
- With benchmarks: Objective data but may be synthetic
- Without benchmarks: Flexibility but no validation
- Benchmarks rare in this space (as of 2026)

---

## Using This Guide

### For Framework Selection

1. **Identify must-haves** in each dimension
2. **Rank dimensions** by importance to your use case
3. **Compare frameworks** using this guide
4. **Weigh trade-offs** for your specific context

### For Framework Development

1. **Use as checklist** for complete design
2. **Make conscious choices** for each attribute
3. **Document decisions** in your "agent card"
4. **Consider implications** across dimensions

### For Research

1. **Identify patterns** across frameworks
2. **Spot gaps** and opportunities
3. **Track evolution** over time
4. **Compare approaches** systematically

---

## Key Insights

### Most Critical Dimensions for Production
1. **Resilience** - Must handle failures gracefully
2. **Boundaries** - Security is non-negotiable
3. **Observability** - Must be able to debug
4. **Control** - Need appropriate autonomy guardrails

### Most Variable Across Frameworks
1. **Structural** - Vastly different architectures
2. **Reasoning** - Different cognitive approaches
3. **Communication Protocols** - Fragmented standards
4. **Performance** - Orders of magnitude differences

### Most Commonly Overlooked
1. **Sandboxing** - 6/9 frameworks have none
2. **Checkpointing** - 5/9 frameworks lack this
3. **Input validation** - Often just basic type checking
4. **Circuit breakers** - Rare but important

---

## Glossary

- **Agent**: An AI system that can perceive, reason, and act autonomously
- **Chain**: Sequence of operations, typically LLM calls
- **Checkpoint**: Saved state that can be restored
- **Circuit breaker**: Pattern that stops calling failing services
- **CoT (Chain of Thought)**: Step-by-step reasoning pattern
- **Federated**: Distributed with local autonomy
- **ReAct**: Reason-Act-Observe loop pattern
- **Sandboxing**: Isolated execution environment
- **Token**: Unit of text for LLM (roughly 4 characters)
- **ToT (Tree of Thoughts)**: Exploring multiple reasoning paths

---

## 14. Data & Retrieval - RAG Capabilities

**Question:** *How does the framework integrate with and retrieve external data?*

### 14.1 vector_store_support

**What it measures:** How the framework integrates with vector databases.

**Possible values:**
- `native` - Built-in vector store integration
- `adapter` - Through adapters/plugins
- `none` - No vector store support

**Why it matters:** Native support means the framework was designed with retrieval in mind. Adapter support means you can add RAG, but it's not the primary focus.

**Examples:**
- **LlamaIndex (native)**: Built-in vector store integration
- **LangChain (native)**: First-class RAG support
- **LangGraph (adapter)**: Through LangChain ecosystem
- **Academy (none)**: No vector store support

**Trade-offs:**
- Native: Optimized integration but can bias toward data-centric use cases
- Adapter: Flexible but extra integration work
- None: Simpler but no RAG capabilities

---

### 14.2 supported_vector_stores

**What it measures:** List of specific vector databases supported.

**Possible values:** List of vector database names (e.g., ["chroma", "pinecone", "weaviate"])

**Why it matters:** More options = less vendor lock-in. Broad support indicates maturity in the data/retrieval space.

**Examples:**
- **LlamaIndex**: chroma, pinecone, weaviate, faiss, qdrant, milvus, pgvector, elasticsearch
- **LangChain**: chroma, pinecone, weaviate, faiss, qdrant, milvus, pgvector
- **CrewAI**: chroma, pinecone
- **Academy**: none

**Trade-offs:**
- More stores: Less vendor lock-in but more maintenance
- Fewer stores: Simpler but potential lock-in
- None: No RAG capability

---

### 14.3 data_connector_count

**What it measures:** Number of data source connectors available.

**Possible values:**
- `0` - No connectors
- `1-10` - Basic set (common file types)
- `10-50` - Moderate (databases, APIs)
- `50+` - Extensive (cloud storage, specialized sources)
- `100+` - Comprehensive ecosystem

**Why it matters:** Reflects how easily you can ingest data from diverse sources. Critical for enterprise use cases with varied data silos.

**Examples:**
- **LlamaIndex (100+)**: Comprehensive connector ecosystem
- **LangChain (100+)**: Extensive data source support
- **Semantic Kernel (10-50)**: Good enterprise coverage
- **CrewAI (1-10)**: Basic connectors
- **Academy (0)**: No data connectors

**Trade-offs:**
- More connectors: Enterprise-ready but larger attack surface
- Fewer connectors: Simpler but limited integration
- Zero connectors: Not designed for data integration

---

### 14.4 connector_types

**What it measures:** Types of data sources supported.

**Possible values:** List containing:
- `files` - PDFs, docs, text, JSON, CSV
- `databases` - SQL, NoSQL, graph databases
- `apis` - REST APIs, GraphQL, custom protocols
- `web` - Web scraping, sitemap crawling
- `cloud_storage` - S3, Azure Blob, GCS

**Why it matters:** Different use cases require different source types. Web scraping for public knowledge, database connectors for internal data, API connectors for real-time feeds.

**Examples:**
- **LlamaIndex**: files, databases, apis, web, cloud_storage (comprehensive)
- **LangChain**: files, databases, apis, web, cloud_storage (comprehensive)
- **Semantic Kernel**: files, databases, apis, cloud_storage (enterprise-focused)
- **CrewAI**: files, apis (basic)

**Trade-offs:**
- More types: Versatile but complex
- Focused types: Optimized for specific use cases
- No types: Not data-centric

---

### 14.5 retrieval_strategies

**What it measures:** Methods for searching and retrieving information.

**Possible values:** List containing:
- `dense` - Semantic search via embeddings
- `sparse` - Keyword/BM25 search (traditional IR)
- `hybrid` - Dense + sparse combined
- `reranking` - Re-score results with secondary model
- `multi_query` - Generate multiple query variations
- `parent_document` - Retrieve summaries, return full docs
- `hypothetical` - HyDE (generate hypothetical answer, search for it)

**Why it matters:** Advanced strategies improve retrieval quality. Simple dense-only search often misses relevant results. Hybrid and reranking significantly boost accuracy.

**Examples:**
- **LlamaIndex**: dense, sparse, hybrid, reranking, multi_query, parent_document, hypothetical (most comprehensive)
- **LangChain**: dense, sparse, hybrid, reranking, multi_query (advanced)
- **Semantic Kernel**: dense, sparse, hybrid (solid)
- **CrewAI**: dense (basic)

**Trade-offs:**
- Multiple strategies: Better quality but complexity
- Single strategy: Simpler but limited quality
- Advanced strategies: Higher quality but more expensive

---

### 14.6 chunking_support

**What it measures:** How documents are split for indexing.

**Possible values:**
- `none` - No chunking capabilities
- `basic` - Fixed-size chunks (e.g., 500 tokens)
- `advanced` - Semantic chunking, recursive splitting, overlap control

**Why it matters:** Bad chunking destroys retrieval quality. Advanced chunking preserves semantic coherence, handles varied document structures, and maintains context.

**Examples:**
- **LlamaIndex (advanced)**: Semantic chunking, recursive splitting
- **LangChain (advanced)**: Multiple chunking strategies
- **Semantic Kernel (basic)**: Fixed-size chunks
- **CrewAI (basic)**: Simple chunking
- **Academy (none)**: No chunking

**Trade-offs:**
- Advanced: Better retrieval quality but complex
- Basic: Simple but can break semantic units
- None: No RAG capability

---

### 14.7 embedding_support

**What it measures:** How text is converted to vectors.

**Possible values:**
- `native` - Framework generates embeddings
- `bring_your_own` - Must provide pre-computed embeddings
- `both` - Supports both modes

**Why it matters:** Native embedding support simplifies implementation. "Bring your own" offers flexibility but adds complexity.

**Examples:**
- **LlamaIndex (both)**: Can generate or accept embeddings
- **LangChain (both)**: Flexible embedding options
- **Semantic Kernel (native)**: Built-in embedding generation
- **CrewAI (native)**: Generates embeddings

**Trade-offs:**
- Native: Simple but less control
- Bring your own: Flexible but more work
- Both: Maximum flexibility

---

### 14.8 query_transformation

**What it measures:** Can the system modify queries before retrieval?

**Possible values:** `true` or `false`

**Why it matters:** User queries are often poorly formed. Transformation significantly improves retrieval quality without changing the data.

**Transformations include:**
- Query expansion (add synonyms)
- Query decomposition (break complex queries into sub-queries)
- Query rewriting (rephrase for better results)
- Hypothetical document generation

**Examples:**
- **LlamaIndex (true)**: Advanced query transformation
- **LangChain (true)**: Query rewriting and expansion
- **Semantic Kernel (true)**: Query optimization
- **CrewAI (false)**: No transformation
- **Academy (false)**: No retrieval

**Trade-offs:**
- With transformation: Better results but more LLM calls
- Without transformation: Simpler but lower quality

---

### 14.9 retrieval_mode

**What it measures:** Is retrieval a simple step or an agentic process?

**Possible values:**
- `simple` - Single-step retrieval (query → results)
- `agentic` - Multi-step with reasoning (plan → retrieve → evaluate → retrieve again)
- `both` - Supports both patterns

**Why it matters:** This is the key distinction between "RAG framework" and "agentic framework that does RAG":
- **Simple mode**: Traditional RAG
- **Agentic mode**: Self-RAG, corrective RAG, adaptive retrieval

**Examples:**
- **LlamaIndex (both)**: Simple retrieval or agentic agents
- **LangChain (both)**: Traditional RAG or agent-based retrieval
- **LangGraph (both)**: Configurable per workflow
- **CrewAI (simple)**: Basic retrieval only
- **Semantic Kernel (simple)**: Single-step retrieval

**Trade-offs:**
- Simple: Fast and predictable but limited
- Agentic: Better quality but expensive and complex
- Both: Maximum flexibility

---

*Last updated: May 21, 2026*
*Based on framework versions as of last_updated dates in profiles*
