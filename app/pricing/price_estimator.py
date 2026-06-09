"""Local price estimation for Cloud Diet findings."""

from __future__ import annotations

from typing import Any


def estimate_finding_costs(
    finding: dict[str, Any], rules: dict[str, Any]
) -> dict[str, Any]:
    """Estimate monthly costs using the local rules.yaml price table."""

    pricing = rules.get("pricing", {})
    currency = pricing.get("currency", "USD")
    result: dict[str, Any] = {
        "estimated_current_monthly_cost": None,
        "estimated_recommended_monthly_cost": None,
        "estimated_monthly_savings": None,
        "currency": currency,
        "pricing_source": "local_config",
    }

    if finding.get("resource_type") == "EC2":
        _estimate_ec2(finding, pricing, result)
    elif finding.get("resource_type") == "EBS":
        _estimate_ebs(finding, pricing, result)

    if result["estimated_current_monthly_cost"] is None:
        result["pricing_note"] = "가격 정보가 없어 예상 절감액을 계산하지 않았습니다."
    return result


def _estimate_ec2(
    finding: dict[str, Any], pricing: dict[str, Any], result: dict[str, Any]
) -> None:
    hourly_prices = pricing.get("ec2_hourly_prices", {})
    monthly_hours = float(pricing.get("monthly_hours", 730))
    current_type = finding.get("current_instance_type")
    recommended_type = finding.get("recommended_instance_type")
    current_hourly = hourly_prices.get(current_type)

    if current_hourly is None:
        return

    current_monthly = round(float(current_hourly) * monthly_hours, 2)
    result["estimated_current_monthly_cost"] = current_monthly

    recommended_hourly = hourly_prices.get(recommended_type)
    if recommended_type and recommended_hourly is not None:
        recommended_monthly = round(float(recommended_hourly) * monthly_hours, 2)
        result["estimated_recommended_monthly_cost"] = recommended_monthly
        result["estimated_monthly_savings"] = round(
            current_monthly - recommended_monthly, 2
        )


def _estimate_ebs(
    finding: dict[str, Any], pricing: dict[str, Any], result: dict[str, Any]
) -> None:
    resource = finding.get("resource", {})
    gb_prices = pricing.get("ebs_gb_month_prices", {})
    volume_type = resource.get("volume_type")
    size_gb = resource.get("size_gb")
    gb_price = gb_prices.get(volume_type)

    if gb_price is None or size_gb is None:
        return

    current_monthly = round(float(size_gb) * float(gb_price), 2)
    result["estimated_current_monthly_cost"] = current_monthly
    result["estimated_recommended_monthly_cost"] = 0.0
    result["estimated_monthly_savings"] = current_monthly
