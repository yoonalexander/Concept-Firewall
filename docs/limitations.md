# Limitations

- Sudoku validity is structural reliability, not harmful-content, privacy or policy safety.
- One deterministic trajectory per puzzle confounds internal state with puzzle difficulty; unseen-puzzle prediction does not establish within-puzzle risk or causation.
- A small smoke run is operational validation only. A lack of failures prevents meaningful discrimination/calibration estimates.
- All recorded levels are reconstructed after full generation. No actual early decision, per-level generation timing, restart, prefix resume, intervention, recovery or savings has been demonstrated.
- Tokenizer latents are not generator hidden states or human-readable intentions. Code ID numbering has no numeric geometry.
- Exact duplicate puzzle identities can be grouped, but digit/row/column symmetry leakage requires a further dataset audit.
- Upstream solved/reference equality, grid validity and clue-preserving correctness are distinct labels.
- Windows CUDA support must be measured in the actual environment. The environment snapshot applies to this machine; it is not a portable dependency lock.
- Later natural-language evaluation and any novelty or safety framing require independent evidence. A negative probe result is valid research.
