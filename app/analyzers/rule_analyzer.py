"""Rule-based waste candidate detection."""

from __future__ import annotations

from typing import Any


SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}


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
            {
                "severity": "medium",
                "type": "possible_overprovisioned_ec2",
                "resource_type": "EC2",
                "resource_id": resource.get("resource_id"),
                "reason": f"최근 {analysis_days}일 평균 CPU 사용률이 {cpu_avg}%로 낮습니다.",
                "evidence": {
                    "cpu_avg": cpu_avg,
                    "cpu_max": cpu_max,
                    "analysis_days": analysis_days,
                    "threshold_cpu_avg": avg_threshold,
                    "threshold_cpu_max": max_threshold,
                },
                "recommended_action": "다운사이징 검토",
                "risk_checklist": [
                    "피크 시간대 트래픽 확인",
                    "배치 작업 및 예약 작업 여부 확인",
                    "서비스 소유자와 변경 가능 시간 확인",
                ],
                "resource": resource,
            }
        )

    if cpu_max is not None and cpu_max < max_threshold:
        findings.append(
            {
                "severity": "low",
                "type": "low_peak_usage_ec2",
                "resource_type": "EC2",
                "resource_id": resource.get("resource_id"),
                "reason": f"최근 {analysis_days}일 최대 CPU 사용률도 {cpu_max}%로 낮습니다.",
                "evidence": {
                    "cpu_avg": cpu_avg,
                    "cpu_max": cpu_max,
                    "analysis_days": analysis_days,
                    "threshold_cpu_max": max_threshold,
                },
                "recommended_action": "피크 트래픽 확인 후 축소 검토",
                "risk_checklist": [
                    "이벤트성 트래픽 여부 확인",
                    "CloudWatch 알람과 애플리케이션 로그 확인",
                ],
                "resource": resource,
            }
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

    return [
        {
            "severity": "high",
            "type": "unused_ebs_volume",
            "resource_type": "EBS",
            "resource_id": resource.get("resource_id"),
            "reason": f"{detached_days}일 동안 EC2 인스턴스에 연결되지 않은 EBS 볼륨입니다.",
            "evidence": {
                "detached_days": detached_days,
                "threshold_detached_days": detached_threshold,
                "state": resource.get("state"),
                "size_gb": resource.get("size_gb"),
                "volume_type": resource.get("volume_type"),
            },
            "recommended_action": "삭제 또는 스냅샷 전환 검토",
            "risk_checklist": [
                "스냅샷 백업 필요 여부 확인",
                "최근 복구 작업 또는 테스트 작업에서 사용되는지 확인",
                "태그의 서비스/소유자 정보 확인",
            ],
            "resource": resource,
        }
    ]


def _metric_value(
    resource: dict[str, Any], primary_key: str, fallback_key: str
) -> float | None:
    """Read a numeric metric from a resource model."""

    raw = resource.get(primary_key, resource.get(fallback_key))
    if raw is None:
        return None
    return float(raw)

