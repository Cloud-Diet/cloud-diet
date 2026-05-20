"""AWS EC2 instance collector."""

from __future__ import annotations

from typing import Any

from app.config import Settings


def collect_ec2_instances(settings: Settings) -> list[dict[str, Any]]:
    """Collect raw EC2 instances with describe_instances."""

    session = _create_boto3_session(settings)
    ec2 = session.client("ec2", region_name=settings.aws_region)
    paginator = ec2.get_paginator("describe_instances")

    instances: list[dict[str, Any]] = []
    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            instances.extend(reservation.get("Instances", []))
    return instances


def _create_boto3_session(settings: Settings) -> Any:
    """Create a boto3 session using the optional AWS_PROFILE."""

    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - dependency is installed in Docker image
        raise RuntimeError("boto3 is required for COLLECTOR_MODE=aws") from exc

    if settings.aws_profile:
        return boto3.Session(profile_name=settings.aws_profile, region_name=settings.aws_region)
    return boto3.Session(region_name=settings.aws_region)

