# Standard Categorical Values

This document defines the standardized categorical values used across all evaluation JSON files. These values are used consistently without parentheticals or explanatory text.

## Modalities

Standard values for `multimodal_support.modalities`:

- `Text`
- `Images`
- `Audio`
- `Video`
- `Code`
- `Tables`
- `Documents`
- `Structured data`

## Chunking Strategies

Standard values for `chunking_strategies.strategies`:

- `Fixed-size`
- `Sentence-based`
- `Paragraph-based`
- `Semantic chunking`
- `Recursive chunking`
- `Token-aware`
- `Sliding window`
- `Context-preserving`
- `Hierarchical chunking`
- `Markdown-aware`
- `Code-aware`
- `Document-aware`
- `Custom`
- `Automatic`

## Agent/Tool Capabilities

Standard values for `agent_tool_support.capabilities`:

- `Native agent framework`
- `Tool calling`
- `Function calling`
- `Memory management`
- `Conversational memory`
- `Planning`
- `Reasoning`
- `Multi-agent orchestration`
- `Multi-agent conversations`
- `Callbacks`
- `Streaming`
- `Code interpreter`
- `File search`
- `Plugin system`
- `Planner`
- `Pipeline orchestration`
- `Basic RAG retrieval`
- `Query engines`
- `Search tool`
- `Custom tools`
- `API connections`
- `Human-in-the-loop`
- `Code execution`
- `Teachability`
- `Nested chats`
- `Group chat`
- `Retrieval agents`
- `Slack bot`
- `Persistent memory`
- `Thread-based conversations`
- `Memory connectors`
- `Basic query-response`
- `N/A`

## Prompt Management Features

Standard values for `prompt_management.features`:

- `Template system`
- `Prompt templates`
- `Prompt versioning`
- `Prompt tracking`
- `Few-shot examples`
- `Few-shot example management`
- `Prompt optimization`
- `Prompt testing`
- `Variable substitution`
- `System instructions`
- `Semantic functions`
- `Prompt rendering`
- `Dynamic prompting`
- `System message templates`
- `Per-assistant configuration`
- `Persona-based prompts`
- `Custom prompts`
- `Configurable prompts`
- `Basic templates`
- `N/A`

## Query Efficacy - Speed Features

Standard values for `query_efficacy.speed_features`:

- `Caching`
- `Streaming`
- `Streaming responses`
- `Async support`
- `Async`
- `Async pipelines`
- `Batch processing`
- `Local inference optimization`
- `Managed infrastructure`
- `Auto-scaling`
- `Background indexing`
- `Query optimization`
- `Index optimization`
- `Weaviate optimization`
- `N/A`

## Query Efficacy - Accuracy Features

Standard values for `query_efficacy.accuracy_features`:

- `Hybrid search`
- `Reranking`
- `Query understanding`
- `Query transformation`
- `Context compression`
- `Semantic search`
- `Metadata filtering`
- `Permission-aware search`
- `Boost rules`
- `Decay rules`
- `Document filtering`
- `Automatic citation`
- `Query optimization`
- `Multi-agent refinement`
- `Context filtering`
- `Response synthesis`
- `Response synthesis modes`
- `Memory search`
- `Semantic ranking`
- `N/A`

## Advanced Features

Standard values for `advanced_features.features`:

- `Hybrid search`
- `Reranking`
- `Metadata filtering`
- `Multi-tenancy`
- `Multi-tenancy support`
- `Streaming`
- `Streaming responses`
- `Citation tracking`
- `Evaluation framework`
- `Query understanding`
- `Query transformation`
- `Context compression`
- `Context optimization`
- `Document versioning`
- `Document loaders`
- `Self-querying retrievers`
- `Router query engines`
- `Graph-based retrieval`
- `Permission-aware filtering`
- `Connector ecosystem`
- `Document-level permissions`
- `Query analytics`
- `Integration marketplace`
- `API access`
- `Collaboration features`
- `Custom pipeline components`
- `Document preprocessing`
- `Multiple retrievers`
- `Multi-file support`
- `Thread persistence`
- `Code execution`
- `File annotations`
- `Vector store management`
- `Multi-LLM support`
- `Multiple LLM support`
- `Custom embeddings`
- `UI-based configuration`
- `Synthetic test data generation`
- `LLM-as-judge evaluation`
- `Answer correctness scoring`
- `Aspect critique`
- `Evaluation metrics`
- `Memory stores`
- `Plugin ecosystem`
- `Kernel filters`
- `Slack/Teams integration`
- `N/A`

## Usage Guidelines

1. **Categorical values MUST NOT include:**
   - Parenthetical explanations: ~~`"Text (primary)"`~~ → `"Text"`
   - Numbers/counts: ~~`"Tool calling with 100+ integrations"`~~ → `"Tool calling"`
   - Qualifiers: ~~`"Images (via CLIP)"`~~ → `"Images"`
   - Implementation details: ~~`"Audio (transcription)"`~~ → `"Audio"`

2. **All explanatory information goes in:**
   - Top-level `commentary` field (one per JSON file)
   - Nested `note` fields (deprecated, use commentary instead)
   - `unified_modalities` and `separate_modalities` arrays

3. **Consistency:**
   - Use exact case-sensitive matches from standard lists above
   - Prefer specific terms over generic (e.g., "Streaming responses" > "Streaming" when about responses)
   - Use singular form unless plural is conventional ("Few-shot examples")

## Processing Guidelines

When evaluating a new system:

1. Identify supported capabilities/features
2. Map to standard categorical values (exact match)
3. If no match exists, add to standards list
4. Place all explanatory details in `commentary` field
5. Use `unified_modalities` / `separate_modalities` to clarify multimodal support

This ensures JSON files are machine-parseable and can be programmatically compared.
