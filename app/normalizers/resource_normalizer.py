"""Normalize raw AWS API responses into Cloud Diet resource models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import Settings


def normalize_resources(
    ec2_instances: list[dict[str, Any]],
    ebs_volumes: list[dict[str, Any]],
    settings: Settings,
) -> list[dict[str, Any]]:
    """Normalize EC2 and EBS API responses into one resource list."""

    resources: list[dict[str, Any]] = []
    resources.extend(normalize_ec2_instances(ec2_instances, settings))
    resources.extend(normalize_ebs_volumes(ebs_volumes, settings))
    return resources


def normalize_ec2_instances(
    ec2_instances: list[dict[str, Any]], settings: Settings
) -> list[dict[str, Any]]:
    """Normalize raw EC2 instance dictionaries."""

    normalized: list[dict[str, Any]] = []
    for instance in ec2_instances:
        tags = _tags_to_dict(instance.get("Tags", []))
        normalized.append(
            {
                "resource_type": "EC2",
                "resource_id": instance.get("InstanceId"),
                "name": tags.get("Name"),
                "region": settings.aws_region,
                "instance_type": instance.get("InstanceType"),
                "state": instance.get("State", {}).get("Name"),
                "launch_time": _isoformat(instance.get("LaunchTime")),
                "cpu_avg_14d": None,
                "cpu_max_14d": None,
                "memory_avg_14d": None,
                "estimated_monthly_cost": None,
                "tags": tags,
            }
        )
    return normalized


def normalize_ebs_volumes(
    ebs_volumes: list[dict[str, Any]], settings: Settings
) -> list[dict[str, Any]]:
    """Normalize raw EBS volume dictionaries."""

    normalized: list[dict[str, Any]] = []
    for volume in ebs_volumes:
        tags = _tags_to_dict(volume.get("Tags", []))
        attachments = volume.get("Attachments", [])
        attached_instance_id = attachments[0].get("InstanceId") if attachments else None
        create_time = volume.get("CreateTime")

        normalized.append(
            {
                "resource_type": "EBS",
                "resource_id": volume.get("VolumeId"),
                "region": settings.aws_region,
                "state": volume.get("State"),
                "size_gb": volume.get("Size"),
                "volume_type": volume.get("VolumeType"),
                "create_time": _isoformat(create_time),
                "attached_instance_id": attached_instance_id,
                "detached_days": _detached_days(volume.get("State"), create_time),
                "estimated_monthly_cost": None,
                "tags": tags,
            }
        )
    return normalized


def _tags_to_dict(tags: list[dict[str, Any]]) -> dict[str, str]:
    """Convert AWS tag arrays into a plain dictionary."""

    return {
        str(tag.get("Key")): str(tag.get("Value"))
        for tag in tags
        if tag.get("Key") is not None and tag.get("Value") is not None
    }


def _isoformat(value: Any) -> str | None:
    """Serialize datetime-like values as ISO 8601 strings."""

    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _detached_days(state: str | None, create_time: Any) -> int | None:
    """Estimate detached days for available EBS volumes."""

    if state != "available" or not isinstance(create_time, datetime):
        return None

    if create_time.tzinfo is None:
        create_time = create_time.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - create_time.astimezone(timezone.utc)
    return max(delta.days, 0)

