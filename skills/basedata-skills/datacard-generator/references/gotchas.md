# Additional gotchas

These are gotchas the day-to-day generation workflow doesn't hit
frequently — either they're schema-invisible (nothing in the validator
catches a violation) or the validator already produces a clear, actionable
error, so there's little value in front-loading them into `SKILL.md`'s main
Gotchas list. Read this file if you're debugging an unexpected result, or
before working with `created_by` ordering or `ai_model`/`software` agent
entries.

1. **`created_by` chronological ordering**: when
   `creation_method=Hybrid`, list the `ai_model` entry first (initial
   draft), then any `person` entry (reviewer). This ordering is not
   schema-enforced — nothing in the validator will flag a datacard that
   gets it backwards.

2. **`ai_model`/`software` agents require a `relationship` slot.** When
   `discoverability.datacard.created_by[].creator.ai_model` or `.software`
   is populated, `relationship` is required — one of `used_to_create |
   used_to_process | used_to_analyze | recorded_by | trained_on |
   evaluated_on` (`ExtendedRelationshipEnum`; there is no `other` value
   despite some upstream docs implying one). The same enum applies to
   `interoperability.related_resources.software[].relationship` and
   `.ai_models[].relationship`. The validator catches a missing
   `relationship` cleanly as `MISSING_REQUIRED`, so this is easy to fix
   once flagged.

3. **Take `ai_model.version` from the model ID; never invent one.**
   `gpt-5.5` → `5.5`, `llama-3.3-70b` → `3.3`. The pattern is
   `^\d+\.\d+(\.\d+)?$`, so an ID carrying only a major version
   (`claude-opus-5` → `5`) has no legal form: omit the key, which is
   optional, rather than pad to `5.0` and assert a minor version the model
   does not have. The full ID belongs in `identifier`
   (`{type: local, value: claude-opus-5}`), the product name in `name`.
   `linkml-validate` reports this as `does not match '^\\d+\\.\\d+(\\.\\d+)?$'`.

4. **Never leave `authors: []`, and never fake an entry to fill it.**
   The schema requires at least one author once `release_status` is
   `Approved` or `Published`, but the check is for presence, not for a
   non-empty list. Both of these validate clean, and both are worthless:

   ```yaml
   authors: []                    # observed in a real run
   authors:                       # observed in a real run
     - person:
         role: [Data_Curation]    # no given_name, no family_name
   ```

   `PersonClass` requires no name, so a nameless person passes. If you
   cannot name a person, the honest fallback is the stewarding
   **organization** — a real, checkable entity with a ROR — and say in the
   review summary that no individual was named.

   This bites hardest on a derived dataset whose DOI failed the provenance
   gate. The source record's creators are not this dataset's authors, so
   they are correctly not copied — but that leaves nothing behind. Find the
   preparers locally (CITATION.cff, a README credits section, a repository
   metadata record) or ask the user. The hosting facility as an
   organization author is a last resort, not a default, and the source's
   authors are never the answer. See `references/live-enrichment.md`
   § "A failed gate does not mean discard the record".
