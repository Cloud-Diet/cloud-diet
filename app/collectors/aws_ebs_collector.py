"""AWS EBS volume collector."""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.collectors.aws_ec2_collector import _create_boto3_session


def collect_ebs_volumes(settings: Settings) -> list[dict[str, Any]]:
    """Collect raw EBS volumes with describe_volumes."""

    session = _create_boto3_session(settings)
    ec2 = session.client("ec2", region_name=settings.aws_region)
    paginator = ec2.get_paginator("describe_volumes")

    volumes: list[dict[str, Any]] = []
    for page in paginator.paginate():
        volumes.extend(page.get("Volumes", []))
    return volumes

