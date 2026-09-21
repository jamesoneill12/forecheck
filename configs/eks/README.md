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
`forecheck-train-8b` to run the Nimble-parity Granite-3.3-8B recipe instead, or for
`configs/eks/train-encoder-b200-recipe.yaml` / `forecheck-train-encoders` to train both
encoder-classifier-arm configs (`encoder-modernbert-large.yaml`,
`encoder-granite-embedding-r2.yaml`) back to back. To run the two arms in parallel
on one node (one GPU each), submit the per-arm recipes instead:

```bash
ai-infra eks submit-job /tmp/forecheck-job --recipe configs/eks/train-encoder-modernbert-large-b200-recipe.yaml --name forecheck-enc-modernbert --gpu-type B200 --instance-type ml.p6-b200.48xlarge --az us-east-2a --gpus-per-pod 1 --cpus-per-pod 6 --memory-per-pod 100 --efas 0 --region us-east-2 --cluster eks-fsdp-cluster --fsx-id fs-0979a8395b825c774
ai-infra eks submit-job /tmp/forecheck-job --recipe configs/eks/train-encoder-granite-embedding-r2-b200-recipe.yaml --name forecheck-enc-granite-r2 --gpu-type B200 --instance-type ml.p6-b200.48xlarge --az us-east-2a --gpus-per-pod 1 --cpus-per-pod 6 --memory-per-pod 100 --efas 0 --region us-east-2 --cluster eks-fsdp-cluster --fsx-id fs-0979a8395b825c774
```

Swap in `configs/eks/train-2b-b200-v3-recipe.yaml` / `forecheck-train-2b-v3` to
generate onto `/opt/ml/fsx/forecheck/data/v3` and additionally evaluate the two
policy-generalisation splits from ADR 0010 (`heldout_policy_kind`,
`heldout_policy_phrasing`, both `synthetic_heldout_adversarial`) for the hf and
`rule_baseline` backends:

```bash
ai-infra eks submit-job /tmp/forecheck-job --recipe configs/eks/train-2b-b200-v3-recipe.yaml --name forecheck-train-2b-v3 --gpu-type B200 --instance-type ml.p6-b200.48xlarge --az us-east-2a --gpus-per-pod 1 --cpus-per-pod 2 --memory-per-pod 60 --efas 0 --region us-east-2 --cluster eks-fsdp-cluster --fsx-id fs-0979a8395b825c774 --follow-logs
```

Unlike the decoder recipes, the encoder recipes do not regenerate or split the
dataset -- they guard on `/opt/ml/fsx/forecheck/data/v2/train.jsonl` already existing
(run `train-2b-b200-recipe.yaml` or `forecheck data generate`/`split` first if it does
not) and train/calibrate/evaluate the encoder config against it.

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

`train-encoder-b200-recipe.yaml` instead trains the encoder classifier arm (a pooled
backbone plus an 11-logit head, see `configs/training/README.md`) against an
already-generated dataset, for both configured bases, calibrating and evaluating each.

## Guardian zero-shot baselines

`configs/eks/eval-guardian-baselines-b200-recipe.yaml` evaluates the three zero-shot
guardian baselines (`configs/baselines/granite-guardian-3.3-8b.yaml`,
`llama-guard-4-12b.yaml`, `gpt-oss-safeguard-20b.yaml`; see ADR 0009) against
`test` and `heldout_family`, with and without `--strip-identity`, writing to
`/opt/ml/fsx/forecheck/runs/baselines/<model>/reports/<split>[-noid]`. It guards on
`/opt/ml/fsx/forecheck/data/v2/train.jsonl` already existing, same as the encoder
recipes:

```bash
ai-infra eks submit-job /tmp/forecheck-job --recipe configs/eks/eval-guardian-baselines-b200-recipe.yaml --name forecheck-guardian-baselines --gpu-type B200 --instance-type ml.p6-b200.48xlarge --az us-east-2a --gpus-per-pod 1 --cpus-per-pod 2 --memory-per-pod 60 --efas 0 --region us-east-2 --cluster eks-fsdp-cluster --fsx-id fs-0979a8395b825c774
```

## Before a production run

Build and push a pinned forecheck image to ECR instead of `pip install -e` at job start,
and set `ecr_image` accordingly. ECR tags are immutable; use a new tag per build.

## Estimated cost

~2B LoRA on ~50k synthetic examples, seq ≤ 4k: well under one node-hour on B200. The
3B and 8B/7B (Nimble-parity) recipes scale to a few node-hours; see `configs/training/`.
