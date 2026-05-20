"""CloudWatch metric collector for normalized resources."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import Settings
from app.collectors.aws_ec2_collector import _create_boto3_session

logger = logging.getLogger(__name__)


def attach_cloudwatch_metrics(
    resources: list[dict[str, Any]], settings: Settings
) -> list[dict[str, Any]]:
    """Attach CPU average and maximum metrics to EC2 resources."""

    session = _create_boto3_session(settings)
    cloudwatch = session.client("cloudwatch", region_name=settings.aws_region)

    for resource in resources:
        if resource.get("resource_type") != "EC2":
            continue
        if resource.get("state") != "running":
            resource["cpu_avg_14d"] = None
            resource["cpu_max_14d"] = None
            continue

        metric = _get_cpu_statistics(
            cloudwatch,
            instance_id=str(resource["resource_id"]),
            analysis_days=settings.analysis_days,
        )
        resource[f"cpu_avg_{settings.analysis_days}d"] = metric["average"]
        resource[f"cpu_max_{settings.analysis_days}d"] = metric["maximum"]
        resource["cpu_avg_14d"] = metric["average"]
        resource["cpu_max_14d"] = metric["maximum"]

    return resources


def _get_cpu_statistics(
    cloudwatch: Any, instance_id: str, analysis_days: int
) -> dict[str, float | None]:
    """Fetch CPUUtilization average and maximum for one EC2 instance."""

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=analysis_days)

    try:
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=["Average", "Maximum"],
            Unit="Percent",
        )
    except Exception:
        logger.exception("Failed to collect CloudWatch metric for %s", instance_id)
        return {"average": None, "maximum": None}

    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return {"average": None, "maximum": None}

    averages = [point["Average"] for point in datapoints if "Average" in point]
    maximums = [point["Maximum"] for point in datapoints if "Maximum" in point]

    average = round(sum(averages) / len(averages), 2) if averages else None
    maximum = round(max(maximums), 2) if maximums else None
    return {"average": average, "maximum": maximum}

