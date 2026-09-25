# Validation extras

Schema validation is upstream's `linkml-validate` against
`scripts/genesis_datacard.yaml` (see SKILL.md step 9). This skill ships no
validator of its own.

The rules below are the ones the schema cannot express. Nothing checks them
for you — confirm each by eye before you call a card done.

## Filename rule (warn)

`datacard.filename` must equal `genesis_datacard_<snake_case(identification.name)>.md`,
where `snake_case` lowercases the dataset name and replaces any non-alphanumeric
run with a single underscore.

- Severity: `warn` (informational; doesn't block validation)
- Path checked (v2): `discoverability.datacard.filename` ↔ `discoverability.identification.name`
- Legacy path checked: `datacard.filename` ↔ `identification.name` (for v1-shaped datacards)

## Workflow ↔ release_status alignment (warn)

The workflow state of the dataset should align with its release status. Mismatches
are not errors but should be flagged.

| `workflow.state` | Typical `release_status` |
|---|---|
| `Raw` / `Processing` / `QA` / `Analysis` | `Draft` |
| `Review` | `Under_Review` |
| `Embargo` / `Published` | `Approved` or `Published` |
| `Archived` | `Deprecated` or `Published` |

- Severity: `warn`
- Paths checked (v2): `discoverability.workflow.state` ↔ `discoverability.release_status`
- Legacy paths checked: `workflow.state` ↔ `release_status`

## Why the schema cannot express these

`scripts/genesis_datacard.yaml` covers required fields, enums, and format
patterns. It does not express:

- **Severity.** A LinkML result is pass/fail. The filename mismatch and the
  workflow/release misalignment are advisory — a card can be correct and
  still trip them — so they are not schema rules.
- **Cross-field slug computation.** The filename rule needs
  `snake_case(identification.name)` computed and compared against
  `filename`; the schema can only check the filename's own pattern.
- **Recommendation vs constraint.** The workflow/release pairings are
  typical, not required. Cards in transitional states are valid.

## The upstream publisher bug

`linkml-validate` reports `'dataset_publisher' is a required property` on
**every** card. The schema's rule says the publisher is required only when
`release_status` is `Approved` or `Published`, but its precondition is
written `in_subset: [Approved, Published]`, and in LinkML `in_subset`
declares subset membership of a schema element rather than testing a value.
The precondition is therefore vacuous and the postcondition always applies.
The fix upstream is `equals_string_in`.

Until that lands: treat the error as real only when `release_status` is
`Approved` or `Published`, and ignore it otherwise. Every other error is
genuine.

## Quote your dates

`created_date: 2026-09-21` unquoted is a YAML date, not a string, and the
schema declares these slots as strings — `linkml-validate` rejects it with
`is not of type 'string'`. Quote every date, as the template does.
