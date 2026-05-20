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
}


def test_ec2_low_cpu_creates_findings():
    resource = {
        "resource_type": "EC2",
        "resource_id": "i-test",
        "state": "running",
        "cpu_avg_14d": 7.8,
        "cpu_max_14d": 21.4,
    }

    findings = analyze_ec2(resource, RULES)

    assert any(finding["type"] == "possible_overprovisioned_ec2" for finding in findings)
    assert any(finding["type"] == "low_peak_usage_ec2" for finding in findings)


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
    }

    findings = analyze_ebs(resource, RULES)

    assert len(findings) == 1
    assert findings[0]["type"] == "unused_ebs_volume"
    assert findings[0]["severity"] == "high"


def test_analyze_resources_orders_high_severity_first():
    resources = [
        {
            "resource_type": "EC2",
            "resource_id": "i-test",
            "state": "running",
            "cpu_avg_14d": 7.8,
            "cpu_max_14d": 21.4,
        },
        {
            "resource_type": "EBS",
            "resource_id": "vol-test",
            "state": "available",
            "detached_days": 18,
            "size_gb": 100,
            "volume_type": "gp3",
        },
    ]

    findings = analyze_resources(resources, RULES)

    assert findings[0]["severity"] == "high"
    assert findings[0]["type"] == "unused_ebs_volume"

