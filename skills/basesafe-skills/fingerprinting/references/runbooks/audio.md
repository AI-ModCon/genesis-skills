# Audio Runbook

Use this runbook for speech, speaker, audio event, or other acoustic systems.

## Inspect

- waveform and spectrogram preprocessing
- sample-rate assumptions and augmentation
- transcription or classification outputs
- training and evaluation scripts
- streaming or batch inference paths

## Capture

- task type: transcription, classification, speaker ID, retrieval
- feature pipeline: mel spectrograms, embeddings, raw waveform
- architecture family and framework
- latency constraints if real-time
- robustness evidence for noise and channel variation

## Common Hooks

- attack surface: adversarial audio, channel corruption, spoofing
- uncertainty hooks: confidence under noise or accent shift
- explainability hooks: temporal saliency, segment-level attribution

## Typical Unknowns

- mic and environment assumptions
- multilingual or accent coverage
- streaming degradation behavior

