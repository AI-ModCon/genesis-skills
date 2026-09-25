---
name: datacard-generator
description: "Generate Genesis Mission Datacard v1.2 documentation for scientific datasets by introspecting a directory and filling the structured template. Use when the user asks to create a datacard, dataset card, dataset documentation, dataset metadata, document a dataset, or prepare a dataset for sharing. Supports six capability dimensions (discoverability, accessibility, interoperability, reusability, governed_use, ai_usability) — pick which ones apply via `supports_*` flags. Also converts MODCON v1 datacards to Genesis v1.2."
allowed-tools: Bash(*) Read WebSearch WebFetch
---

# Generating Datacards

Generate a Genesis Mission Datacard v1.2 by introspecting a dataset
directory and filling both the YAML frontmatter and the markdown narrative
body of the canonical template, prompting the user for fields that
introspection can't infer.

The skill also has a one-shot **Convert** path for migrating an existing
MODCON v1 datacard to Genesis v1.2.

**Validation is upstream's `linkml-validate`** against the vendored schema
(`scripts/genesis_datacard.yaml`); this skill ships no validator. Rules
the schema cannot express are eye checks (`references/validation-rules.md`).

## Workflow

Copy this checklist and check off steps as you go.

```
Progress:
- [ ] 1. Gather context (dataset_path now; `supports_*` capabilities after step 2, with evidence)
- [ ] 2. Run python3 scripts/introspect.py on the dataset directory
- [ ] 3. Load capability-specific guidance
- [ ] 4. Auto-fill YAML from introspect output
- [ ] 5. Confirm dataset readiness level with the user (optional)
- [ ] 6. Prompt for remaining required fields in batches
- [ ] 7. Cross-check every ORCID/ROR/DOI/OSTI identifier via live APIs
- [ ] 8. Compute filename and write the datacard (YAML + markdown body)
- [ ] 9. Validate with linkml-validate
- [ ] 10. Address findings; re-validate
- [ ] 11. Present review summary
```

### 1. Gather context

**Ask for the dataset path now.** Do not answer the capability questions
below cold — first run step 2 (introspect), then come back and propose
each `supports_*` answer with evidence from what introspection found.

- **Dataset path** — directory to document. Ask for this now.
- **Which capabilities does this dataset support?** (after step 2 — see
  the note at its end). Genesis v1.2 has six capability containers.
  Propose a default for each, backed by an introspection finding, and ask
  the user to confirm Yes/No:
  - `supports_discoverability` — **always Yes** (schema enforces this). Identification, description, project, release status, contacts, authorship. Minimum core fields.
  - `supports_accessibility` — Yes if the dataset is meant to be accessed/shared. Adds access policy, endpoints, dataset scale.
  - `supports_interoperability` — Yes if the dataset uses standard formats, structured features, controlled vocabularies, or has documented provenance. Adds data_structure, dates, semantic_layer, provenance, related_resources.
  - `supports_reusability` — Yes if the dataset is licensed for downstream use. Adds license, citation, integrity, stewardship, data_quality.
  - `supports_governed_use` — Yes if the dataset has access restrictions, PII, export control, or formal review requirements. Adds use_governance, security/sensitivity blocks, compliance, review_provenance_companion.
  - `supports_ai_usability` — Yes if the dataset is suitable for AI/ML training, inference, or evaluation. Adds ai_usage policy block.

Each `supports_X = Yes` triggers a required `X` block in the YAML and a corresponding set of required fields. Each `supports_X = No` omits that block entirely.

### 2. Introspect the directory

Run `python3 scripts/introspect.py <dataset_path>` and capture the JSON. See
[references/introspection-commands.md](references/introspection-commands.md) for
what each output field means.

**Now return to the capability questions from step 1.** Propose an answer
for each `supports_*` flag backed by an introspection finding — e.g., "I
found a LICENSE file and CITATION.cff → I recommend
`supports_reusability=Yes`. No `train/`/`test/` splits detected →
`supports_ai_usability` optional." Confirm each with the user
([Yes/No]) before moving on to step 3.

### 2b. Resolve the DOI first (fast path)

**If introspection or the user surfaced a DOI, resolve it now** — one
request yields title, abstract, authors with ORCIDs/affiliations,
keywords, publisher, funding, often the OSTI ID. Follow § "Order of
operations: DOI first" and § DOI (incl. the **provenance gate** — a README
DOI is often a cited paper, not this dataset) in
`references/live-enrichment.md`. Carry the result into step 4 and present
it as one table. No DOI? Skip to step 3.

### 3. Load capability-specific guidance

Read `references/capability-prompts.md` (the per-capability prompt sequence).

For deep field-by-field explanation, load the relevant section of
`references/genesis_field_guide.md` only as needed (the file is large).

### 4. Auto-fill the data card

**The template is the field reference, not a skeleton to copy** — ~130KB
/ ~35K tokens of commented guidance, none of which belongs in a finished
card. Never read it whole. Read only the section you need:

```bash
# Absolute path from the skill root; works from any cwd.
sed -n 'START,ENDp' <skill_root>/references/genesis_v1.0_template.md
```

Write the card directly, in template key order, with only the blocks the
`supports_*` flags turn on. Step 9 proves nothing required is missing.

**Where to save:** inside `<dataset_dir>/` by default; ask if the user
prefers elsewhere. Compute the filename via the Filename rule (§8 below).

Populate the YAML frontmatter using this decision table. A DOI record
from step 2b takes precedence over README/CITATION.cff for every field in
`references/live-enrichment.md` § "What to extract".

| Genesis field | Auto-fill if… | Otherwise |
|---|---|---|
| `discoverability.datacard.created_date` | always (today, ISO 8601) | — |
| `discoverability.datacard.updated_date` | `if_applicable` — leave blank on initial creation; only set on subsequent edits (see Gotcha below) | — |
| `discoverability.datacard.creation_method` | always → `"Hybrid"` (Title case in v2) | — |
| `discoverability.datacard.template_version` | always → `"1.2"` (matches the vendored schema/template version) | — |
| `discoverability.datacard.change_log[0]` | always (`change_date`, `datacard_version: "1.2"`, "Initial creation" or "Converted from MODCON v1") | — |
| `discoverability.datacard.filename` | computed from `discoverability.identification.name` (see Filename rule below) | — |
| `discoverability.datacard.language` | always → `en` (override if README is non-English) | — |
| `discoverability.datacard.created_by[]` | always (AI model first if Hybrid; see `references/gotchas.md`) | — |
| `discoverability.identification.name` | from README / CITATION.cff title | prompt |
| `discoverability.identification.version` | from CITATION.cff or default `"1.0"` | prompt |
| `discoverability.product_type` | never — `ProductTypeEnum` (see `references/lookup-tables.md`) | always prompt |
| `discoverability.datacard.id` | never — `IdentifierClass` (`{type: local, value: <slug>}` for pre-publication is a sensible default) | prompt |
| `discoverability.dataset_description.dataset_summary` | from README first paragraph | prompt |
| `discoverability.dataset_description.keywords` | from README / CITATION.cff | prompt |
| `interoperability.data_structure.formats` | introspect.py `formats` | prompt (requires `supports_interoperability=Yes`) |
| `interoperability.data_structure.features` | introspect.py `sample_columns` (structured form: `- name: x` objects) | prompt |
| `interoperability.data_structure.splits` | introspect.py `splits_detected` | leave empty |
| `accessibility.dataset_scale.record_count` / `.compressed_bytes` | introspect.py | prompt (requires `supports_accessibility=Yes`) |
| `reusability.license.spdx_id` | introspect.py `license_hint` | prompt (requires `supports_reusability=Yes`) |
| `reusability.license.name` | never | prompt whenever the `reusability.license` block is emitted (required always, not just when `spdx_id=other`) |
| `discoverability.authors[]` | from CITATION.cff (use **CRediT roles** — see `references/lookup-tables.md`) | prompt |
| `reusability.citation.preferred_citation` | from CITATION.cff bibtex | prompt at `[pub]` |
| `interoperability.provenance.was_generated_by` | always prompt (often forgotten) | — |
| `discoverability.dataset_description.science_domain` | never auto-filled — closed `ScienceDomainEnum` (see `references/lookup-tables.md`) | prompt |
| `ai_usability.ai_usage.training_use_status` / `.inference_use_status` / `.evaluation_use_status` | never auto-filled | prompt (`Yes \| No \| Conditional`); if `Conditional`, also prompt for the matching `*_use_conditions` free-text field |
| `_repository.*` | **NEVER** — system-owned | — |

For each `supports_X=Yes`, also write `supports_X: "Yes"` at the top level
of the YAML. The schema enforces that the matching `X:` block must exist
when `supports_X=Yes`.

Identifiers gathered here are **cross-checked live in step 7** — not optional.

### 5. Confirm dataset readiness level (optional)

If the user wants to indicate dataset readiness, ask them to set a level
(1, 2, or 3) as freetext in the datacard narrative. There is no dedicated
`dataset_readiness` YAML field in Genesis v1.2 — readiness is expressed
through the combination of `supports_*` flags that are set to `"Yes"`.

Heuristic (roughly: 1 `supports_*=Yes` → level 1, 2-3 → level 2, ≥4 → level 3):

- 1 = Discoverable (metadata only; `supports_discoverability=Yes` + perhaps `accessibility`)
- 2 = Interoperable & Reusable (also license, contacts, provenance; `supports_interoperability` and `supports_reusability`)
- 3 = AI-Ready & Trustworthy (also semantic layer, integrity, governed use; `supports_ai_usability` or `supports_governed_use`)

Confirm with the user.

### 6. Prompt for missing fields

Present auto-discovered values for confirmation. Then ask for unfilled
required fields. Ask **3-5 at a time** following the batches in
`references/capability-prompts.md`. Stop and confirm after each batch.

**Ask only for what is still empty.** Confirm step 2b values in one table;
a DOI never supplies CRediT `role[]`, `product_type`, `science_domain`,
access/governance decisions, or `provenance.was_generated_by` — still ask.

**Key vocabulary changes in v2** (full list in `references/lookup-tables.md`):

- **CRediT taxonomy** for `authors[]` / `contributors[]` `role[]` — 16 values
  (`Conceptualization`, `Data_Curation`, … `Other`), **multi-valued per
  author**, and the `role[]` lives **inside** the `person` / `organization`
  sub-block (Gotcha #8). Replaces the old `creator | contributor | …` list.
- **Title_Case for all enums** — `Published` not `published`, `Hybrid` not `hybrid`.
- **Sensitivity** uses `OverallSensitivityEnum`, not a tier ladder (Gotcha #2).
- **Yes/No/Conditional** strings (not booleans) for
  `ai_usability.ai_usage.*_use_status` (renamed from `*_use_allowed`) and
  governance Yes/No fields; `Conditional` requires the matching
  `*_use_conditions` free-text field.
- **`science_domain` is a closed enum** (Gotcha #9).

### 7. Cross-check identifiers via live APIs

**Not optional; do not write (step 8) without completing it** —
unverified identifiers silently misattribute authorship, funding, or DOIs.
Resolve EVERY ORCID, ROR, DOI, and OSTI award number — user-provided or
inferred, already populated or not — per `references/live-enrichment.md`
(plain HTTP, no API key; `WebFetch`, `curl`, or equivalent). If step 2b
resolved the DOI, this step **verifies rather than discovers**: confirm
seeded ORCIDs/affiliations, query OSTI by canonical OSTI ID (not a bare
`?doi=` search), and reuse the 2b response instead of re-resolving.

Enrich every path under § "Identifier paths to check" (grouped by
capability, so skip opted-out ones) and classify each outcome as that
section defines (clean match / mismatch / incomplete / does not resolve /
rate-limited). **Widespread network failure** — more than 2-3 consecutive
connection errors (not per-ID 404s) — means stop enrichment, tell the
user, and **mark the datacard as unverified** in the step 11 summary; do
not write with silently unverified identifiers.

Batch the fetches, then present ALL findings as one consolidated table
(§ Batching guidance). Do NOT prompt after each individual lookup.

### 8. Filename + write

**Filename rule:** `genesis_datacard_<snake_case(discoverability.identification.name)>.md`,
where `snake_case` lowercases the name and replaces any non-alphanumeric
run with a single `_`.

**What to write:** a card in the canonical template's structure
(`references/genesis_v1.0_template.md`), with **both halves filled**:

- **YAML frontmatter** — fully populated from the workflow above. Set
  `supports_discoverability: "Yes"` and any other `supports_X: "Yes"` the
  user opted into; omit the corresponding `X:` block (or set
  `supports_X: "No"`) for capabilities the user opted out of.
- **Markdown narrative body** — also fully filled. See
  [references/body-fill-guide.md](references/body-fill-guide.md) for the
  section-by-section mapping.

**Strip all placeholder markup before saving.** No `[!TODO]`, `<REPLACE:>`,
`<INSTRUCTIONS:>`, `<metadata_key:>`, `${VARIABLE}`, or `__VALUE__` tokens
should remain. Verify with:
`grep -E '\[!TODO\]|<REPLACE:|<INSTRUCTIONS:|<metadata_key:|\$\{|__VALUE__' <output_file>`

### 9. Validate

`linkml-validate` takes YAML, so split the frontmatter off first (uv
fetches linkml on demand):

```bash
awk 'NR>1 && /^---$/{exit} NR>1' <written_file> > /tmp/card.yaml
uv run --with linkml linkml-validate \
  -s <skill_root>/scripts/genesis_datacard.yaml \
  -C GenesisDatacardClass /tmp/card.yaml
```

Prints `No issues found`, or one `[ERROR]` per problem naming the JSON
path; exit 1 on failure. Enums: `references/lookup-tables.md`.
**`'dataset_publisher' is a required property` is a known upstream bug** —
real only when `release_status` is `Approved` or `Published`.

### 10. Address findings

Loop steps 6 → 7 → 8 → 9 until the only output left is `No issues found`
(or that publisher line, on an unpublished card). **Do not claim done
with un-addressed errors.** `warn` severity findings can stand
in the review summary but errors must be resolved.

On loop-back to step 7, re-enrich ONLY identifiers changed in this
iteration (§ Re-check-only-changed).

### 11. Review summary

Present:
- Auto-populated fields (count + brief list)
- User-provided fields (count + brief list)
- Empty / `not_applicable` fields (with reason)
- Validator warnings
- Suggestions for improvement (empty optional fields worth filling)

Ask if the user wants to revise any section before finishing.

---

## Convert path (MODCON v1 → Genesis v1.2)

When the user asks to convert an existing MODCON v1 datacard:

1. Run `python3 scripts/convert_v1_to_genesis.py <v1_path> --json` and capture the JSON report. The report has three lists:
   - `mapped` — fields the converter populated.
   - `missing_required` — Genesis fields the converter couldn't map. **Iterate over this list and prompt the user.**
   - `orphans` — v1 fields with no v2 equivalent.
2. After prompting the user for the fields in `missing_required`, **compose
   the final YAML inline** — apply the answered values to the converter's
   `mapped` output. Do NOT rerun `convert_v1_to_genesis.py` after prompts;
   the converter only reads the v1 source and cannot re-integrate user
   answers.
3. Set `discoverability.datacard.creation_method = "Hybrid"`, `template_version = "1.2"`, and ensure
   `change_log[0] = {change_date: today, datacard_version: "1.2", summary: "Converted from MODCON v1"}`.
4. **Fill the markdown body** using `references/body-fill-guide.md`.
5. **Cross-check every identifier via live APIs** (step 7 of the Generate path).
6. **Compute the filename and write the datacard** (step 8 of the Generate path).
7. Run the validator (step 9 of the Generate path).
8. Present the review summary (step 11 of the Generate path).

---

## Gotchas (read before generating)

More in [references/gotchas.md](references/gotchas.md).

1. **`workflow.state` ≠ `release_status`.** Both are needed (under
   `discoverability.workflow.state` and `discoverability.release_status`).
   Recommended alignments are in `references/lookup-tables.md`.

2. **Sensitivity is no longer a tier ladder.** Use
   `OverallSensitivityEnum` (`Public | Unclassified_Uncontrolled | CUI |
   UCNI | Classified | Legacy_Controlled | Mixed | Other_Controlled`) on
   both `discoverability.datacard.sensitivity.overall_sensitivity` (the
   document) and `discoverability.sensitivity.overall_sensitivity` (the
   dataset). These are independent and often differ — never default them
   to match.

3. **`primary_id.type`** is not `doi` before a DOI is minted — use
   `ark`, `local`, or `unregistered`.

4. **`provenance.was_generated_by`** is required (when
   `supports_interoperability=Yes`) and often forgotten. Even a one-line
   answer adds catalog value.

5. **`change_log` is append-only.** On re-runs, add a new entry plus
   `updated_date` bump. Never edit or delete prior entries. The field
   name inside each entry is `datacard_version` (patched locally from an
   upstream typo).

6. **`_repository` is system-owned.** Never populate it.

7. **`supports_discoverability` is always `"Yes"`.** The schema (via
   the schema) enforces this — every Genesis datacard has at least the
   discoverability block.

8. **`role[]` lives INSIDE the agent sub-block, not on the agent entry
   itself.** `AgentClass` (used by `created_by`, `contact`,
   `additional_contacts`, `authors`, `contributors`, `facilities`,
   `related_resources.software|ai_models`) has no top-level `role` slot —
   it is a tagged union of `person` / `organization` / `ai_model` /
   `software`, and each of those four sub-classes carries its own `role[]`
   (CRediT taxonomy). Do **not** write `role:` as a sibling of `person:`.
   Correct shape:
   ```yaml
   - contribution_date: "2026-07-01"
     creator:
       person:
         given_name: "Jane"
         family_name: "Doe"
         role: [Conceptualization, Data_Curation]   # inside person, not sibling
   ```

9. **`science_domain` is a closed, quoted-string-with-spaces enum.**
   `discoverability.dataset_description.science_domain` and
   `interoperability.domain_metadata.science_domain` both use
   `ScienceDomainEnum`, unlike every other enum in the schema which uses
   `Title_Case` / `snake_case` tokens. See `references/lookup-tables.md`
   for the full list. Free text is no longer accepted.

10. **`discoverability.datacard.updated_date` is now `if_applicable`, not
    required.** Leave it blank on initial creation (a datacard that has
    never been updated has nothing to report). Only set it when performing
    a genuine update to an existing datacard, alongside a new `change_log`
    entry (see Gotcha #5).

11. **Never resolve a dataset DOI via OSTI `?doi=`.** A DOE prefix
    (`10.15485`, `10.11578`) tempts a jump straight to the OSTI API. Don't
    — `?doi=` can return several records that disagree on the funder, and
    OSTI carries fewer ORCIDs than DataCite. Always `doi.org` content
    negotiation first (step 2b); OSTI comes later, by canonical ID.

---

## References

- **Template (do not edit)**: [references/genesis_v1.0_template.md](references/genesis_v1.0_template.md)
- **Upstream provenance**: https://gitlab.osti.gov/genesis/data-cards (vendored at commit `7226c2c`).
- **LinkML schema** (validator source of truth): `scripts/genesis_datacard.yaml`
- **Field-by-field guidance**: [references/genesis_field_guide.md](references/genesis_field_guide.md)
- **Per-capability prompts**: [references/capability-prompts.md](references/capability-prompts.md)
- **Body-fill guide**: [references/body-fill-guide.md](references/body-fill-guide.md)
- **Lookup tables** (enums, vocabularies): [references/lookup-tables.md](references/lookup-tables.md)
- **Validation extras** (warn-level rules): [references/validation-rules.md](references/validation-rules.md)
- **Live DOI/ORCID/ROR/OSTI enrichment**: [references/live-enrichment.md](references/live-enrichment.md)
- **Introspection commands**: [references/introspection-commands.md](references/introspection-commands.md)
- **Validation**: upstream `linkml-validate` (see step 9)
- **Introspector**: `scripts/introspect.py`
- **Converter**: `scripts/convert_v1_to_genesis.py`
