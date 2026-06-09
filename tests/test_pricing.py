from app.pricing.price_estimator import estimate_finding_costs


RULES = {
    "pricing": {
        "currency": "USD",
        "monthly_hours": 730,
        "ec2_hourly_prices": {"t3.large": 0.0832, "t3.medium": 0.0416},
        "ebs_gb_month_prices": {"gp3": 0.08},
    }
}


def test_ec2_pricing_calculates_savings():
    finding = {
        "resource_type": "EC2",
        "current_instance_type": "t3.large",
        "recommended_instance_type": "t3.medium",
    }

    costs = estimate_finding_costs(finding, RULES)

    assert costs["estimated_current_monthly_cost"] == 60.74
    assert costs["estimated_recommended_monthly_cost"] == 30.37
    assert costs["estimated_monthly_savings"] == 30.37


def test_missing_pricing_keeps_cost_fields_none():
    finding = {
        "resource_type": "EC2",
        "current_instance_type": "m5.large",
        "recommended_instance_type": None,
    }

    costs = estimate_finding_costs(finding, RULES)

    assert costs["estimated_current_monthly_cost"] is None
    assert costs["estimated_monthly_savings"] is None
    assert "가격 정보" in costs["pricing_note"]
