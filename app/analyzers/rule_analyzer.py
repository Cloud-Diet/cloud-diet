"""Rule-based waste candidate detection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.pricing.price_estimator import estimate_finding_costs


SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}
DOWNGRADE_MAP = {
    "t3.large": "t3.medium",
    "t3.medium": "t3.small",
    "t3.small": "t3.micro",
}
TAG_KEYS = {
    "owner": ("Owner", "owner", "Team", "team"),
    "project": ("Project", "project"),
    "environment": ("Environment", "environment", "Env", "env"),
    "service": ("Service", "service", "Name"),
}
PROTECTED_TAG_MARKERS = ("prod", "production", "critical")
LOWER_ENV_MARKERS = ("dev", "test", "staging")


def analyze_resources(
    resources: list[dict[str, Any]], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    """Analyze normalized resources and return ordered findings."""

    findings: list[dict[str, Any]] = []
    for resource in resources:
        if resource.get("resource_type") == "EC2":
            findings.extend(analyze_ec2(resource, rules))
        elif resource.get("resource_type") == "EBS":
            findings.extend(analyze_ebs(resource, rules))

    return sorted(
        findings,
        key=lambda item: (
            SEVERITY_RANK.get(str(item.get("severity")), 99),
            -int(item.get("confidence_score") or 0),
            str(item.get("resource_type")),
            str(item.get("resource_id")),
        ),
    )


def analyze_ec2(resource: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect low-utilization EC2 findings."""

    if resource.get("resource_type") != "EC2":
        return []
    if resource.get("state") != "running":
        return []

    ec2_rules = rules.get("ec2", {})
    analysis_days = int(ec2_rules.get("analysis_days", 14))
    avg_threshold = float(ec2_rules.get("cpu_avg_threshold", 10))
    max_threshold = float(ec2_rules.get("cpu_max_threshold", 30))
    cpu_avg = _metric_value(resource, f"cpu_avg_{analysis_days}d", "cpu_avg_14d")
    cpu_max = _metric_value(resource, f"cpu_max_{analysis_days}d", "cpu_max_14d")

    findings: list[dict[str, Any]] = []
    if cpu_avg is not None and cpu_avg < avg_threshold:
        findings.append(
            _enrich_finding(
                {
                    "severity": "medium",
                    "type": "possible_overprovisioned_ec2",
                    "finding_type": "possible_overprovisioned_ec2",
                    "resource_type": "EC2",
                    "resource_id": resource.get("resource_id"),
                    "reason": (
                        f"최근 {analysis_days}일 평균 CPU 사용률이 {cpu_avg}%로 "
                        f"임계값 {avg_threshold}%보다 낮습니다."
                    ),
                    "reason_codes": _ec2_reason_codes(resource, cpu_avg, cpu_max, avg_threshold, max_threshold),
                    "evidence": {
                        "cpu_avg": cpu_avg,
                        "cpu_max": cpu_max,
                        "analysis_days": analysis_days,
                        "threshold_cpu_avg": avg_threshold,
                        "threshold_cpu_max": max_threshold,
                    },
                    "recommended_action": "다운사이즈 검토",
                    "risk_checklist": [
                        "피크 시간대 트래픽을 확인합니다.",
                        "배치 작업 및 예약 작업 여부를 확인합니다.",
                        "서비스 소유자와 변경 가능 시간을 확인합니다.",
                    ],
                    "resource": resource,
                },
                rules,
            )
        )

    if cpu_max is not None and cpu_max < max_threshold:
        findings.append(
            _enrich_finding(
                {
                    "severity": "low",
                    "type": "low_peak_usage_ec2",
                    "finding_type": "low_peak_usage_ec2",
                    "resource_type": "EC2",
                    "resource_id": resource.get("resource_id"),
                    "reason": (
                        f"최근 {analysis_days}일 최대 CPU 사용률도 {cpu_max}%로 "
                        f"임계값 {max_threshold}%보다 낮습니다."
                    ),
                    "reason_codes": _ec2_reason_codes(resource, cpu_avg, cpu_max, avg_threshold, max_threshold),
                    "evidence": {
                        "cpu_avg": cpu_avg,
                        "cpu_max": cpu_max,
                        "analysis_days": analysis_days,
                        "threshold_cpu_max": max_threshold,
                    },
                    "recommended_action": "피크 트래픽 확인 후 축소 검토",
                    "risk_checklist": [
                        "이벤트성 트래픽 여부를 확인합니다.",
                        "CloudWatch 알람과 애플리케이션 로그를 확인합니다.",
                    ],
                    "resource": resource,
                },
                rules,
            )
        )

    return findings


def analyze_ebs(resource: dict[str, Any], rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect detached EBS volume findings."""

    if resource.get("resource_type") != "EBS":
        return []

    ebs_rules = rules.get("ebs", {})
    detached_threshold = int(ebs_rules.get("detached_days_threshold", 14))
    detached_days = resource.get("detached_days")

    if resource.get("state") != "available":
        return []
    if detached_days is None or int(detached_days) < detached_threshold:
        return []

    finding = {
        "severity": "high",
        "type": "unused_ebs_volume",
        "finding_type": "unused_ebs_volume",
        "resource_type": "EBS",
        "resource_id": resource.get("resource_id"),
        "reason": f"{detached_days}일 동안 어떤 EC2 인스턴스에도 연결되지 않은 EBS 볼륨입니다.",
        "reason_codes": _ebs_reason_codes(resource, detached_threshold),
        "evidence": {
            "detached_days": detached_days,
            "threshold_detached_days": detached_threshold,
            "state": resource.get("state"),
            "size_gb": resource.get("size_gb"),
            "volume_type": resource.get("volume_type"),
        },
        "recommended_action": "스냅샷 생성 후 삭제 검토",
        "safe_action": "snapshot_before_delete",
        "recommended_steps": [
            "미연결 상태와 소유자를 확인합니다.",
            "삭제 전 스냅샷을 생성합니다.",
            "검토 기간 동안 스냅샷을 보관합니다.",
            "소유자 승인 후 볼륨 삭제 여부를 결정합니다.",
        ],
        "risk_checklist": [
            "스냅샷 백업 필요 여부를 확인합니다.",
            "최근 복구 작업 또는 테스트 작업에서 사용했는지 확인합니다.",
            "태그에서 서비스 소유자 정보를 확인합니다.",
        ],
        "resource": resource,
    }
    return [_enrich_finding(finding, rules)]


def _enrich_finding(finding: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Attach shared deterministic metadata to a finding."""

    resource = finding.get("resource", {})
    finding.update(_extract_tag_metadata(resource.get("tags", {})))
    finding["confidence_score"] = _confidence_score(finding, rules)
    finding["action_priority"] = _action_priority(finding)

    if finding.get("resource_type") == "EC2":
        current = resource.get("instance_type")
        recommended = DOWNGRADE_MAP.get(str(current))
        finding["current_instance_type"] = current
        finding["recommended_instance_type"] = recommended
        if recommended:
            finding["recommendation_basis"] = "CPU average and max usage are below thresholds"

    finding.update(estimate_finding_costs(finding, rules))
    return finding


def _confidence_score(finding: dict[str, Any], rules: dict[str, Any]) -> int:
    """Calculate a deterministic confidence score from evidence and tags."""

    resource = finding.get("resource", {})
    evidence = finding.get("evidence", {})
    score = 50

    if finding.get("resource_type") == "EC2":
        avg_threshold = float(evidence.get("threshold_cpu_avg", rules.get("ec2", {}).get("cpu_avg_threshold", 10)))
        max_threshold = float(evidence.get("threshold_cpu_max", rules.get("ec2", {}).get("cpu_max_threshold", 30)))
        cpu_avg = evidence.get("cpu_avg")
        cpu_max = evidence.get("cpu_max")
        if cpu_avg is not None:
            score += min(20, int(max(avg_threshold - float(cpu_avg), 0) * 2))
        if cpu_max is not None:
            score += min(15, int(max(max_threshold - float(cpu_max), 0)))
        if int(evidence.get("analysis_days") or 0) >= 14:
            score += 10
        if _is_recent(resource.get("launch_time"), 7):
            score -= 15
    elif finding.get("resource_type") == "EBS":
        detached_days = int(evidence.get("detached_days") or 0)
        threshold = int(evidence.get("threshold_detached_days") or 14)
        score += min(30, max(detached_days - threshold, 0))
        if evidence.get("state") == "available":
            score += 10
        if int(evidence.get("size_gb") or 0) >= 100:
            score += 5

    if _has_protected_tag(resource):
        score -= 30
    if _has_lower_env_tag(resource):
        score += 5
    return max(0, min(100, score))


def _action_priority(finding: dict[str, Any]) -> str:
    """Classify review urgency for a finding."""

    resource = finding.get("resource", {})
    if _has_protected_tag(resource):
        return "excluded"
    score = int(finding.get("confidence_score") or 0)

    if finding.get("resource_type") == "EBS":
        detached_days = int(finding.get("evidence", {}).get("detached_days") or 0)
        threshold = int(finding.get("evidence", {}).get("threshold_detached_days") or 14)
        if detached_days >= threshold and score >= 75:
            return "immediate_review"
        return "review"

    if finding.get("resource_type") == "EC2":
        evidence = finding.get("evidence", {})
        both_low = evidence.get("cpu_avg") is not None and evidence.get("cpu_max") is not None
        if both_low and score >= 65:
            return "review"
        return "observe"

    return "observe"


def _extract_tag_metadata(tags: dict[str, Any]) -> dict[str, str]:
    """Extract owner, project, environment, and service metadata from tags."""

    metadata: dict[str, str] = {}
    for output_key, candidates in TAG_KEYS.items():
        metadata[output_key] = "unknown"
        for key in candidates:
            value = tags.get(key)
            if value:
                metadata[output_key] = str(value)
                break
    return metadata


def _ec2_reason_codes(
    resource: dict[str, Any],
    cpu_avg: float | None,
    cpu_max: float | None,
    avg_threshold: float,
    max_threshold: float,
) -> list[str]:
    codes: list[str] = []
    if cpu_avg is not None and cpu_avg < avg_threshold:
        codes.append("LOW_AVG_CPU")
    if cpu_max is not None and cpu_max < max_threshold:
        codes.append("LOW_MAX_CPU")
    if _has_protected_tag(resource):
        codes.append("PROTECTED_TAG")
    else:
        codes.append("NO_PRODUCTION_TAG")
    if _has_lower_env_tag(resource):
        codes.append("LOWER_ENVIRONMENT_TAG")
    return codes


def _ebs_reason_codes(resource: dict[str, Any], detached_threshold: int) -> list[str]:
    codes = ["AVAILABLE_VOLUME"]
    if int(resource.get("detached_days") or 0) >= detached_threshold:
        codes.append("DETACHED_DAYS_EXCEEDED")
    if _has_protected_tag(resource):
        codes.append("PROTECTED_TAG")
    return codes


def _has_protected_tag(resource: dict[str, Any]) -> bool:
    haystack = _tag_haystack(resource)
    return any(marker in haystack for marker in PROTECTED_TAG_MARKERS)


def _has_lower_env_tag(resource: dict[str, Any]) -> bool:
    haystack = _tag_haystack(resource)
    return any(marker in haystack for marker in LOWER_ENV_MARKERS)


def _tag_haystack(resource: dict[str, Any]) -> str:
    tags = resource.get("tags", {})
    values = [str(resource.get("name", ""))]
    values.extend(str(key) for key in tags.keys())
    values.extend(str(value) for value in tags.values())
    return " ".join(values).lower()


def _is_recent(value: Any, days: int) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).days < days


def _metric_value(
    resource: dict[str, Any], primary_key: str, fallback_key: str
) -> float | None:
    """Read a numeric metric from a resource model."""

    raw = resource.get(primary_key, resource.get(fallback_key))
    if raw is None:
        return None
    return float(raw)
