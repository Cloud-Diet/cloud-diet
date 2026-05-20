from pathlib import Path
from types import SimpleNamespace

from app.reporters.markdown_reporter import build_daily_summary, save_report_bundle


def test_save_report_bundle_writes_files(tmp_path):
    settings = SimpleNamespace(
        output_dir=tmp_path,
        analysis_days=14,
    )
    findings = [
        {
            "severity": "high",
            "type": "unused_ebs_volume",
            "resource_type": "EBS",
            "resource_id": "vol-test",
            "reason": "18일 동안 EC2 인스턴스에 연결되지 않은 EBS 볼륨입니다.",
            "evidence": {"detached_days": 18},
            "recommended_action": "삭제 또는 스냅샷 전환 검토",
            "risk_checklist": ["스냅샷 백업 필요 여부 확인"],
            "resource": {"region": "ap-northeast-2"},
        }
    ]

    paths = save_report_bundle([], findings, ["권고문"], settings)

    assert Path(paths["resources"]).exists()
    assert Path(paths["findings"]).exists()
    assert Path(paths["report"]).exists()


def test_build_daily_summary_contains_resource_id():
    settings = SimpleNamespace(analysis_days=14)
    findings = [
        {
            "severity": "high",
            "type": "unused_ebs_volume",
            "resource_type": "EBS",
            "resource_id": "vol-test",
            "reason": "18일 동안 연결되지 않음",
            "evidence": {"detached_days": 18},
            "recommended_action": "삭제 또는 스냅샷 전환 검토",
            "risk_checklist": ["스냅샷 확인"],
        }
    ]

    summary = build_daily_summary(findings, ["권고문"], settings)

    assert "vol-test" in summary
    assert "Cloud Diet" in summary

