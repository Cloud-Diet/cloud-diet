from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.normalizers.resource_normalizer import normalize_ec2_instances, normalize_ebs_volumes


def test_normalize_ec2_instance_maps_expected_fields():
    settings = SimpleNamespace(aws_region="ap-northeast-2")
    raw = [
        {
            "InstanceId": "i-test",
            "InstanceType": "t3.large",
            "State": {"Name": "running"},
            "LaunchTime": datetime(2026, 5, 1, tzinfo=timezone.utc),
            "Tags": [{"Key": "Name", "Value": "api-server"}],
        }
    ]

    resources = normalize_ec2_instances(raw, settings)

    assert resources[0]["resource_type"] == "EC2"
    assert resources[0]["resource_id"] == "i-test"
    assert resources[0]["name"] == "api-server"
    assert resources[0]["region"] == "ap-northeast-2"
    assert resources[0]["cpu_avg_14d"] is None


def test_normalize_available_ebs_calculates_detached_days():
    settings = SimpleNamespace(aws_region="ap-northeast-2")
    raw = [
        {
            "VolumeId": "vol-test",
            "State": "available",
            "Size": 100,
            "VolumeType": "gp3",
            "CreateTime": datetime.now(timezone.utc) - timedelta(days=20),
            "Attachments": [],
            "Tags": [{"Key": "Name", "Value": "old-volume"}],
        }
    ]

    resources = normalize_ebs_volumes(raw, settings)

    assert resources[0]["resource_type"] == "EBS"
    assert resources[0]["resource_id"] == "vol-test"
    assert resources[0]["attached_instance_id"] is None
    assert resources[0]["detached_days"] >= 19

