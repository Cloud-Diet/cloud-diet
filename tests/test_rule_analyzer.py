from app.analyzers.rule_analyzer import analyze_ec2, analyze_ebs, analyze_resources


RULES = {
    "ec2": {
        "cpu_avg_threshold": 10,
        "cpu_max_threshold": 30,
        "analysis_days": 14,
    },
    "ebs": {
        "detached_days_threshold": 14,
    },
    "pricing": {
        "currency": "USD",
        "monthly_hours": 730,
        "ec2_hourly_prices": {
            "t3.micro": 0.0104,
            "t3.small": 0.0208,
            "t3.medium": 0.0416,
            "t3.large": 0.0832,
        },
        "ebs_gb_month_prices": {
            "gp3": 0.08,
        },
    },
}


def test_ec2_low_cpu_creates_findings():
    resource = {
        "resource_type": "EC2",
        "resource_id": "i-test",
        "state": "running",
        "instance_type": "t3.large",
        "cpu_avg_14d": 7.8,
        "cpu_max_14d": 21.4,
        "tags": {"Environment": "dev", "Owner": "backend-team"},
    }

    findings = analyze_ec2(resource, RULES)

    assert any(finding["type"] == "possible_overprovisioned_ec2" for finding in findings)
    assert any(finding["type"] == "low_peak_usage_ec2" for finding in findings)
    assert all(0 <= finding["confidence_score"] <= 100 for finding in findings)
    assert findings[0]["recommended_instance_type"] == "t3.medium"
    assert findings[0]["estimated_monthly_savings"] is not None


def test_ec2_stopped_instance_is_not_analyzed():
    resource = {
        "resource_type": "EC2",
        "resource_id": "i-stopped",
        "state": "stopped",
        "cpu_avg_14d": 0,
        "cpu_max_14d": 0,
    }

    assert analyze_ec2(resource, RULES) == []


def test_ebs_detached_volume_creates_finding():
    resource = {
        "resource_type": "EBS",
        "resource_id": "vol-test",
        "state": "available",
        "detached_days": 18,
        "size_gb": 100,
        "volume_type": "gp3",
        "tags": {"Name": "old-dev-volume", "Owner": "backend-team"},
    }

    findings = analyze_ebs(resource, RULES)

    assert len(findings) == 1
    assert findings[0]["type"] == "unused_ebs_volume"
    assert findings[0]["severity"] == "high"
    assert findings[0]["safe_action"] == "snapshot_before_delete"
    assert findings[0]["estimated_monthly_savings"] == 8.0
    assert findings[0]["owner"] == "backend-team"


def test_protected_tags_mark_priority_excluded():
    resource = {
        "resource_type": "EBS",
        "resource_id": "vol-prod",
        "state": "available",
        "detached_days": 30,
        "size_gb": 100,
        "volume_type": "gp3",
        "tags": {"Name": "critical-prod-backup", "Env": "prod"},
    }

    findings = analyze_ebs(resource, RULES)

    assert findings[0]["action_priority"] == "excluded"


def test_unknown_pricing_keeps_cost_fields_none():
    resource = {
        "resource_type": "EC2",
        "resource_id": "i-unsupported",
        "state": "running",
        "instance_type": "m5.large",
        "cpu_avg_14d": 1,
        "cpu_max_14d": 2,
        "tags": {"Environment": "test"},
    }

    findings = analyze_ec2(resource, RULES)

    assert findings[0]["recommended_instance_type"] is None
    assert findings[0]["estimated_monthly_savings"] is None


def test_analyze_resources_orders_high_severity_first():
    resources = [
        {
            "resource_type": "EC2",
            "resource_id": "i-test",
            "state": "running",
            "instance_type": "t3.large",
            "cpu_avg_14d": 7.8,
            "cpu_max_14d": 21.4,
            "tags": {"Environment": "dev"},
        },
        {
            "resource_type": "EBS",
            "resource_id": "vol-test",
            "state": "available",
            "detached_days": 18,
            "size_gb": 100,
            "volume_type": "gp3",
            "tags": {"Environment": "dev"},
        },
    ]

    findings = analyze_resources(resources, RULES)

    assert findings[0]["severity"] == "high"
    assert findings[0]["type"] == "unused_ebs_volume"
