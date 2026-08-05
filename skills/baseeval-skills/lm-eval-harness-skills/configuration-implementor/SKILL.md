---
name: configuration-implementor
description: Creates the YAML file and associated utils.py code to define the benchmark configuration. Use this skill after the completion of the data-exploration skill.
---

# Steps

1. Read `tasks/{benchmark_name}/plan.md` to understand the configuration design.
2. Read the documentation in `references/*.md` as needed to confirm the required YAML/task structure.
3. Read `assets/examples/README.md`, then inspect the most relevant example subdirectories under `assets/examples/` for patterns that match this benchmark.
4. Based on the plan, the documentation, and the example configurations, create the YAML file in `tasks/{benchmark_name}/`.
5. If necessary, create `tasks/{benchmark_name}/utils.py` for supporting Python functions.
6. Keep simple prompt formatting and declarative transforms in YAML when possible; move only non-trivial logic into `utils.py`.
7. Document your implementation choices by appending an **Implementation Decision Log** section to `plan.md`:
   ```markdown
   ## Implementation Decision Log
   
   **Date**: <date>
   
   **Implementation Choices**:
   - Choice 1: <what you chose> - **Why**: <rationale> - **Alternative considered**: <what else was possible>
   - Choice 2: <what you chose> - **Why**: <rationale>
   
   **Tradeoffs**:
   - Tradeoff 1: <description> - **Impact**: <what this means for users>
   
   **Known Limitations**:
   - Limitation 1: <what doesn't work or isn't supported> - **Workaround**: <if any>
   ```
8. Provide a concise implementation summary and ask the user for concurrence before proceeding to testing.
