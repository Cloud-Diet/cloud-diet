"""Cloud Diet application entry point."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.analyzers.rule_analyzer import analyze_resources
from app.collectors.aws_ebs_collector import collect_ebs_volumes
from app.collectors.aws_ec2_collector import collect_ec2_instances
from app.collectors.cloudwatch_collector import attach_cloudwatch_metrics
from app.config import Settings, load_settings
from app.normalizers.resource_normalizer import normalize_resources
from app.notifiers import send_message
from app.recommenders.llm_recommender import generate_recommendations
from app.reporters.markdown_reporter import build_daily_summary, save_report_bundle
from app.utils.logger import configure_logging


def main() -> None:
    """Run one complete Cloud Diet analysis batch."""

    settings = load_settings()
    configure_logging(settings.log_level, settings.output_dir)
    logger = logging.getLogger(__name__)

    logger.info("Cloud Diet batch started")
    resources = _load_resources(settings)
    findings = analyze_resources(resources, settings.rules)
    limited_findings = findings[: settings.notification.max_findings_per_report]

    recommendations = generate_recommendations(limited_findings, settings)
    report_paths = save_report_bundle(resources, limited_findings, recommendations, settings)
    logger.info("Report files written: %s", report_paths)

    if not limited_findings:
        logger.info("No waste candidates detected")
        if settings.notification.send_empty_report:
            send_message(
                "Cloud Diet 검사 결과, 현재 비용 낭비 후보가 발견되지 않았습니다.",
                settings,
            )
        return

    summary = build_daily_summary(limited_findings, recommendations, settings)
    send_message(summary, settings)
    logger.info("Cloud Diet batch finished")


def _load_resources(settings: Settings) -> list[dict[str, Any]]:
    """Load normalized resources from AWS or from a local sample file."""

    if settings.collector_mode == "sample":
        return _load_sample_resources(settings)
    if settings.collector_mode != "aws":
        raise ValueError("COLLECTOR_MODE must be one of: aws, sample")

    ec2_raw = collect_ec2_instances(settings)
    ebs_raw = collect_ebs_volumes(settings)
    resources = normalize_resources(ec2_raw, ebs_raw, settings)
    return attach_cloudwatch_metrics(resources, settings)


def _load_sample_resources(settings: Settings) -> list[dict[str, Any]]:
    """Read normalized resources from configs/sample_resources.json for demos."""

    with settings.sample_data_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Sample data must be a JSON list of normalized resources")

    return data


if __name__ == "__main__":
    main()

