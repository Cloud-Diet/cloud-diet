"""Configuration loading for Cloud Diet."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in Docker image
    load_dotenv = None  # type: ignore[assignment]


DEFAULT_RULES: dict[str, Any] = {
    "ec2": {
        "cpu_avg_threshold": 10,
        "cpu_max_threshold": 30,
        "analysis_days": 14,
    },
    "ebs": {
        "detached_days_threshold": 14,
    },
    "notification": {
        "send_empty_report": True,
        "max_findings_per_report": 20,
    },
    "llm": {
        "enabled": True,
        "max_sentences": 5,
        "language": "ko",
    },
}


@dataclass(frozen=True)
class NotificationSettings:
    """Notification delivery configuration."""

    notifier: str
    discord_webhook_url: str | None
    slack_webhook_url: str | None
    send_empty_report: bool
    max_findings_per_report: int


@dataclass(frozen=True)
class LlmSettings:
    """LLM recommendation generation configuration."""

    enabled: bool
    api_key: str | None
    model: str
    max_sentences: int
    language: str


@dataclass(frozen=True)
class Settings:
    """Application settings shared across modules."""

    aws_region: str
    aws_profile: str | None
    analysis_days: int
    output_dir: Path
    rule_config_path: Path
    log_level: str
    collector_mode: str
    sample_data_path: Path
    rules: dict[str, Any]
    notification: NotificationSettings
    llm: LlmSettings


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Load environment variables and rule configuration into a settings object."""

    if env_file and load_dotenv:
        load_dotenv(dotenv_path=env_file, override=False)

    rule_config_path = Path(
        os.getenv("RULE_CONFIG_PATH", "configs/rules.yaml")
    ).expanduser()
    rules = _load_rules(rule_config_path)

    analysis_days = int(
        os.getenv("ANALYSIS_DAYS", rules.get("ec2", {}).get("analysis_days", 14))
    )
    rules.setdefault("ec2", {})["analysis_days"] = analysis_days

    notification_rules = rules.get("notification", {})
    llm_rules = rules.get("llm", {})

    notification = NotificationSettings(
        notifier=os.getenv("NOTIFIER", "discord").lower(),
        discord_webhook_url=_empty_to_none(os.getenv("DISCORD_WEBHOOK_URL")),
        slack_webhook_url=_empty_to_none(os.getenv("SLACK_WEBHOOK_URL")),
        send_empty_report=_env_bool(
            "SEND_EMPTY_REPORT",
            bool(notification_rules.get("send_empty_report", True)),
        ),
        max_findings_per_report=int(
            os.getenv(
                "MAX_FINDINGS_PER_REPORT",
                notification_rules.get("max_findings_per_report", 20),
            )
        ),
    )

    llm = LlmSettings(
        enabled=_env_bool("LLM_ENABLED", bool(llm_rules.get("enabled", True))),
        api_key=_empty_to_none(os.getenv("OPENAI_API_KEY")),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        max_sentences=int(os.getenv("LLM_MAX_SENTENCES", llm_rules.get("max_sentences", 5))),
        language=os.getenv("LLM_LANGUAGE", llm_rules.get("language", "ko")),
    )

    return Settings(
        aws_region=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2"),
        aws_profile=_empty_to_none(os.getenv("AWS_PROFILE")),
        analysis_days=analysis_days,
        output_dir=Path(os.getenv("OUTPUT_DIR", "outputs")).expanduser(),
        rule_config_path=rule_config_path,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        collector_mode=os.getenv("COLLECTOR_MODE", "aws").lower(),
        sample_data_path=Path(os.getenv("SAMPLE_DATA_PATH", "configs/sample_resources.json")).expanduser(),
        rules=rules,
        notification=notification,
        llm=llm,
    )


def _load_rules(path: Path) -> dict[str, Any]:
    """Read rules.yaml and merge it over safe defaults."""

    rules = _deep_copy(DEFAULT_RULES)
    if not path.exists():
        return rules

    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f"Rule config must be a mapping: {path}")

    return _deep_merge(rules, loaded)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge nested dictionaries without mutating the input dictionaries."""

    result = _deep_copy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _deep_copy(value: Any) -> Any:
    """Copy nested dictionaries and lists used in simple config values."""

    if isinstance(value, dict):
        return {key: _deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    return value


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean environment variable."""

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _empty_to_none(value: str | None) -> str | None:
    """Return None for missing or blank environment values."""

    if value is None or not value.strip():
        return None
    return value.strip()

