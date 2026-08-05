# Adversarial Uncertainty Analysis

## Purpose

Uncertainty estimates may behave differently when the model is under attack. Test whether uncertainty signals can detect adversarial manipulation or OOD scenarios.

## 1. Calibration Under Attack

**Objective**: Measure whether confidence remains well-calibrated on adversarial examples

**Methodology**:
```
1. Generate adversarial examples using gradient-based attacks (FGSM, PGD, C&W)
2. Measure model predictions and confidence on adversarial data
3. Compute calibration metrics (ECE, MCE) on adversarial distribution
4. Compare to baseline calibration on clean data
```

**Expected Behavior**:
- **Good**: Model shows high uncertainty on adversarial examples, especially when wrong
- **Bad**: Model remains highly confident on misclassified adversarial examples

**Metrics**:
- ECE on adversarial data vs. clean data
- Confidence on correctly vs. incorrectly classified adversarial examples
- Reliability diagram comparison (clean vs. adversarial)

**Tools**: Use uncertainty-toolbox with adversarial examples from ART/Foolbox

## 2. Uncertainty as Attack Detector

**Objective**: Use uncertainty signals to detect when model is under attack

**Methodology**:
```
1. Establish uncertainty baseline on clean validation data
2. Generate adversarial examples with varying perturbation strengths
3. Measure uncertainty on adversarial examples
4. Set detection threshold (e.g., 95th percentile of clean uncertainty)
5. Compute detection metrics (TPR, FPR, ROC-AUC)
```

**Detection Criteria**:
- High uncertainty → potential adversarial input
- Threshold tuning balances detection rate vs. false alarms

**Metrics**:
- ROC curve: detection rate vs. false positive rate
- Precision-recall curve for attack detection
- Detection threshold selection (balance safety vs. usability)

**Integration**: Connect to runtime monitoring, trigger alerts on sustained high uncertainty

## 3. Attack-Specific Uncertainty Patterns

**Objective**: Different attacks produce different uncertainty signatures - use for attribution

**Methodology**:
```
1. Generate examples using multiple attack types (FGSM, PGD, C&W, boundary attacks)
2. Measure uncertainty for each attack type
3. Analyze uncertainty distributions per attack
4. Build attack fingerprints based on uncertainty patterns
```

**Observations**:
- **FGSM**: One-step gradient, may produce moderate uncertainty
- **PGD**: Iterative optimization, may push to decision boundary with variable uncertainty
- **C&W**: Minimal perturbation, may evade detection with low uncertainty
- **Transfer attacks**: Often produce higher uncertainty than white-box attacks

**Use Case**: Uncertainty fingerprints help identify attack type for incident response

## 4. OOD Detection for Agents

**Objective**: Use uncertainty to detect when agents encounter out-of-distribution scenarios

### Agent-Specific Uncertainty Monitoring

**Tool Usage Uncertainty**:
- Confidence in tool selection decisions
- Uncertainty when choosing between similar tools
- Detection of unclear or ambiguous user requests
- Example: "Agent unsure whether to use search_web or query_database"

**Context Boundary Detection**:
- Uncertainty signals when approaching context limits
- Memory recall confidence (is retrieved memory relevant?)
- Prompt complexity vs. confidence correlation
- Example: "High uncertainty on queries that require synthesis of distant context"

**Runtime Anomaly Detection**:
- Establish uncertainty baseline during normal operation
- Alert on sustained high uncertainty (potential attack or OOD scenario)
- Integration with agent monitoring frameworks
- Example: "Uncertainty spike detected - possible prompt injection or novel query type"

**Metrics**:
- Mean uncertainty over time (drift detection)
- Uncertainty spike frequency and duration
- Correlation between uncertainty and task failure rate

**Operational Policy**:
- High uncertainty → escalate to human review
- Sustained uncertainty → fallback to safer default behavior
- Uncertainty threshold tuning based on acceptable error rate

## 5. Uncertainty Under Distribution Shift

**Objective**: Test if uncertainty increases appropriately when data distribution shifts

**Methodology**:
```
1. Test on datasets with known distribution shift (WILDS benchmark, ImageNet-C)
2. Measure uncertainty on shifted data
3. Compare to uncertainty on in-distribution data
4. Verify uncertainty increases with shift severity
```

**Expected Behavior**: Uncertainty should increase as data moves further from training distribution

**Red Flag**: Uncertainty remains low despite distribution shift (overconfident on OOD)

## Adversarial UQ Risk Assessment

- **Critical**: Model confident on misclassified adversarial examples, no OOD detection
- **High**: Poor calibration under attack, uncertainty doesn't increase on adversarial data
- **Medium**: Uncertainty increases on adversarial data but not sufficiently for detection
- **Low**: Well-calibrated under attack, uncertainty effectively detects adversarial inputs

## Integration with Security Testing

This analysis complements adversarial robustness testing and distribution shift robustness testing by adding uncertainty-focused evaluation. When combined with comprehensive vulnerability testing, provides deeper understanding of model behavior under attack.
