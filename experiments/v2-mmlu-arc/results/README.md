# V2 Result Artifacts

This directory is the canonical output location for every V2 script. Paths are
resolved relative to the scripts, so commands can be run from any working
directory.

## Reproducibility set

The following files form the reviewable V2 result set:

| File | Purpose | Current repository state |
| --- | --- | --- |
| `raw_responses_v2.json` | API responses with contextual confidence rerun | Missing; requires API rerun |
| `traces_final.json` | Valid, successfully parsed traces | Missing; regenerate after API rerun |
| `calibration_final.json` | Calibration metrics | Missing; regenerate after API rerun |
| `conformance_final.json` | GLM-5.2 reference conformance | Missing; regenerate after API rerun |
| `conformance_deepseek_ref.json` | DeepSeek reference conformance | Present, but must be regenerated after the alignment fix |
| `discovery_final.json` | Process discovery summary | Missing; regenerate after API rerun |
| `entropy_step_analysis.json` | Entropy and distribution analysis | Present, but must be regenerated after the distance/JSD fix |
| `full_metrics_final.csv` | Consolidated model metrics | Missing; regenerate after API rerun |

Generated checkpoints such as `raw_responses.json` and
`confidence_v2_*.json` remain ignored because they can be incomplete. Promote
only a completed, validated run to the filenames above.

## Regeneration workflow

From the repository root, after activating the environment and exporting a
rotated `OLLAMA_API_KEY`:

```bash
python experiments/v2-mmlu-arc/experiment_v2.py
python experiments/v2-mmlu-arc/run_pm_step4.py
python experiments/v2-mmlu-arc/run_entropy_step_analysis.py
python experiments/v2-mmlu-arc/run_conformance_deepseek_ref.py
python experiments/v2-mmlu-arc/generate_v2_figures.py
python scripts/check_v2_results.py
```

`experiment_v2.py` writes an ignored `raw_responses.json` checkpoint after
every case. It promotes that checkpoint to tracked `raw_responses_v2.json`
only when all supported models and questions have successful answer and
confidence responses. API failures are retried on the next run and replace
their failed checkpoint entry instead of being appended as additional cases.

Do not treat the two legacy JSON files currently present as corrected results.
Their source inputs are absent, so they are retained only as historical output
until the experiment is rerun.

Check completeness and structural validity with:

```bash
python scripts/check_v2_results.py
```
