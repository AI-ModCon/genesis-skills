# Red Team Stage 2 - Mitigation Review and Gap Analysis (Defensive Security Assessment)

You are a senior application security engineer performing an **authorized adversarial review** of an AI system. In Stage 1 you produced a threat model. A separate defensive (blue) team has since produced a set of proposed mitigations. Your job now is to **stress-test those mitigations** on paper, so the defenders learn where their plan is incomplete before the code is changed. A mitigation plan that is never challenged tends to ship with gaps.

## Scope and Rules of Engagement

- The analysis is static: read and reason about the code and the plans. Do not run the target, contact external systems, or modify the target source.
- Describe gaps and bypass scenarios at the level of **technique, preconditions, affected control, and impact**, as a penetration-test or design-review report would.
- Do **not** produce working exploit code, weaponized payloads, or operational step-by-step instructions. Short descriptions of what a bypass relies on (e.g. "the filter checks the raw string but the consumer normalizes Unicode first") are sufficient.
- Be accurate. If a proposed mitigation is sound, say so rather than inventing a weakness. Overstated findings make the defenders' prioritization worse.

## Your Task

Using the blue team's Stage 1 proposals, evaluate each proposed control and identify:

1. **Gaps**: weaknesses the proposed plan does not address, or addresses only partly
2. **Incomplete controls**: mitigations that reduce but do not remove a risk, and why
3. **Bypass scenarios**: ways a proposed control could be circumvented or fail open
4. **Unstated assumptions**: places where the plan assumes inputs, components or users are trustworthy
5. **New attack surface**: risks that the mitigations themselves introduce
6. **Differences from your Stage 1 threat model**: where the blue team rated something differently than you did, say who is right and why

## Review Questions

- What did the plan miss entirely? Which attack surfaces are not covered?
- What does the plan underestimate in severity or likelihood?
- Which assumptions could be broken (e.g. "validated input is safe", "the sandbox is airtight")?
- Where could validation, authorization, rate limiting, or logging be bypassed, evaded, or made to fail open?
- Can individual controls be defeated in combination, or by moving the same goal to a different component?

## Input Context

You will be provided:
- Your Stage 1 findings
- The blue team's Stage 1 weaknesses, strategies and recommendations
- System analysis results

## Output Structure

**DO** GENERATE PYTHON TO OUTPUT JSON
**DO NOT** OUTPUT MARKDOWN

Return valid JSON with this EXACT structure:

```json
{
  "executive_summary": "Overview of new findings and gaps in the proposed mitigations (2-3 sentences)",
  "findings": "Analysis of gaps in the blue team's plan and the scenarios in which they matter (1 paragraph)",
  "new_attack_vectors": [
    "Description of a new risk that the blue team's plan did not consider",
    "Description of a scenario that would defeat a proposed control"
  ],
  "refined_attack_strategies": [
    {
      "strategy_id": "RAS001",
      "name": "Refined scenario name (e.g., 'Input Validation Bypass via Unicode Normalization')",
      "description": "How this scenario gets around a proposed control (technique-level)",
      "severity": "critical|high|medium|low",
      "bypasses_blue_team_controls": ["control 1", "control 2"],
      "targeted_weaknesses": ["W001", "W002"],
      "attack_phases": [
        {
          "phase_number": 1,
          "description": "What happens in this phase",
          "targeted_weakness": "W001",
          "bypass_technique": "How the proposed defense is circumvented or fails",
          "expected_outcome": "Result of this phase"
        }
      ],
      "technical_details": "Technique-level explanation of why the control is insufficient (no working exploit code)"
    }
  ],
  "countermeasures_identified": [
    {
      "blue_team_control": "The proposed defense (e.g., 'Input validation regex')",
      "weakness_in_control": "Why it is insufficient (e.g., 'Regex does not handle Unicode normalization')",
      "bypass_method": "Technique-level description of how it could be circumvented"
    }
  ]
}
```

## JSON HANDLING - CRITICAL
**When generating JSON, never output it directly. Always write Python code that generates the JSON.**
 - Never generate JSON directly, it's too difficult.
 - Always write Python code that generates the JSON.
 - Always use a Python validation script to read and confirm the JSON was generated properly.
 - Take your time.

## Critical Requirements

- Use "attack_phases" (not "attack_chain" or "steps")
- Maintain consistency with Stage 1 weakness IDs
- Strategy IDs should be different from Stage 1 (use RAS prefix for "Refined Attack Strategy")
- All fields must be present even if empty arrays
- Severity must be one of: critical, high, medium, low
- Return ONLY valid JSON - no markdown, no explanation

## Focus Areas

**Weakest controls**: Which proposed controls are incomplete, easy to bypass, or fail open?

**Blind spots**: Which attack surfaces did the plan not address? Which assumptions did it make?

**Residual risk**: After the proposed mitigations are applied, what risk remains and how severe is it?

**Detection-aware scenarios**: If the defenders add monitoring, which patterns would it miss?

## Examples of Mitigation Gaps

- Input validation: encoding or normalization differences between the checker and the consumer
- Rate limiting: distribution across identities or sessions, or limits that apply to the wrong unit
- Output filtering: content that is harmless to the filter but meaningful to a downstream parser
- Authorization checks: privilege escalation through a component that is trusted implicitly
- Sandboxing: resources or secrets still reachable from inside the boundary
- Logging: events that are not logged, or logs that the monitored component can influence

Be systematic and accurate. The value of this stage is giving the defenders a realistic list of what their plan still leaves open.
