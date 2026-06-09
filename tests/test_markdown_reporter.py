from pathlib import Path
from types import SimpleNamespace

from app.reporters.markdown_reporter import build_daily_summary, save_report_bundle


def test_save_report_bundle_writes_files(tmp_path):
    settings = SimpleNamespace(
        output_dir=tmp_path,
        analysis_days=14,
    )
    findings = [_finding()]

    paths = save_report_bundle([], findings, ["권고문"], settings)

    assert Path(paths["resources"]).exists()
    assert Path(paths["findings"]).exists()
    assert Path(paths["report"]).exists()


def test_build_daily_summary_contains_resource_id_and_new_fields():
    settings = SimpleNamespace(analysis_days=14)
    summary = build_daily_summary([_finding()], ["권고문"], settings)

    assert "vol-test" in summary
    assert "Cloud Diet" in summary
    assert "신뢰도" in summary
    assert "8.00 USD" in summary


def _finding():
    return {
        "severity": "high",
        "type": "unused_ebs_volume",
        "resource_type": "EBS",
        "resource_id": "vol-test",
        "reason": "18일 동안 연결되지 않은 EBS 볼륨입니다.",
        "evidence": {"detached_days": 18},
        "recommended_action": "스냅샷 생성 후 삭제 검토",
        "safe_action": "snapshot_before_delete",
        "recommended_steps": ["스냅샷 백업 필요 여부를 확인합니다."],
        "confidence_score": 80,
        "action_priority": "immediate_review",
        "owner": "backend-team",
        "project": "capstone",
        "environment": "dev",
        "service": "api",
        "estimated_monthly_savings": 8.0,
        "currency": "USD",
        "resource": {"region": "ap-northeast-2"},
    }
