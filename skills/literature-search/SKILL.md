---
name: literature-search
description: Search scientific literature across arXiv, PubMed, Semantic Scholar, and Google Scholar. Use when finding papers, reviewing research topics, building bibliographies, or exploring citation networks.
---

# Scientific Literature Search

Search, discover, and synthesize scientific literature across multiple databases to support research workflows.

## When to Use This Skill

Use this skill when you need:
- **Paper discovery** across arXiv, PubMed, Semantic Scholar, Google Scholar
- **Topic surveys** to understand the state of a research area
- **Citation analysis** to find foundational and recent work
- **Bibliography generation** in BibTeX, APA, or other formats
- **Related work** for a paper or grant proposal

## Core Workflow

### 1. Search

Query databases using web search with site-specific targeting:

```
site:arxiv.org "neural radiance fields"
site:pubmed.ncbi.nlm.nih.gov "CRISPR delivery"
site:semanticscholar.org "climate model uncertainty"
```

### 2. Evaluate

For each relevant paper, extract:
- Title, authors, year, venue
- Key contribution (1-2 sentences)
- Citation count (indicates influence)
- DOI or permanent URL

### 3. Synthesize

Present results organized by:
- **Foundational work** — highly cited, establishes the field
- **Recent advances** — last 2-3 years
- **Reviews/surveys** — comprehensive overviews

### 4. Format

Generate citations in requested format (BibTeX, APA, markdown table).

## Quick Reference

| Database | Best For | Search Prefix |
|----------|----------|---------------|
| arXiv | Physics, Math, CS, ML | `site:arxiv.org` |
| PubMed | Biomedicine, Life Sciences | `site:pubmed.ncbi.nlm.nih.gov` |
| Semantic Scholar | Cross-domain, citations | `site:semanticscholar.org` |
| Google Scholar | Broad coverage | Direct search |

## Additional Resources

- For database-specific search syntax, see [databases.md](databases.md)
- For citation formatting examples, see [formats.md](formats.md)
- For literature review strategies, see [strategies.md](strategies.md)

## Links

- arXiv: https://arxiv.org
- PubMed: https://pubmed.ncbi.nlm.nih.gov
- Semantic Scholar: https://www.semanticscholar.org
- Connected Papers: https://www.connectedpapers.com
