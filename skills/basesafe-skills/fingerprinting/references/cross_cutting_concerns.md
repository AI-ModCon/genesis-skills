# Cross-Cutting Concerns

Fingerprinting should annotate the likely concerns that later skills should examine in depth.

## Vision Systems

Likely attack surfaces:
- adversarial perturbations
- patch attacks
- data poisoning
- preprocessing mismatch

Likely uncertainty hooks:
- confidence calibration
- OOD and corruption robustness
- MC dropout or ensembles

Likely explainability hooks:
- saliency maps
- Grad-CAM
- feature attribution on failure slices

## NLP / RAG / Agent Systems

Likely attack surfaces:
- prompt injection
- retrieval poisoning
- tool abuse
- context poisoning

Likely uncertainty hooks:
- answerability
- self-consistency disagreement
- retrieval sufficiency
- refusal / escalation thresholds

Likely explainability hooks:
- citation grounding
- chain or step auditability
- source attribution

## Tabular and Classical ML

Likely attack surfaces:
- data leakage
- feature manipulation
- training-serving skew
- privacy inference

Likely uncertainty hooks:
- calibration
- conformal prediction
- selective prediction

Likely explainability hooks:
- SHAP
- feature importance
- counterfactual analysis

## Time Series and Sensor Systems

Likely attack surfaces:
- temporal shift
- sensor spoofing
- aggregation-window mismatch

Likely uncertainty hooks:
- prediction intervals
- horizon-specific degradation
- drift monitoring

Likely explainability hooks:
- lag importance
- temporal saliency
- regime-specific diagnostics

## Retrieval and Recommendation

Likely attack surfaces:
- index poisoning
- ranking manipulation
- feedback-loop abuse

Likely uncertainty hooks:
- confidence in retrieval sufficiency
- abstention on weak evidence
- ranking stability

Likely explainability hooks:
- source attribution
- feature and score decomposition
- recommendation rationale

## RL and Control

Likely attack surfaces:
- reward hacking
- simulator mismatch
- unsafe exploration
- observation spoofing

Likely uncertainty hooks:
- state uncertainty
- policy stability
- safe fallback conditions

Likely explainability hooks:
- policy behavior by scenario
- reward contribution analysis
- state-action trace review

## Serving and Platform Concerns

Always consider:
- auth and access control
- rate limiting
- logging and redaction
- monitoring and drift detection
- fallback behavior
- human review paths

