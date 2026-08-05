# Vision Runbook

Use this runbook for image or video systems including classification, detection, and segmentation.

## Inspect

- dataset structure, labels, and augmentation pipeline
- training scripts and config files
- evaluation metrics and failure slices
- inference entrypoints and preprocessing assumptions
- export or serving paths

## Capture

- task type and output form: label, box, or mask
- image sizes, normalization, augmentations
- architecture family: CNN, ResNet, UNet, ViT, hybrid
- framework and training regime
- evidence of calibration, robustness, and slice evaluation

## Common Hooks

- attack surface: perturbations, patches, poisoning
- uncertainty hooks: confidence scores, OOD tests, corruption benchmarks
- explainability hooks: saliency, Grad-CAM, attribution maps

## Typical Unknowns

- exact label semantics
- annotation quality
- domain-shift coverage
- human review procedures for uncertain predictions

