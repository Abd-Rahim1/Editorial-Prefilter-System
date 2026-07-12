# Feature Scale Normalization Verification

## Feature Scale Analysis
The `dataset.csv` prepared in the historical TFG_Evaluation study normalizes semantic scores (Layer 2) strictly to the `[0.0, 1.0]` range.
Passing values on the 1-5 scale will cause all values to be evaluated into the right-most tree leaves (`> 0.85` or `> 0.95`), creating a highly skewed probability distribution.

## Verification Matrix

| Feature | Layer 2 Raw Scale | Training Scale | Online Transformation | Parity Status |
|---|---|---|---|---|
| `argumentative_quality` | 1-5 or 0-1 (LLM dependent) | 0.0 - 1.0 | None (Requires 0-1 input) | **MATCH** (Must ensure 0-1 passing in Layer 4) |
| `experimental_strength` | 1-5 or 0-1 (LLM dependent) | 0.0 - 1.0 | None (Requires 0-1 input) | **MATCH** |
| `methodological_strength` | 1-5 or 0-1 (LLM dependent) | 0.0 - 1.0 | None (Requires 0-1 input) | **MATCH** |
| `overall_quality` | 1-5 or 0-1 (LLM dependent) | 0.0 - 1.0 | None (Requires 0-1 input) | **MATCH** |
| `scope_alignment` | 1-5 or 0-1 (LLM dependent) | 0.0 - 1.0 | None (Requires 0-1 input) | **MATCH** |
| `structural_completeness` | 1-5 or 0-1 (LLM dependent) | 0.0 - 1.0 | None (Requires 0-1 input) | **MATCH** |

## Conclusion
Online feature construction accurately mirrors the training architecture by NOT applying double-scaling. Layer 4 MUST ensure semantic outputs are passed into Layer 3 normalized to `0.0 - 1.0`.
