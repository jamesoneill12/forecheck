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

Stage only what the job needs into a directory named exactly `forecheck-job` — ai-infra uploads the directory itself and the `fin-base-training` image's `setup_and_run.sh` syncs the upload into `/workspace`, so the code lands at `/workspace/forecheck-job/`, which is where the recipe command `cd`s (the upload is scanned, and `docs/`/`tests/` are not required on the node):

```bash
rm -rf /tmp/forecheck-job && mkdir -p /tmp/forecheck-job && cp -R pyproject.toml uv.lock README.md LICENSE NOTICE src configs policies scripts /tmp/forecheck-job/
```

Then submit. Both recipes train on a single GPU, so they request 1 GPU / 6 CPU / 100 Gi (partially used B200 nodes are usually ~95% CPU-committed, so a larger CPU ask will not schedule) and, with no `--custom-label`, schedules onto any unlabelled B200 node in us-east-2a that has a spare GPU (labelled pools such as `pretraining-tests` are excluded by ai-infra when no label is given):

```bash
ai-infra eks submit-job /tmp/forecheck-job --recipe configs/eks/train-2b-b200-recipe.yaml --name forecheck-train-2b --gpu-type B200 --instance-type ml.p6-b200.48xlarge --az us-east-2a --gpus-per-pod 1 --cpus-per-pod 6 --memory-per-pod 100 --efas 0 --region us-east-2 --cluster eks-fsdp-cluster --fsx-id fs-0979a8395b825c774 --follow-logs
```

Swap the recipe/name for `configs/eks/train-8b-b200-recipe.yaml` /
`forecheck-train-8b` to run the Nimble-parity Granite-3.3-8B recipe instead.

Job names are prefixed with your username by ai-infra and limited to 63 characters.

## What the recipe does

Installs `forecheck[train]` into the team's `ai/fin-base-training:latest` ECR image
(NGC PyTorch 26.02 base, Python 3.12; ai-infra rejects non-ECR image references),
generates a medium synthetic
dataset offline onto FSx, splits it (family-level, leakage-checked), LoRA-trains the
configured size (`configs/training/2b.yaml`, `3b.yaml`, `8b.yaml`, or `olmo3-7b.yaml`),
fits calibration
on the `calibration` split, and writes two evaluation reports
(`synthetic_in_distribution` on `test`, `synthetic_heldout_adversarial` on
`heldout_family`) under `/opt/ml/fsx/forecheck/runs/<run>/`.

## Before a production run

Build and push a pinned forecheck image to ECR instead of `pip install -e` at job start,
and set `ecr_image` accordingly. ECR tags are immutable; use a new tag per build.

## Estimated cost

~2B LoRA on ~50k synthetic examples, seq ≤ 4k: well under one node-hour on B200. The
3B and 8B/7B (Nimble-parity) recipes scale to a few node-hours; see `configs/training/`.
