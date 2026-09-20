# EKS training recipes (ai-infra)

These recipes run the real-model training path on the team's B200 EKS pool. **None of
them is launched automatically.** Each consumes a shared GPU node and needs explicit
approval.

## Prerequisites

1. AWS credentials in the shell (`developer-tools:aws-auth`, or the team's
   `hammer agent-auth` flow).
2. A free node in the pool — check before submitting; the pool is multi-tenant and
   fluctuates:
   ```bash
   kubectl get nodes -l custom-label=pretraining-tests -o wide
   ```
3. The FSx filesystem `fs-0979a8395b825c774` (us-east-2a) selected when prompted by
   `--use-fsx`. Do not select the us-east-2b filesystem.

## Submit

From the forecheck repo root:

```bash
ai-infra eks submit-job scripts --recipe configs/eks/train-1b-b200-recipe.yaml --name forecheck-train-1b --gpu-type B200 --instance-type p6-b200.48xlarge --az us-east-2a --custom-label pretraining-tests --region us-east-2 --cluster eks-fsdp-cluster --use-fsx --follow-logs
```

Job names are prefixed with your username by ai-infra and limited to 63 characters.

## What the recipe does

Installs `forecheck[train]` into a stock NGC PyTorch image, generates a medium synthetic
dataset offline onto FSx, splits it (family-level, leakage-checked), LoRA-trains the
~1B config, fits calibration on the `calibration` split, and writes two evaluation
reports (`synthetic_in_distribution` on `test`, `synthetic_heldout_adversarial` on
`heldout_family`) under `/opt/ml/fsx/forecheck/runs/<run>/`.

## Before a production run

Build and push a pinned forecheck image to ECR instead of `pip install -e` at job start,
and set `ecr_image` accordingly. ECR tags are immutable; use a new tag per build.

## Estimated cost

~1B LoRA on ~50k synthetic examples, seq ≤ 4k: well under one node-hour on 8×B200. The
4B and 8-9B recipes scale to a few node-hours; see `configs/training/`.
