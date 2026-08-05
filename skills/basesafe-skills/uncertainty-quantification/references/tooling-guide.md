# Uncertainty Quantification Tooling Guide

Comprehensive guide to tools and libraries for uncertainty quantification across calibration, conformal prediction, Bayesian methods, OOD detection, and adversarial testing.

## Calibration Tools

### NetCal
**Install**: `pip install netcal`  
**Use Cases**: Temperature scaling, Platt scaling, reliability diagrams  
**Best For**: Post-hoc calibration of classification models  
**Key Features**:
- Multiple calibration methods (temperature, Platt, isotonic, beta)
- Built-in reliability diagrams
- ECE, MCE, and other calibration metrics
- Works with scikit-learn, PyTorch, TensorFlow

### scikit-learn Calibration
**Install**: Included with scikit-learn  
**Use Cases**: Calibration curves, Platt and isotonic scaling  
**Best For**: Quick calibration for scikit-learn models  
**Key Features**:
- `CalibratedClassifierCV` for calibration
- `calibration_curve` for plotting
- Brier score, log loss metrics

### uncertainty-toolbox
**Install**: `pip install uncertainty-toolbox`  
**Use Cases**: Calibration metrics, proper scoring, comprehensive UQ evaluation  
**Best For**: Regression calibration, comprehensive analysis  
**Key Features**:
- Calibration error, sharpness, proper scoring rules
- Prediction interval coverage
- Adversarial group calibration
- Visualization tools

## Conformal Prediction

### MAPIE
**Install**: `pip install mapie`  
**Use Cases**: Conformal prediction for classification and regression  
**Best For**: Production-ready prediction intervals with coverage guarantees  
**Key Features**:
- Distribution-free prediction sets
- Adaptive conformal prediction
- Time series conformal prediction

### crepes
**Install**: `pip install crepes`  
**Use Cases**: Conformal regressors and classifiers  
**Best For**: Fast conformal prediction with minimal overhead  

## Bayesian and Ensemble Methods

### PyTorch MC Dropout
**Install**: Included with PyTorch  
**Use Cases**: Epistemic uncertainty via dropout at inference  
**Best For**: Deep learning models with existing dropout layers  

### TensorFlow Probability
**Install**: `pip install tensorflow-probability`  
**Use Cases**: Bayesian layers, variational inference  
**Best For**: Bayesian neural networks in TensorFlow  

### Pyro
**Install**: `pip install pyro-ppl`  
**Use Cases**: Probabilistic programming, Bayesian deep learning  
**Best For**: Custom probabilistic models  

### Edward2
**Install**: Part of TensorFlow  
**Use Cases**: Bayesian neural networks in TensorFlow  
**Best For**: Research-oriented Bayesian modeling  

## OOD Detection

### PyOD
**Install**: `pip install pyod`  
**Use Cases**: Outlier and anomaly detection (Isolation Forest, One-Class SVM, LOF)  
**Best For**: Identifying out-of-distribution samples  

### ADBench
**Install**: From GitHub (https://github.com/Minqi824/ADBench)  
**Use Cases**: Anomaly detection benchmarking  

### torch-uncertainty
**Install**: `pip install torch-uncertainty`  
**Use Cases**: OOD detection methods for PyTorch (energy-based, Mahalanobis distance)  

## Metrics and Evaluation

### uncertainty-toolbox
**Metrics**: ECE, sharpness, proper scoring, interval coverage  

### scikit-learn Metrics
**Metrics**: Brier score, log loss, calibration curve  

### Custom Metrics
- **Coverage**: Percentage of true values within prediction intervals
- **Interval Width**: Average width of prediction intervals
- **CRPS**: Continuous Ranked Probability Score

## Agent and LLM-Specific Methods

### Self-Consistency
**Approach**: Sample multiple outputs, measure variance  
**Use Case**: Measure epistemic uncertainty in generation  

### Logit Variance
**Approach**: Track logit variance across tokens  
**Use Case**: Token-level uncertainty in generation  

### Attention Entropy
**Approach**: Compute entropy over attention weights  
**Use Case**: Identify uncertain reasoning steps  

### Citation Confidence
**Approach**: Measure grounding quality  
**Use Case**: RAG systems - track retrieval scores and evidence sufficiency  

## Adversarial Uncertainty Testing

### Adversarial Robustness Toolbox (ART)
**Install**: `pip install adversarial-robustness-toolbox`  
**Use Cases**: Generate adversarial examples for uncertainty testing  
**Best For**: Testing calibration under adversarial attack  
**Key Features**:
- 50+ adversarial attacks (FGSM, PGD, C&W, DeepFool)
- Compatibility with TensorFlow, PyTorch, scikit-learn

### Foolbox
**Install**: `pip install foolbox`  
**Use Cases**: Clean API for adversarial example generation  
**Best For**: Rapid adversarial testing with minimal code  

### WILDS
**Install**: `pip install wilds`  
**Use Cases**: Real-world distribution shift datasets  
**Best For**: Testing uncertainty under natural distribution shift  
**Key Features**:
- 10+ distribution shift benchmarks
- Healthcare, satellite, text domains

### ImageNet-C
**Install**: `pip install imagecorruptions`  
**Use Cases**: Corruption robustness benchmark  
**Best For**: Testing uncertainty under corruptions (noise, blur, weather, digital effects)  

## Tool Selection Guide

| Use Case | Recommended Tool | Alternative |
|----------|-----------------|-------------|
| **Classification calibration** | NetCal | scikit-learn CalibratedClassifierCV |
| **Regression calibration** | uncertainty-toolbox | MAPIE |
| **Prediction intervals** | MAPIE | crepes |
| **Epistemic uncertainty** | MC Dropout | TensorFlow Probability |
| **OOD detection** | PyOD | torch-uncertainty |
| **Adversarial testing** | ART | Foolbox |
| **Distribution shift** | WILDS | ImageNet-C |
| **LLM uncertainty** | Self-consistency | Logit variance |

## Production Considerations

- **Start Simple**: Temperature scaling before Bayesian methods
- **Validate Thoroughly**: Test on IID, OOD, and adversarial data
- **Monitor Drift**: Track calibration metrics in production
- **Combine Methods**: Use multiple signals (calibration + OOD + conformal)
- **Document**: Record which tools, versions, and validation protocols used
