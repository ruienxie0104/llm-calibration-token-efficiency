# Activity Label Human Review

The generated review sheet is:

`experiments/v2-mmlu-arc/results/activity_label_sample.csv`

Regenerate the deterministic, model-balanced 100-step sample from the repository root:

```bash
python experiments/v2-mmlu-arc/export_activity_label_sample.py \
  --sample-size 100 \
  --seed 42
```

Each reviewer should work from a separate copy and fill only:

- `human_activity`: one of the nine labels below
- `reviewer`: reviewer identifier
- `notes`: optional ambiguity or rationale

Do not overwrite `predicted_activity`; it records the rule-based label being evaluated.

## Label definitions

| Label | Use when the step primarily… |
| --- | --- |
| `understand` | extracts givens, the target, or the problem setup |
| `recall` | retrieves a rule, definition, formula, or known fact |
| `plan` | chooses or sequences a strategy before executing it |
| `calculate` | performs an arithmetic, algebraic, or symbolic operation |
| `reason` | derives a conclusion or explains an implication |
| `evaluate` | compares choices or eliminates alternatives |
| `verify` | checks an already-derived result |
| `reconsider` | explicitly corrects or revises earlier reasoning |
| `answer` | states the final selected answer |

If a step contains several actions, label its dominant purpose. Use `notes` when two labels
remain equally plausible. Keep the two reviewers independent until both copies are complete;
agreement and Cohen's kappa should be calculated before adjudication.
