"""Markdown and JSON report generation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import Settings


PRIORITY_TITLES = {
    "immediate_review": "즉시 검토 대상",
    "review": "검토 대상",
    "observe": "관찰 대상",
    "excluded": "제외 권장 대상",
}


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
                "현재 설정된 규칙 기준으로 비용 낭비 후보가 발견되지 않았습니다.",
                "",
            ]
        )
        return "\n".join(lines)

    for priority in ("immediate_review", "review", "observe", "excluded"):
        group = [
            item for item in findings if item.get("action_priority") == priority
        ]
        if not group:
            continue
        lines.extend([f"## {PRIORITY_TITLES[priority]}", ""])
        for finding in group:
            _append_finding(lines, finding, recommendations, findings)

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
        recommendation = recommendations[index - 1] if index - 1 < len(recommendations) else ""
        savings = _format_money(finding.get("estimated_monthly_savings"), finding.get("currency"))
        lines.extend(
            [
                f"{index}. {finding.get('resource_type')} {finding.get('resource_id')}",
                f"- 심각도: {finding.get('severity')}",
                f"- 유형: {finding.get('type')}",
                f"- 신뢰도: {finding.get('confidence_score')}",
                f"- 우선순위: {finding.get('action_priority')}",
                f"- 담당/환경: {finding.get('owner')} / {finding.get('environment')}",
                f"- 예상 월 절감액: {savings}",
                f"- 권장 안전 조치: {finding.get('safe_action', 'owner_review')}",
                f"- 권고: {recommendation or finding.get('recommended_action')}",
                "",
            ]
        )

    return "\n".join(lines).strip()


def _append_finding(
    lines: list[str],
    finding: dict[str, Any],
    recommendations: list[str],
    all_findings: list[dict[str, Any]],
) -> None:
    index = all_findings.index(finding)
    recommendation = recommendations[index] if index < len(recommendations) else ""
    resource = finding.get("resource", {})
    evidence = finding.get("evidence", {})
    lines.extend(
        [
            f"### {finding.get('resource_id')}",
            "",
            f"- 유형: `{finding.get('resource_type')}`",
            f"- finding_type: `{finding.get('type')}`",
            f"- 심각도: `{finding.get('severity')}`",
            f"- 신뢰도: `{finding.get('confidence_score')}`",
            f"- 액션 우선순위: `{finding.get('action_priority')}`",
            f"- 리전: `{resource.get('region', '-')}`",
            f"- 담당: `{finding.get('owner', 'unknown')}`",
            f"- 프로젝트: `{finding.get('project', 'unknown')}`",
            f"- 환경: `{finding.get('environment', 'unknown')}`",
            f"- 서비스: `{finding.get('service', 'unknown')}`",
            f"- 예상 현재 월 비용: `{_format_money(finding.get('estimated_current_monthly_cost'), finding.get('currency'))}`",
            f"- 예상 권장 월 비용: `{_format_money(finding.get('estimated_recommended_monthly_cost'), finding.get('currency'))}`",
            f"- 예상 월 절감액: `{_format_money(finding.get('estimated_monthly_savings'), finding.get('currency'))}`",
            f"- 권장 안전 조치: `{finding.get('safe_action', 'owner_review')}`",
            f"- 권장 작업: {finding.get('recommended_action')}",
            f"- 탐지 근거: {finding.get('reason')}",
            f"- 근거 코드: `{', '.join(finding.get('reason_codes', []))}`",
            f"- 근거 데이터: `{json.dumps(evidence, ensure_ascii=False)}`",
            "",
            "권고:",
            "",
            recommendation,
            "",
            "조치 전 확인:",
            "",
        ]
    )
    for item in finding.get("recommended_steps") or finding.get("risk_checklist", []):
        lines.append(f"- {item}")
    lines.append("")


def _format_money(value: Any, currency: Any) -> str:
    if value is None:
        return "계산 불가"
    return f"{float(value):.2f} {currency or ''}".strip()


def _write_json(path: Path, payload: Any) -> None:
    """Write JSON output with readable Korean text."""

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
