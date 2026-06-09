"""Generate human-friendly recommendations from rule findings."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "당신은 클라우드 비용 최적화(FinOps) 보조자입니다. "
    "규칙 기반 분석 결과만 설명하고, 입력 데이터에 없는 비용, 절감액, 우선순위, 신뢰도를 만들지 마세요."
)


def generate_recommendations(
    findings: list[dict[str, Any]], settings: Settings
) -> list[str]:
    """Generate one Korean recommendation message per finding."""

    if not findings:
        return []
    if not settings.llm.enabled or not settings.llm.api_key:
        return [fallback_recommendation(finding, settings) for finding in findings]

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package is not installed; using fallback recommendations")
        return [fallback_recommendation(finding, settings) for finding in findings]

    client = OpenAI(api_key=settings.llm.api_key)
    recommendations: list[str] = []
    for finding in findings:
        try:
            recommendations.append(_generate_one(client, finding, settings))
        except Exception:
            logger.exception(
                "LLM recommendation failed for %s; using fallback",
                finding.get("resource_id"),
            )
            recommendations.append(fallback_recommendation(finding, settings))
    return recommendations


def fallback_recommendation(finding: dict[str, Any], settings: Settings) -> str:
    """Create a deterministic recommendation when LLM is disabled or unavailable."""

    resource_id = finding.get("resource_id", "unknown")
    reason = finding.get("reason", "비용 최적화 후보로 탐지되었습니다.")
    action = finding.get("recommended_action", "소유자 검토")
    priority = finding.get("action_priority", "observe")
    savings = finding.get("estimated_monthly_savings")
    currency = finding.get("currency", "")
    savings_text = (
        f"예상 월 절감액은 {savings:.2f} {currency}입니다."
        if isinstance(savings, (int, float))
        else "가격 정보가 부족해 예상 절감액은 계산하지 않았습니다."
    )

    if finding.get("type") == "unused_ebs_volume":
        sentences = [
            f"{resource_id}는 {reason}",
            "바로 삭제하지 말고 미연결 상태와 소유자를 확인한 뒤 스냅샷을 생성하세요.",
            f"{savings_text} 우선순위는 {priority}이며, 보관 기간 후 삭제 여부를 승인받는 흐름을 권장합니다.",
        ]
    else:
        recommended_type = finding.get("recommended_instance_type")
        type_text = (
            f"현재 타입 {finding.get('current_instance_type')}에서 {recommended_type}로 낮추는 검토 후보입니다."
            if recommended_type
            else "지원되지 않는 인스턴스 타입이므로 자동 타입 제안은 생략했습니다."
        )
        sentences = [
            f"{resource_id}는 {reason}",
            f"{type_text} 실제 변경 전 피크 트래픽과 배치 작업을 확인하세요.",
            f"{savings_text} 우선순위는 {priority}입니다.",
        ]

    return " ".join(sentences[: settings.llm.max_sentences])


def _generate_one(client: Any, finding: dict[str, Any], settings: Settings) -> str:
    """Call the OpenAI API for a single finding."""

    prompt = _build_prompt(finding, settings)
    response = client.chat.completions.create(
        model=settings.llm.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content or ""
    return content.strip() or fallback_recommendation(finding, settings)


def _build_prompt(finding: dict[str, Any], settings: Settings) -> str:
    """Build a constrained FinOps recommendation prompt."""

    safe_payload = {
        "severity": finding.get("severity"),
        "type": finding.get("type"),
        "resource_type": finding.get("resource_type"),
        "resource_id": finding.get("resource_id"),
        "reason": finding.get("reason"),
        "reason_codes": finding.get("reason_codes"),
        "evidence": finding.get("evidence"),
        "recommended_action": finding.get("recommended_action"),
        "safe_action": finding.get("safe_action"),
        "recommended_steps": finding.get("recommended_steps"),
        "confidence_score": finding.get("confidence_score"),
        "action_priority": finding.get("action_priority"),
        "owner": finding.get("owner"),
        "project": finding.get("project"),
        "environment": finding.get("environment"),
        "service": finding.get("service"),
        "estimated_monthly_savings": finding.get("estimated_monthly_savings"),
        "currency": finding.get("currency"),
        "current_instance_type": finding.get("current_instance_type"),
        "recommended_instance_type": finding.get("recommended_instance_type"),
    }
    return (
        "아래 분석 결과를 바탕으로 운영자가 이해하기 쉬운 한국어 권고문을 작성하세요.\n"
        "규칙:\n"
        "- 삭제, 중지, 다운사이즈를 확정적으로 말하지 마세요.\n"
        "- '검토', '확인 후 조치' 형태로 말하세요.\n"
        "- 위험 확인 항목을 1개 이상 포함하세요.\n"
        f"- {settings.llm.max_sentences}문장 이내로 작성하세요.\n"
        "- 입력에 없는 비용, 절감액, 우선순위, 신뢰도를 만들지 마세요.\n\n"
        f"분석 결과:\n{json.dumps(safe_payload, ensure_ascii=False, indent=2)}"
    )
