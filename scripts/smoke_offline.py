#!/usr/bin/env python3
"""End-to-end offline smoke test: fixtures -> mock backend -> calibrate -> evaluate ->
policy -> API, all without torch or a network call. Deterministic; exits non-zero on
any failure. Intended to run in well under 60 seconds and is wired into CI.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import typer
from starlette.testclient import TestClient

from forecheck.api.app import create_app
from forecheck.api.settings import Settings
from forecheck.calibration.fit import fit_bundle
from forecheck.calibration.store import save_bundle
from forecheck.cli_cmds._common import calibrators_from_bundle
from forecheck.cli_cmds.data import verify as verify_fixtures
from forecheck.contracts import CalibrationMethod, Example, LabelValue, RiskDimension
from forecheck.data.io import read_jsonl, sha256_file
from forecheck.evaluation.report import EvaluationClass
from forecheck.evaluation.runner import evaluate
from forecheck.inference import MockBackend
from forecheck.policies.builtin import load_builtin_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"
EXAMPLE_REQUEST_PATH = REPO_ROOT / "examples" / "requests" / "injected_exfiltration.json"
OUT_DIR = REPO_ROOT / "outputs" / "smoke_offline"

_SYNTHETIC_DISCLAIMER = "Synthetic data. No real-world safety claim is made."


def _fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def _score_split(
    backend: MockBackend, examples: list[Example]
) -> tuple[dict[RiskDimension, list[float]], dict[RiskDimension, list[LabelValue]]]:
    raw_scores = backend.score_batch([e.context for e in examples])
    scores: dict[RiskDimension, list[float]] = {d: [] for d in RiskDimension}
    labels: dict[RiskDimension, list[LabelValue]] = {d: [] for d in RiskDimension}
    for example, raw in zip(examples, raw_scores, strict=True):
        for dimension in RiskDimension:
            value = raw.scores.get(dimension)
            if value is None:
                continue
            scores[dimension].append(value)
            labels[dimension].append(example.labels.values[dimension])
    return scores, labels


def main() -> int:
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    started = time.perf_counter()
    summary: list[str] = []

    try:
        verify_fixtures(FIXTURES_DIR)
    except typer.Exit as exc:
        if exc.exit_code:
            _fail(f"fixture verification failed (exit code {exc.exit_code})")
    summary.append(f"1. fixtures verified: manifests + leakage OK at {FIXTURES_DIR}")

    calibration_path = FIXTURES_DIR / "calibration.jsonl"
    test_path = FIXTURES_DIR / "test.jsonl"
    calibration_examples = read_jsonl(calibration_path)
    test_examples = read_jsonl(test_path)
    if not calibration_examples or not test_examples:
        _fail("calibration or test split is empty")
    summary.append(
        f"2. loaded {len(calibration_examples)} calibration + {len(test_examples)} test examples"
    )

    backend = MockBackend()
    scores, labels = _score_split(backend, calibration_examples)
    # Fixture calibration split is too small for the library default (min_positives=25).
    fit_report = fit_bundle(
        scores,
        labels,
        CalibrationMethod.TEMPERATURE,
        backend_model_id=backend.model_info.model_id,
        prompt_contract_hash=backend.model_info.prompt_contract_hash,
        dataset_sha256=sha256_file(calibration_path),
        split_name="calibration",
        min_positives=3,
    )
    summary.append(
        f"3. fitted temperature calibration; macro ECE "
        f"{fit_report.macro_ece_before:.4f} -> {fit_report.macro_ece_after:.4f}"
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = OUT_DIR / "calibration" / "bundle.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    save_bundle(fit_report.bundle, bundle_path)
    summary.append(f"4. saved calibration bundle -> {bundle_path}")

    engine = load_builtin_engine("conservative")
    report = evaluate(
        backend,
        test_examples,
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        calibrators=calibrators_from_bundle(fit_report.bundle),
        calibrator_bundle=fit_report.bundle,
        engine=engine,
        dataset_sha256=sha256_file(test_path),
    )
    backend.close()
    summary.append(f"5. evaluated {len(test_examples)} test examples with the conservative bundle")

    if len(report.dimensions) != len(RiskDimension):
        _fail(f"expected {len(RiskDimension)} dimensions in report, got {len(report.dimensions)}")
    summary.append(f"6. report covers all {len(report.dimensions)} risk dimensions")

    reports_dir = OUT_DIR / "reports" / "test"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report.to_json(reports_dir / "report.json")
    report.to_markdown(reports_dir / "report.md")
    markdown = (reports_dir / "report.md").read_text(encoding="utf-8")
    if EvaluationClass.SYNTHETIC_IN_DISTRIBUTION.value.upper() not in markdown:
        _fail("evaluation report is missing the evaluation-class banner")
    if _SYNTHETIC_DISCLAIMER not in markdown:
        _fail("evaluation report is missing the synthetic-data disclaimer sentence")
    summary.append(f"7. wrote {reports_dir / 'report.json'} and report.md; banner + disclaimer OK")

    settings = Settings(backend="mock", calibration_path=bundle_path, policy_bundle="conservative")
    app = create_app(settings)
    with TestClient(app) as client:
        summary.append("8. started FastAPI app in-process (mock backend, fitted bundle loaded)")

        request_payload = json.loads(EXAMPLE_REQUEST_PATH.read_text(encoding="utf-8"))
        classify_response = client.post("/v1/classify", json=request_payload)
        if classify_response.status_code != 200:
            _fail(
                f"POST /v1/classify returned {classify_response.status_code}: "
                f"{classify_response.text}"
            )
        classify_body = classify_response.json()
        probabilities = [
            s["probability"] for s in classify_body["scores"] if s["probability"] is not None
        ]
        if not probabilities:
            _fail("POST /v1/classify returned no calibrated probabilities")
        if classify_body["calibration"]["method"] == CalibrationMethod.NONE.value:
            _fail("POST /v1/classify reported calibration.method == 'none'")
        summary.append(
            f"9. POST /v1/classify: {len(probabilities)} probabilities, "
            f"calibration.method={classify_body['calibration']['method']}"
        )

        policy_response = client.post(
            "/v1/policies/evaluate", json={"context": request_payload["context"]}
        )
        if policy_response.status_code != 200:
            _fail(f"POST /v1/policies/evaluate returned {policy_response.status_code}")
        policy_body = policy_response.json()
        if not policy_body.get("decision"):
            _fail("POST /v1/policies/evaluate returned no decision")
        if not policy_body.get("matched_rules"):
            _fail("POST /v1/policies/evaluate matched no rules for an injected-exfiltration action")
        summary.append(
            f"10. POST /v1/policies/evaluate: decision={policy_body['decision']}, "
            f"matched_rules={len(policy_body['matched_rules'])}"
        )

    elapsed = time.perf_counter() - started
    summary.append(f"11. total elapsed: {elapsed:.2f}s")
    summary.append("12. SMOKE OK")
    summary.append(f"13. fixtures dir: {FIXTURES_DIR}")
    summary.append(f"14. artifacts dir: {OUT_DIR}")
    summary.append("15. backend=mock, calibration=temperature, policy_bundle=conservative")

    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
