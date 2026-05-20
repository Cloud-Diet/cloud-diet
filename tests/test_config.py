import os

from app.config import load_settings


def test_load_settings_uses_default_rules_when_file_is_missing(monkeypatch):
    monkeypatch.setenv("RULE_CONFIG_PATH", "configs/not-found.yaml")
    monkeypatch.setenv("NOTIFIER", "console")
    monkeypatch.setenv("COLLECTOR_MODE", "sample")

    settings = load_settings(env_file=None)

    assert settings.analysis_days == 14
    assert settings.notification.notifier == "console"
    assert settings.collector_mode == "sample"


def test_environment_overrides_analysis_days(monkeypatch):
    monkeypatch.setenv("RULE_CONFIG_PATH", "configs/not-found.yaml")
    monkeypatch.setenv("ANALYSIS_DAYS", "7")

    settings = load_settings(env_file=None)

    assert settings.analysis_days == 7
    assert settings.rules["ec2"]["analysis_days"] == 7

