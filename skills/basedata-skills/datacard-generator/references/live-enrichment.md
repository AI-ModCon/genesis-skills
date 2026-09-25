# Live Enrichment Reference

**This step is not optional.** SKILL.md workflow step 7 is a required stop.
Skipping enrichment produces datacards where a typo'd ORCID resolves to the
wrong human and no one catches it until publication. The API round-trips
cost a handful of seconds; that's cheaper than a wrong-authorship
correction post-publication.

The skill resolves every ORCID, ROR, DOI, and OSTI award number in the datacard against its public API — **even when the user already provided a value**. The dataset's own DOI is resolved early, at workflow step 2b (§ Order of operations below); everything else is swept at step 7 ("Cross-check identifiers via live APIs"). The goal is two-fold: (1) fill missing fields the authoritative source has (affiliations, names, emails), and (2) catch mistyped identifiers that would otherwise resolve to the wrong entity or 404 silently. This file is the agent's guide to those APIs. Make the calls with whatever HTTP-fetch capability your harness provides (`WebFetch`, `curl`, or equivalent) — the endpoints below are plain HTTP with an `Accept` header and no API keys.

Treat every resolved value as a candidate for cross-check, not as authoritative. When the API returns a value that conflicts with the datacard, **present both to the user** rather than silently overwriting.

Format validation (ORCID/ROR regex patterns) lives in the LinkML schema at `scripts/genesis_datacard.yaml` and is enforced by `linkml-validate` at step 9. This doc covers only the unique value-add: checksum verification, live API endpoints, DOE-specific OSTI guidance, and rate-limit compliance.

---

## Order of operations: DOI first

**If the dataset has a DOI, resolve it before anything else — including
before prompting the user in step 6.** A single DOI request returns the
title, abstract, the *complete* author roster with ORCIDs and affiliations,
keywords, publisher, funding, and often the canonical OSTI ID. Every one of
those is a field the skill would otherwise ask the user for one at a time,
or look up one identifier at a time.

```
    DOI ──► title, abstract, keywords, publisher, funding, geo
        ├─► authors[] + ORCIDs ──► ORCID API (verify, don't discover)
        ├─► affiliations ─────────► ROR API (resolve names → ror_id)
        └─► OSTI ID ──────────────► OSTI record (DOE extras, by ID not by ?doi=)
```

Run in this order:

1. **DOI** (§ DOI below) — one call, seeds the most fields. Do this during
   workflow step 2b, as soon as introspection surfaces a DOI.
2. **ORCID** — for each ORCID now known, confirm the name matches. The DOI
   record already supplied names, so these are *verifications*, not lookups
   into the dark.
3. **ROR** — resolve affiliation strings from the DOI record to `ror_id`s.
4. **OSTI** — DOE-funded datasets only, for fields DataCite lacks
   (`doe_contract_number` variants, sponsor org phrasing, full issue date).

Without a DOI, start at step 2 and work with whatever identifiers
introspection and the user supplied.

---

## Identifier paths to check (by capability)

Enrich every path below that is present in the datacard. The list is
grouped by capability so you can skip capabilities the user opted out of
(`supports_X = No`).

**`discoverability` (always present):**

- Every `discoverability.authors[].person.orcid` and `…person.affiliation.ror_id`
- Every `discoverability.authors[].organization.ror_id`
- Every `discoverability.contributors[].person.orcid` and `…ror_id`
- `discoverability.contact.person.orcid` and `…ror_id`
- Every `discoverability.additional_contacts[].person.orcid` and `…ror_id`
- Every `discoverability.sponsor_organizations[].ror_id` and `…award_number` (the latter from the DOI record's `fundingReferences[]`, or via OSTI)
- Every `discoverability.research_organizations[].ror_id`
- Every `discoverability.facilities[].ror_id` and `…location.ror_id`
- `discoverability.identification.primary_id.value` (if `type: doi`)
- Every `discoverability.identification.additional_ids[].value` of type `doi`

**`reusability` (when `supports_reusability=Yes`):**

- `reusability.stewardship.maintainer.person.orcid` and `…ror_id`

**`governed_use` (when `supports_governed_use=Yes`):**

- Every `governed_use.review_provenance_companion[].reviewed_by.person.orcid`

**`interoperability` (when `supports_interoperability=Yes`):**

- Every `interoperability.related_resources.datasets[].identifier.value` (if `type: doi`)
- Every `interoperability.related_resources.publications[].value` (if `type: doi` — the only `IdentifierTypeEnum` value cross-checked here)

For each lookup, classify the outcome as one of: **Clean match** (silent
pass), **Mismatch** (present both side-by-side, ask the user), **Datacard
incomplete** (API has fields the datacard doesn't; offer to add), **Does
not resolve** (404/error; warn the user — likely typo), or **Rate-limited**
(retry once; if still failing, log and move on).

The DOI paths above are a special case: resolving a DOI doesn't only
*check* the identifier, it **seeds** a dozen other paths across
`discoverability`, `interoperability` and `reusability`. See the mapping
table in § DOI.

---

## DOI

The DOI is the highest-yield call in this file and the cheapest: one
request, no API key, and it resolves across every registrar (DataCite,
Crossref, and the repositories built on them — ESS-DIVE, Zenodo, Dryad,
figshare, OSTI). Resolve it **first**; everything else gets easier.

**Rate limit:** `doi.org` content negotiation publishes no numeric limit.
Space calls ~1/sec, as elsewhere in this file. DOI records are stable —
resolve each distinct DOI once per session and reuse the response.

### Live Lookup

Ask for DataCite JSON first; it is the richest shape for datasets:

```
GET https://doi.org/{doi}
Headers: Accept: application/vnd.datacite.datacite+json
```

**On `HTTP 406` ("No acceptable resource available"), retry with CSL-JSON:**

```
GET https://doi.org/{doi}
Headers: Accept: application/vnd.citationstyles.csl+json
```

CSL-JSON works for every registrar but carries fewer fields (no
`fundingReferences`, no `geoLocations`, no nested `identifiers`). A 406 on
the DataCite request is itself informative: it means the DOI is registered
with Crossref, which almost always means **a journal article, not a
dataset** — see the provenance gate below.

A `404` means the DOI is not registered anywhere. Flag it loudly; the user
most likely mistyped it or is holding a placeholder.

Verified 2026-09-14 against `10.15485/3001901` (DataCite, dataset → 200)
and `10.1111/gcb.13626` (Crossref, article → 406 then CSL-JSON 200).

### Provenance gate — run this BEFORE writing any field

DOIs found in README prose are frequently *related work*: a methods paper,
a prior version, a dataset someone cited. Writing that record's authors and
abstract into the card silently misattributes the dataset. Gate on two
checks:

1. **Is it a dataset?** DataCite `types.resourceTypeGeneral == "Dataset"`
   (or CSL `type == "dataset"`). A `journal-article` — or a 406 on the
   DataCite request — is related work.
2. **Does the title match?** Compare `titles[0].title` against the title
   from README/CITATION.cff. Minor punctuation and subtitle drift is fine;
   a different subject is not.

| Gate result | Where the DOI goes |
|---|---|
| Dataset **and** title matches | `discoverability.identification.primary_id` (`type: doi`) — and seed the fields in the table below |
| Dataset, title **differs** | `interoperability.related_resources.datasets[]`; ask the user whether it is a prior version (`supersedes`) or a different dataset |
| Not a dataset | `interoperability.related_resources.publications[]` — **never** `primary_id`, and never seed authors or abstract from it |
| Does not resolve | Leave `primary_id` alone; flag the DOI as unverified |

Where a DOI came from also carries trust: a **CITATION.cff `doi:` field**
is self-referencing by definition, while a **DOI in README prose** is a
candidate that must clear the gate. Both still get gated — CITATION.cff
files are copy-pasted too.

> Worked example: a README states *"Hanson et al. (2017), DOI:
> 10.1111/gcb.13626 for the SPRUCE experimental design."* That DOI is
> Crossref-registered (406 → CSL-JSON), and resolves to Rollinson et al.
> 2017 on ecosystem-model productivity — not Hanson, not SPRUCE design. It
> belongs in `related_resources.publications[]` with the mismatch reported
> to the user, and nothing from it may touch the dataset's own fields.

### What to extract (DataCite JSON)

| DataCite field | Datacard path | Notes |
|---|---|---|
| `titles[0].title` | `discoverability.identification.name` | required field |
| `descriptions[]` where `descriptionType: Abstract` | `discoverability.dataset_description.dataset_summary` | required field. Trim to 1–3 sentences; park the full abstract in `discoverability.identification.description` if it is long |
| `subjects[].subject` | `discoverability.dataset_description.keywords` | required, ≥1. Drop registrar bookkeeping entries (e.g. `"54 ENVIRONMENTAL SCIENCES"` with a `classificationCode`) or map them to `dataset_description.science_domain` |
| `creators[]` | `discoverability.authors[]` | one `- person:` entry each; see author shape below |
| `creators[].givenName` / `.familyName` | `…authors[].person.given_name` / `.family_name` | |
| `creators[].nameIdentifiers[]` where `schemeUri` is ORCID | `…authors[].person.orcid` | **store the full URL form** `https://orcid.org/XXXX-XXXX-XXXX-XXXX` — the model regex rejects the bare ID |
| `creators[].affiliation[].name` | `…authors[].person.affiliation.name` | `name` is required inside an `affiliation` block; feed the string to the ROR lookup to get `ror_id` |
| `publisher.name` | `discoverability.dataset_publisher.name` | required once `release_status` is `Approved` or `Published` |
| `fundingReferences[].funderName` | `discoverability.sponsor_organizations[].name` | |
| `fundingReferences[].awardNumber` | `discoverability.sponsor_organizations[].award_number` | **often removes the need for an OSTI call** |
| `identifiers[]` where `identifierType: "OSTI ID"` | (not a card field) | the canonical OSTI record id — use it for the OSTI lookup instead of `?doi=` |
| `version` | `discoverability.identification.version` | must match `^\d+\.\d+(\.\d+)?$`. DataCite often omits it or uses a non-numeric string — when it does, fall back to the template default `"1.0"`. There is **no** `not_applicable` escape hatch for this field |
| `types.resourceTypeGeneral` | `discoverability.product_type` → `Data` | `ProductTypeEnum`; also `dataset_description.tags.object_type` → `Dataset` |
| `geoLocations[]` | `interoperability.data_structure` geo fields | requires `supports_interoperability=Yes`; see `references/genesis_field_guide.md` for the bounding-box slots |
| `doi` | `discoverability.identification.primary_id` (`type: doi`) | only past the gate. `IdentifierTypeEnum` is lowercase: `ark \| doi \| handle \| local \| purl \| url \| urn \| uuid \| other \| unregistered` |

**Dates need care.** DataCite gives `publicationYear` (a bare year), but
`interoperability.dates.issued` requires a full `^\d{4}-\d{2}-\d{2}$`. Do
**not** invent a month and day. Take the full date from DataCite `dates[]`
if present, or from OSTI `publication_date`; otherwise leave `issued`
unset and tell the user why. The year alone is still usable for
`reusability.citation.preferred_citation.year` (`^\d{4}$`).

Author entry shape (`AgentClass` allows exactly one of `person` /
`organization` / `ai_model` / `software`; there is **no** `type:` key):

```yaml
discoverability:
  authors:
    - person:
        given_name: Joshua M.
        family_name: Birkebak
        orcid: https://orcid.org/0009-0009-5561-1494
        affiliation:
          name: Oak Ridge National Laboratory (ORNL), Oak Ridge, TN (United States)
          ror_id: https://ror.org/01qz5mb56          # from the ROR lookup
        role: [Data_Curation]                        # CRediT; ask the user
```

CRediT `role[]` is **not** in any DOI record — it still has to be asked.

### CSL-JSON fallback field names

When the DataCite request returned 406, the equivalents are: `title`,
`abstract`, `author[].given` / `.family` / `.ORCID`, `publisher`,
`issued.date-parts[0][0]` (year), `categories`, `type`. CSL titles may
carry XML markup (`<scp>`, `<sub>`) — strip tags before storing.

### Also consider

Whether the resolved DOI belongs in
`reusability.citation.preferred_citation` — that block needs `author`,
`title`, `year`, `publisher`, and at least one of `doi` / `url`, all of
which the DOI record just supplied.

**Everything seeded from a DOI is a candidate, not a fact.** Present the
resolved values to the user as one consolidated table (see § Batching
guidance) before writing them.

---

## ORCID

**Rate limit**: The public ORCID API (`pub.orcid.org`) has no published
per-second limit but returns HTTP 429 under heavy load. Space calls at
~1/sec to be safe. Persistent 429s should back off exponentially.

### Checksum verification (ISO 7064 MOD 11-2)

Before calling the API, you can self-check an ORCID without a network round-trip. Take the first 15 digits, run the algorithm below, and compare to the 16th character (which may be `X` = 10).

```
total = 0
for each of the first 15 digits d:
    total = (total + d) * 2
remainder = total % 11
result = (12 - remainder) % 11   # 10 → "X", else digit
```

If the checksum fails, warn the user before proceeding.

### Live Lookup

```
GET https://pub.orcid.org/v3.0/{orcid}/person
Headers: Accept: application/json
```

On success, extract:
- `name.given-names.value` → `person.given_name`
- `name.family-name.value` → `person.family_name`
- `emails.email[0].email` → `person.email` (only if visibility = `PUBLIC`)
- `researcher-urls.researcher-url[].url.value` — look for an institutional URL if affiliation is absent

For affiliation, also fetch:
```
GET https://pub.orcid.org/v3.0/{orcid}/employments
Headers: Accept: application/json
```
Use the most recent employment's:
- `organization.name` → `person.affiliation.name`
- `organization.disambiguated-organization.disambiguated-organization-identifier` (if `disambiguated-organization-source` is `ROR`) → `person.affiliation.ror_id` (store in URL form, `https://ror.org/XXXXXXX`)

**Present confirmed values to the user before writing them to the card.**

---

## ROR

**Rate limit:** 2000 requests per 5-minute rolling window (~6.7 req/s), no API key required (https://ror.readme.io/docs/rest-api). Space lookups ~1/sec to stay well under this.

**Deprecation status (network-verified 2026-07-02):** ROR API v1 was sunset the week of 2025-12-08. Any request with an explicit `/v1/` path now returns `HTTP 410 Gone`:
```json
{"errors":[{"status":"410","title":"API Version Deprecated","detail":"The v1 API has been deprecated. Please migrate to v2.","deprecated_at":"2025-12-09"}]}
```
Requests to the version-less path (`https://api.ror.org/organizations/{id}`) now default to the **v2** response shape (confirmed live). Use the version-less or explicit `/v2/` path below — never `/v1/`.

### Storage convention

ROR identifiers are stored in **URL form** (`https://ror.org/XXXXXXX`) per the Genesis template. The format regex is in `scripts/genesis_datacard.yaml`. When a user provides a bare 9-character ID (e.g., `03yrm5c26`), prepend `https://ror.org/` before storing.

### Live Lookup

The ROR API expects the bare 9-character ID, not the URL form. Strip the `https://ror.org/` prefix when querying, but **store** the URL form in the datacard.

```
GET https://api.ror.org/v2/organizations/{bare_id}
```

On success, extract (v2 schema — field names changed from v1):
- `names[]` → find the entry whose `types[]` includes `"ror_display"` and use its `value` → the `name` field of whichever sub-block holds this ROR ID — e.g. `person.affiliation.name`, `organization.name`, `discoverability.sponsor_organizations[].name`, `discoverability.research_organizations[].name`, or `discoverability.facilities[].name`
- `locations[0].geonames_details.country_name` — useful context for the user (v1 was `country.country_name`)
- `types[]` — e.g., `["Education"]`, `["Government"]` (unchanged from v1)
- `links[]` → find the entry with `type == "website"` and use its `value` (v1 was a bare array of URL strings; v2 wraps each link in `{type, value}`)

**Present the resolved name to the user for confirmation** — ROR IDs can be mistyped and resolve to the wrong institution.

---

## OSTI

OSTI (Office of Scientific and Technical Information) provides a public REST API for DOE-funded research outputs including datasets, reports, and journal articles. Use it to pre-fill funding and provenance fields.

**Run this after § DOI, not instead of it.** If the DOI resolved, DataCite
has usually already supplied the authors, ORCIDs, abstract, keywords and
`fundingReferences[].awardNumber`. OSTI then covers what DataCite lacks: the
DOE contract number in its canonical form, sponsor-org phrasing, research
orgs, and a full `publication_date` where DataCite gave only a year. For a
dataset with no OSTI record — anything not DOE-funded — this whole section
is a no-op, and that is fine.

**Rate limit:** No numeric rate limit is published in the OSTI API docs, FAQs, or api-help pages (checked 2026-07-02). The sibling `/api/v1/records` (reports/publications) endpoint does return an `x-rate-limit-remaining` response header, so some throttling exists even where undocumented — space requests ~1/sec to stay well under a conservative ~5 req/s ceiling.

**Verified 2026-07-02:** `https://www.osti.gov/api/v1/datasets` returns **HTTP 404** — this endpoint does not exist. The correct dataset-search endpoint is the DOE Data Explorer API:

```
GET https://www.osti.gov/dataexplorer/api/v1/records?{params}
Headers: Accept: application/json
```

Documented query parameters (https://www.osti.gov/dataexplorer/api/v1/docs): `q`, `osti_id`, `fulltext`, `biblio`, `author`, `title`, `identifier`, `sponsor_org`, `research_org`, `contributing_org`, `source_id`, `publication_date_start`/`_end`, `entry_date_start`/`_end`, `language`, `country`, `site_ownership_code`, `sort`, `order`, `rows`, `page`.

**`award_number` and `site_url` are NOT functional filters** — verified empirically: passing either as a query param is silently ignored, and the endpoint returns its default (most-recent) result set instead of a 400/404 or a filtered match. Do not rely on them for lookup. `doi` filtering **does** work (verified with both a real DOI match and a fabricated DOI returning `[]`).

### Lookup by OSTI ID (preferred — skips the ambiguity below)

If § DOI returned an `identifiers[]` entry with `identifierType: "OSTI ID"`,
fetch that record directly. This is exact, single-valued, and avoids the
duplicate-record problem entirely:

```
GET https://www.osti.gov/dataexplorer/api/v1/records/{osti_id}
Headers: Accept: application/json
```

### Lookup by DOI (when no OSTI ID is available)

```
GET https://www.osti.gov/dataexplorer/api/v1/records?doi={doi}
```

**This can return more than one record for a single DOI, and they can
disagree on fields you are about to write.** Never take `records[0]` blindly.

> Verified 2026-09-14: `?doi=10.15485/3001901` returns **two** records.
> `osti_id 3030332` reports `doe_contract_number: "AC05-00OR22725"` (an ORNL
> contract) and `publication_date: 2026-02-28`; `osti_id 3001901` reports
> `"AC02-05CH11231"` (an LBNL contract) and `2025-12-31`, and carries an
> ORCID for an author the other omits. Taking the first record writes the
> wrong funder into the card.

Disambiguate in this order, stopping at the first that resolves:

1. **OSTI ID from DataCite** — use the record whose `osti_id` matches
   `identifiers[]` from § DOI. (In the example above that is `3001901`.)
2. **DOI suffix** — many OSTI DOIs are `10.15485/{osti_id}`; prefer the
   record whose `osti_id` equals the suffix.
3. **Cross-check the award number** — prefer the record whose
   `doe_contract_number` matches DataCite `fundingReferences[].awardNumber`.
   (This confirms `3001901` in the example.)
4. **Ask.** Present the competing records side by side — `osti_id`, title,
   `publication_date`, `doe_contract_number` — and let the user choose.
   Never silently pick one.

On success, extract from the selected record:
- `sponsor_orgs[]` → `discoverability.sponsor_organizations[].name` (array of strings — the response field is `sponsor_orgs`, not `sponsor_org`)
- `doe_contract_number` → `discoverability.sponsor_organizations[].award_number` (there is no separate `award_number` field in the response; DOE contract numbers are the closest available match — OSTI sometimes appends a trailing `; `, trim it)
- `research_orgs[]` → `discoverability.research_organizations[].name` (array of strings — the response field is `research_orgs`, not `research_org`)
- `site_url` / `doi` → cross-check against `discoverability.identification.primary_id.value` and `discoverability.identification.additional_ids[]`
- `title` — cross-check against `discoverability.identification.name`
- `authors[]` — array of formatted strings, e.g. `"Flynn, James (ORCID:0000000288355898)"`, not `{first_name, last_name}` objects; parse the name before the parenthetical, hyphenate the digits after `ORCID:` into `XXXX-XXXX-XXXX-XXXX`, then store as the **URL form** `https://orcid.org/XXXX-XXXX-XXXX-XXXX` (the `PersonClass.orcid` regex rejects a bare ID). Prefer DataCite `creators[]` when both are available — it is already structured
- `description` — seeds `discoverability.dataset_description.dataset_summary` if § DOI did not already supply an abstract
- `publication_date` → `interoperability.dates.issued` (requires `supports_interoperability=Yes`)
- `subjects[]` → `discoverability.dataset_description.keywords` (the response field is `subjects`, not `keywords`)

Also consider whether the resolved DOI belongs in
`reusability.citation.preferred_citation` (the BibTeX-style block: `doi`,
`title`, `author`, `year`, `publisher`, `url`) if a preferred citation
isn't already set.

### Lookup by organization or title (when no DOI is available)

Since there is no server-side award-number or site-url filter, search on a supported parameter instead and manually scan the results:
```
GET https://www.osti.gov/dataexplorer/api/v1/records?sponsor_org={org_name}&rows=20
GET https://www.osti.gov/dataexplorer/api/v1/records?research_org={org_name}&rows=20
GET https://www.osti.gov/dataexplorer/api/v1/records?title={title_text}&rows=20
```
Page through results (`rows`/`page`) and match on `doe_contract_number` or `site_url` in the returned records.

### Usage Notes

- OSTI records are DOE-funded work. If there is no match, the dataset may not be DOE-funded or may not yet be registered — inform the user rather than leaving the field blank silently.
- Award numbers follow no single format: `DE-SC0012345`, `DE-AC02-06CH11357`, `89243021CSC000001` are all valid DOE patterns. Since `award_number` isn't a queryable filter, use these only for manual matching against `doe_contract_number`, not as a URL parameter.
- If multiple records match, run the disambiguation ladder under "Lookup by DOI" before falling back to asking the user.
- The OSTI API returns JSON by default; no API key is required for read access.

---

## Batching guidance

When step 7 runs, resolve ALL identifiers first (batch the fetches) THEN
present a single consolidated diff table to the user showing every
mismatch, missing-field, and unresolvable ID at once. Do NOT interactively
prompt after each individual lookup — that produces 15+ pauses per
datacard and destroys the user experience.

The same applies to the step 2b DOI call: resolve, then present what it
found as one table, rather than confirming the title, then the abstract,
then each author in turn.

**Batched ≠ parallel.** Batch means "no user prompts between individual
lookups"; you should still space calls to respect each API's rate limit
(see the per-API sections below). Firing 15 fetches in parallel will
trigger HTTP 429 on OSTI and burn through ROR's 5-min window.

Consolidated table format:

| Field | Current value | Resolved value | Action |
|---|---|---|---|
| authors[0].person.orcid | 0000-0002-1234-5678 | (name mismatch: J. Doe vs Jane Smith) | Choose which |
| contact.person.affiliation.ror_id | https://ror.org/03yrm5c26 | ✓ resolves to "MIT" | (silent pass) |
| sponsor_organizations[0].award_number | DE-SC0012345 | (not found in OSTI) | Confirm typo? |

## Re-check-only-changed on validation loops

When step 10 (Address findings) loops back to step 7 after re-prompting
for values in step 6: re-enrich ONLY identifiers the user added or changed
in this iteration. Do not re-check every identifier from scratch — that's
wasteful and produces the same passing lookups repeatedly.
