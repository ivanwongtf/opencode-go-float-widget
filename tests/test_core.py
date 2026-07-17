"""Unit tests for the platform-agnostic core module."""

import pytest

import core


def test_color_class_for_green() -> None:
    assert core.color_class_for(0) == "green"
    assert core.color_class_for(49) == "green"


def test_color_class_for_amber() -> None:
    assert core.color_class_for(50) == "amber"
    assert core.color_class_for(79) == "amber"


def test_color_class_for_red() -> None:
    assert core.color_class_for(80) == "red"
    assert core.color_class_for(100) == "red"


def test_format_reset_time_edges() -> None:
    assert core.format_reset_time(-1) == "0 minutes"
    assert core.format_reset_time(0) == "less than a minute"
    assert core.format_reset_time(59) == "less than a minute"
    assert core.format_reset_time(60) == "1 minute"
    assert core.format_reset_time(120) == "2 minutes"


def test_format_reset_time_hours() -> None:
    assert core.format_reset_time(3600) == "1 hour 0 minutes"
    assert core.format_reset_time(3660) == "1 hour 1 minute"
    assert core.format_reset_time(7200) == "2 hours 0 minutes"


def test_format_reset_time_days() -> None:
    assert core.format_reset_time(86400) == "1 day 0 hours"
    assert core.format_reset_time(90000) == "1 day 1 hour"
    assert core.format_reset_time(172800) == "2 days 0 hours"


def test_parse_valid_html() -> None:
    html = """
    rollingUsage:$abc[0]={status:"ok",resetInSec:123,usagePercent:42}
    weeklyUsage:$abc[1]={status:"ok",resetInSec:4567,usagePercent:65}
    monthlyUsage:$abc[2]={status:"throttled",resetInSec:89000,usagePercent:88}
    """
    usage = core.parse(html)
    assert usage.rolling.status == "ok"
    assert usage.rolling.resetInSec == 123
    assert usage.rolling.usagePercent == 42
    assert usage.weekly.usagePercent == 65
    assert usage.monthly.status == "throttled"


def test_parse_missing_usage_raises() -> None:
    with pytest.raises(ValueError):
        core.parse("<html>nothing</html>")


def test_parse_malformed_usage_raises() -> None:
    html = 'rollingUsage:$abc[0]={status:"ok"}'
    with pytest.raises(ValueError):
        core.parse(html)


def test_format_tooltip() -> None:
    usage = core.UsageData(
        rolling=core.UsageItem(status="ok", resetInSec=123, usagePercent=42),
        weekly=core.UsageItem(status="ok", resetInSec=3600, usagePercent=65),
        monthly=core.UsageItem(status="throttled", resetInSec=90000, usagePercent=88),
    )
    tooltip = core.format_tooltip(usage)
    assert "Rolling: 42%" in tooltip
    assert "Weekly: 65%" in tooltip
    assert "Monthly: 88%" in tooltip
    assert "reset in 1 hour 0 minutes" in tooltip


def test_check_auth_failure_with_usage() -> None:
    html = 'rollingUsage:... weeklyUsage:... monthlyUsage:...'
    assert core.check_auth_failure(html) is False


def test_check_auth_failure_login_page() -> None:
    html = '<html>OpenAuth Continue with GitHub</html>'
    assert core.check_auth_failure(html) is True


def test_check_auth_failure_no_usage_no_auth() -> None:
    html = '<html>something else</html>'
    assert core.check_auth_failure(html) is False


def test_fetch_missing_workspace_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENCODE_WORKSPACE_ID", raising=False)
    monkeypatch.setenv("OPENCODE_AUTH", "auth=FAKE")
    with pytest.raises(ValueError, match="OPENCODE_WORKSPACE_ID"):
        core.fetch()


def test_fetch_missing_auth_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_WORKSPACE_ID", "wrk_test")
    monkeypatch.delenv("OPENCODE_AUTH", raising=False)
    with pytest.raises(ValueError, match="OPENCODE_AUTH"):
        core.fetch()


def test_go_url_requires_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENCODE_WORKSPACE_ID", raising=False)
    with pytest.raises(ValueError, match="OPENCODE_WORKSPACE_ID"):
        core.go_url()


def test_go_url_returns_correct_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCODE_WORKSPACE_ID", "wrk_test123")
    assert core.go_url() == "https://opencode.ai/workspace/wrk_test123/go"


def test_js_obj_to_dict() -> None:
    assert core._js_obj_to_dict("{a:1,b:!0,c:!1}") == {"a": 1, "b": True, "c": False}
