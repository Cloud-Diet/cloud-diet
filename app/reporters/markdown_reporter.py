"""Markdown and JSON report generation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import Settings


def save_report_bundle(
    resources: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    recommendations: list[str],
    settings: Settings,
) -> dict[str, Path]:
    """Write resources, findings, and Markdown report files to OUTPUT_DIR."""

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resources_path = settings.output_dir / f"resources_{timestamp}.json"
    findings_path = settings.output_dir / f"findings_{timestamp}.json"
    report_path = settings.output_dir / f"report_{timestamp}.md"

    _write_json(resources_path, resources)
    _write_json(findings_path, findings)
    report_path.write_text(
        render_markdown_report(findings, recommendations, settings),
        encoding="utf-8",
    )

    return {
        "resources": resources_path,
        "findings": findings_path,
        "report": report_path,
    }


def render_markdown_report(
    findings: list[dict[str, Any]], recommendations: list[str], settings: Settings
) -> str:
    """Render a detailed Markdown report body."""

    generated_at = datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Cloud Diet 일일 비용 최적화 리포트",
        "",
        f"- 생성 시각: `{generated_at}`",
        f"- 분석 기간: 최근 `{settings.analysis_days}`일",
        f"- 탐지 건수: `{len(findings)}`",
        "",
    ]

    if not findings:
        lines.extend(
            [
                "## 결과",
                "",
                "현재 설정된 룰 기준으로 비용 낭비 후보가 발견되지 않았습니다.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## 탐지 결과", ""])
    for index, finding in enumerate(findings, start=1):
        recommendation = recommendations[index - 1] if index - 1 < len(recommendations) else ""
        resource = finding.get("resource", {})
        evidence = finding.get("evidence", {})
        lines.extend(
            [
                f"### {index}. {finding.get('resource_type')} {finding.get('resource_id')}",
                "",
                f"- 심각도: `{finding.get('severity')}`",
                f"- 유형: `{finding.get('type')}`",
                f"- 리전: `{resource.get('region', '-')}`",
                f"- 탐지 이유: {finding.get('reason')}",
                f"- 권고 조치: {finding.get('recommended_action')}",
                f"- 근거 데이터: `{json.dumps(evidence, ensure_ascii=False)}`",
                "",
                "#### 권고문",
                "",
                recommendation,
                "",
                "#### 조치 전 확인",
                "",
            ]
        )
        for item in finding.get("risk_checklist", []):
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def build_daily_summary(
    findings: list[dict[str, Any]], recommendations: list[str], settings: Settings
) -> str:
    """Build one concise message for Discord or Slack delivery."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "[Cloud Diet] 일일 비용 최적화 후보 리포트",
        f"- 생성 시각: {generated_at}",
        f"- 분석 기간: 최근 {settings.analysis_days}일",
        f"- 탐지 건수: {len(findings)}",
        "",
    ]

    for index, finding in enumerate(findings, start=1):
        evidence = finding.get("evidence", {})
        recommendation = recommendations[index - 1] if index - 1 < len(recommendations) else ""
        lines.extend(
            [
                f"{index}. {finding.get('resource_type')} {finding.get('resource_id')}",
                f"- 심각도: {finding.get('severity')}",
                f"- 유형: {finding.get('type')}",
                f"- 근거: {finding.get('reason')}",
                f"- 권고: {finding.get('recommended_action')}",
                f"- 확인 필요: {', '.join(finding.get('risk_checklist', [])[:3])}",
            ]
        )
        if evidence:
            lines.append(f"- evidence: {json.dumps(evidence, ensure_ascii=False)}")
        if recommendation:
            lines.append(f"- 설명: {recommendation}")
        lines.append("")

    return "\n".join(lines).strip()


def _write_json(path: Path, payload: Any) -> None:
    """Write JSON output with readable Korean text."""

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

