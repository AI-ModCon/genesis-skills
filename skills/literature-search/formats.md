# Citation Formats

## BibTeX

Standard format for LaTeX documents.

### Journal Article

```bibtex
@article{smith2024neural,
  title={Neural Networks for Scientific Discovery},
  author={Smith, John and Doe, Jane and Johnson, Robert},
  journal={Nature Machine Intelligence},
  volume={6},
  number={3},
  pages={234--248},
  year={2024},
  publisher={Nature Publishing Group},
  doi={10.1038/s42256-024-00123-4}
}
```

### Conference Paper

```bibtex
@inproceedings{chen2024transformers,
  title={Transformers for Molecular Property Prediction},
  author={Chen, Wei and Kumar, Anil and Zhang, Li},
  booktitle={Proceedings of the 41st International Conference on Machine Learning},
  pages={1234--1245},
  year={2024},
  organization={PMLR}
}
```

### arXiv Preprint

```bibtex
@article{wang2024foundation,
  title={Foundation Models for Science: A Survey},
  author={Wang, Mei and Garcia, Carlos},
  journal={arXiv preprint arXiv:2401.12345},
  year={2024}
}
```

### Book

```bibtex
@book{bishop2006pattern,
  title={Pattern Recognition and Machine Learning},
  author={Bishop, Christopher M.},
  year={2006},
  publisher={Springer}
}
```

### Book Chapter

```bibtex
@incollection{lecun2015deep,
  title={Deep Learning},
  author={LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
  booktitle={Handbook of Brain Theory and Neural Networks},
  pages={436--444},
  year={2015},
  publisher={MIT Press}
}
```

### Key Naming Convention

Use `authorYEARkeyword`:
- `smith2024neural`
- `vaswani2017attention`
- `he2016deep`

---

## APA 7th Edition

### Journal Article

```
Smith, J., Doe, J., & Johnson, R. (2024). Neural networks for scientific
    discovery. Nature Machine Intelligence, 6(3), 234-248.
    https://doi.org/10.1038/s42256-024-00123-4
```

### Journal Article (8+ authors)

```
Wang, M., Chen, L., Zhang, H., Liu, Y., Kumar, A., Garcia, C., Smith, J.,
    & Johnson, R. (2024). Large-scale molecular simulations. Science,
    383(6789), 123-130. https://doi.org/10.1126/science.abc1234
```

### Conference Paper

```
Chen, W., Kumar, A., & Zhang, L. (2024). Transformers for molecular property
    prediction. In Proceedings of the 41st International Conference on
    Machine Learning (pp. 1234-1245). PMLR.
```

### Preprint

```
Wang, M., & Garcia, C. (2024). Foundation models for science: A survey.
    arXiv. https://arxiv.org/abs/2401.12345
```

### Book

```
Bishop, C. M. (2006). Pattern recognition and machine learning. Springer.
```

### Website / Online Resource

```
OpenAI. (2024). GPT-4 technical report. https://openai.com/research/gpt-4
```

---

## Chicago (Author-Date)

### Journal Article

```
Smith, John, Jane Doe, and Robert Johnson. 2024. "Neural Networks for
    Scientific Discovery." Nature Machine Intelligence 6 (3): 234-48.
    https://doi.org/10.1038/s42256-024-00123-4.
```

### Book

```
Bishop, Christopher M. 2006. Pattern Recognition and Machine Learning.
    New York: Springer.
```

---

## IEEE

### Journal Article

```
[1] J. Smith, J. Doe, and R. Johnson, "Neural networks for scientific
    discovery," Nature Mach. Intell., vol. 6, no. 3, pp. 234-248, 2024,
    doi: 10.1038/s42256-024-00123-4.
```

### Conference Paper

```
[2] W. Chen, A. Kumar, and L. Zhang, "Transformers for molecular property
    prediction," in Proc. 41st Int. Conf. Mach. Learn., 2024, pp. 1234-1245.
```

---

## Markdown Table

For quick reference in documents:

```markdown
| Title | Authors | Year | Venue | Link |
|-------|---------|------|-------|------|
| Neural Networks for Discovery | Smith et al. | 2024 | Nature MI | [DOI](https://doi.org/...) |
| Transformers for Molecules | Chen et al. | 2024 | ICML | [PDF](https://...) |
```

---

## DOI Resolution

Always prefer DOIs for permanent links:

- Full URL: `https://doi.org/10.1038/s42256-024-00123-4`
- Short form: `doi:10.1038/s42256-024-00123-4`

Resolve any DOI: `https://doi.org/<doi>`

---

## Getting Citation Data

### From arXiv

Click "Export BibTeX citation" on any paper page.

### From Semantic Scholar

Click "Cite" button, select format.

### From Google Scholar

Click the quote icon (") under any result, select format.

### From DOI

```bash
curl -LH "Accept: application/x-bibtex" https://doi.org/10.1038/s42256-024-00123-4
```
