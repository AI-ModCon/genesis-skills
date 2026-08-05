# Scientific Database Reference

## arXiv

Preprint server for physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, electrical engineering, and economics.

### Search Syntax

```
site:arxiv.org "<exact phrase>"
site:arxiv.org author:"LastName"
site:arxiv.org cs.LG "<machine learning topic>"
site:arxiv.org 2024 "<recent work>"
```

### Category Codes

| Code | Field |
|------|-------|
| `cs.LG` | Machine Learning |
| `cs.AI` | Artificial Intelligence |
| `cs.CL` | Computation and Language (NLP) |
| `cs.CV` | Computer Vision |
| `physics.comp-ph` | Computational Physics |
| `cond-mat` | Condensed Matter |
| `quant-ph` | Quantum Physics |
| `astro-ph` | Astrophysics |
| `math.NA` | Numerical Analysis |
| `stat.ML` | Machine Learning (Statistics) |
| `q-bio` | Quantitative Biology |

### arXiv IDs

Format: `YYMM.NNNNN` (e.g., `2301.07041`)

Direct URL: `https://arxiv.org/abs/2301.07041`
PDF: `https://arxiv.org/pdf/2301.07041.pdf`

### Notes

- Preprints are not peer-reviewed
- Many papers have published versions — look for DOI links
- Check version history (`v1`, `v2`, etc.) for updates

---

## PubMed

Biomedical and life sciences literature from MEDLINE, life science journals, and online books.

### Search Syntax

```
site:pubmed.ncbi.nlm.nih.gov "<topic>"
site:pubmed.ncbi.nlm.nih.gov "<gene name>" review
site:pubmed.ncbi.nlm.nih.gov "<disease>" clinical trial
```

### PubMed Advanced Search

For complex queries, use PubMed directly:

- `[Title/Abstract]` — Search title and abstract
- `[Author]` — Author name
- `[Journal]` — Journal name
- `[MeSH Terms]` — Medical Subject Headings

Example: `"machine learning"[Title/Abstract] AND "drug discovery"[Title/Abstract]`

### PMIDs

PubMed IDs are numeric (e.g., `34567890`)

Direct URL: `https://pubmed.ncbi.nlm.nih.gov/34567890/`

### Notes

- All indexed articles are peer-reviewed
- PMC (PubMed Central) provides free full text for some articles
- Use MeSH terms for precise medical/biological searches

---

## Semantic Scholar

AI-powered academic search with citation analysis and paper recommendations.

### Search Syntax

```
site:semanticscholar.org "<topic>"
site:semanticscholar.org author:"<name>"
```

### Features

- **Citation counts** — Useful for identifying influential papers
- **Influential citations** — Distinguishes significant from peripheral citations
- **TLDR** — AI-generated paper summaries
- **Related papers** — Algorithmic recommendations
- **Citation graphs** — Visualize citation networks

### Semantic Scholar API

For programmatic access:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=machine+learning&limit=10"
```

### Corpus IDs

Semantic Scholar uses Corpus IDs and supports DOIs, arXiv IDs, and PMIDs.

---

## Google Scholar

Broad coverage across disciplines, including books, theses, and conference papers.

### Search Syntax

```
"<exact phrase>"
author:"<name>"
intitle:"<word in title>"
source:"<journal name>"
```

### Date Filtering

- Click "Since Year" in sidebar
- Or add to query: `"topic" 2023..2025`

### Features

- **Cited by** — Find papers citing a given work
- **Related articles** — Similar papers
- **Versions** — Find different versions (preprint, published)
- **Create alert** — Email notifications for new papers

### Notes

- Broadest coverage but noisiest results
- Citation counts may differ from other sources
- No API access — use web search

---

## Specialized Databases

### ChemRxiv / ACS Publications

Chemistry preprints and published work.

```
site:chemrxiv.org "<chemistry topic>"
site:pubs.acs.org "<chemistry topic>"
```

### IEEE Xplore

Electrical engineering, computer science, electronics.

```
site:ieeexplore.ieee.org "<topic>"
```

### Nature / Science

High-impact general science.

```
site:nature.com "<topic>"
site:science.org "<topic>"
```

### bioRxiv / medRxiv

Biology and medicine preprints.

```
site:biorxiv.org "<topic>"
site:medrxiv.org "<topic>"
```

---

## Choosing a Database

| Research Area | Primary | Secondary |
|--------------|---------|-----------|
| Machine Learning | arXiv (cs.LG) | Semantic Scholar |
| Biomedicine | PubMed | Google Scholar |
| Physics | arXiv | Google Scholar |
| Chemistry | ACS, ChemRxiv | Semantic Scholar |
| Engineering | IEEE Xplore | Google Scholar |
| Cross-disciplinary | Semantic Scholar | Google Scholar |
| Finding citations | Semantic Scholar | Google Scholar |
