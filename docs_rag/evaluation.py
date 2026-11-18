import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from .service import DEPENDENCY_ERRORS, TemporarilyUnavailable, answer, retrieve


def evaluate(path: Path, store, models):
    cases = json.loads(path.read_text(encoding="utf-8"))
    report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "models": {
            "embedding": {"name": models.settings.embedding_model, "digest": models.embedding_digest()},
            "generation": {
                "name": models.settings.answer_model,
                "digest": models.model_digest(models.settings.answer_model),
            },
        },
        "cases": [],
    }
    covered = []
    for case in cases:
        expected = case["expected_sections"]
        started = perf_counter()
        failure = {}
        try:
            passages = retrieve(case["question"], store, models)
        except DEPENDENCY_ERRORS as exc:
            passages = []
            failure = {"stage": "retrieval", "error_type": type(exc).__name__}
        retrieved_at = perf_counter()
        result = TemporarilyUnavailable()
        if passages:
            try:
                result = answer(case["question"], passages, models)
            except DEPENDENCY_ERRORS as exc:
                failure = {"stage": "generation", "error_type": type(exc).__name__}
        generated_at = perf_counter()
        ranked = [f"{passage.document_slug}#{passage.anchor}" for passage in passages]
        rank = next((index for index, section in enumerate(ranked, start=1) if section in expected), None)
        expected_status = "answered" if expected else "insufficient_evidence"
        row = {
            **case,
            "retrieved_sections": ranked,
            "first_expected_rank": rank,
            "expected_status": expected_status,
            "status_matches": result.status == expected_status,
            "retrieval_ms": round((retrieved_at - started) * 1000),
            "generation_ms": round((generated_at - retrieved_at) * 1000),
            "result": result.model_dump(),
        }
        if failure:
            row["technical_failure"] = failure
        report["cases"].append(row)
        if expected:
            covered.append(row)
    report["retrieval"] = {
        "covered_questions": len(covered),
        "hit_at_1": sum(row["first_expected_rank"] == 1 for row in covered),
        "hit_at_3": sum(row["first_expected_rank"] is not None for row in covered),
    }
    report["automatic_checks_passed"] = (
        bool(covered)
        and report["retrieval"]["hit_at_3"] == len(covered)
        and all(row["status_matches"] for row in report["cases"])
    )
    return report
