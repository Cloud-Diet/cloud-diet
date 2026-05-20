"""Generate human-friendly recommendations from rule findings."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "너는 클라우드 비용 최적화(FinOps) 도우미다. "
    "룰 기반 분석 결과만 설명하고, 입력 데이터에 없는 절감액이나 사실은 만들지 않는다."
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

    checklist = finding.get("risk_checklist") or ["운영 영향도를 확인"]
    checklist_text = ", ".join(str(item) for item in checklist[:2])
    resource_id = finding.get("resource_id", "unknown")
    action = finding.get("recommended_action", "조치 검토")
    reason = finding.get("reason", "비용 낭비 후보로 탐지되었습니다.")
    max_sentences = settings.llm.max_sentences

    sentences = [
        f"{resource_id} 리소스는 {reason}",
        f"즉시 변경하기보다는 {action} 대상으로 보고 운영 영향도를 먼저 확인하는 것이 좋습니다.",
        f"조치 전에는 {checklist_text} 항목을 확인해 주세요.",
    ]
    return " ".join(sentences[:max_sentences])


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
        "evidence": finding.get("evidence"),
        "recommended_action": finding.get("recommended_action"),
        "risk_checklist": finding.get("risk_checklist"),
    }
    return (
        "아래 분석 결과를 바탕으로 운영자가 이해하기 쉬운 한국어 권고문을 작성하라.\n"
        "규칙:\n"
        "- 삭제 또는 축소를 확정적으로 말하지 말 것\n"
        "- '검토', '확인 후 조치' 형태로 말할 것\n"
        "- 위험 확인 항목을 1개 이상 포함할 것\n"
        f"- {settings.llm.max_sentences}문장 이내로 작성할 것\n"
        "- 불확실한 비용 절감액을 만들어내지 말 것\n"
        "- 입력 데이터에 없는 정보는 추가하지 말 것\n\n"
        f"분석 결과:\n{json.dumps(safe_payload, ensure_ascii=False, indent=2)}"
    )

