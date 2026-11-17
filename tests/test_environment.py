"""Configuration stays data, preserves overrides, and does not expose secrets."""

import os
import secrets
from unittest.mock import Mock

import pytest

from jobcompass import environment, serve


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    monkeypatch.setattr(environment, "ENV_FILE", path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    for name in ("JC_TEST_VALUE", "JC_TEST_EMPTY", "JC_TEST_LITERAL"):
        monkeypatch.delenv(name, raising=False)
    return path


def test_loads_only_explicit_file_preserves_exports_and_literal_values(env_file, monkeypatch, capsys):
    env_file.write_text("JC_TEST_VALUE=local\nJC_TEST_EMPTY=local\nJC_TEST_LITERAL='${JC_TEST_VALUE} $(echo should-not-run)'\n")
    monkeypatch.setenv("JC_TEST_VALUE", "exported")
    monkeypatch.setenv("JC_TEST_EMPTY", "")
    monkeypatch.chdir(env_file.parent.parent)
    environment.load_environment()
    assert os.environ["JC_TEST_VALUE"] == "exported"
    assert os.environ["JC_TEST_EMPTY"] == ""
    assert os.environ["JC_TEST_LITERAL"] == "${JC_TEST_VALUE} $(echo should-not-run)"
    assert capsys.readouterr().out == ""


def test_frontend_selection_does_not_import_database_or_provider_secrets(env_file, monkeypatch, capsys):
    token = secrets.token_urlsafe(24)
    env_file.write_text(f"JC_TEST_VALUE=http://127.0.0.1:8765\nJC_TEST_LITERAL={token}\n")
    environment.load_environment({"JC_TEST_VALUE"})
    assert os.environ["JC_TEST_VALUE"] == "http://127.0.0.1:8765"
    assert "JC_TEST_LITERAL" not in os.environ
    captured = capsys.readouterr()
    assert token not in captured.out + captured.err


def test_missing_env_does_not_search_parent_directory(env_file, monkeypatch):
    (env_file.parent.parent / ".env").write_text("JC_TEST_VALUE=wrong-project\n")
    environment.load_environment()
    assert "JC_TEST_VALUE" not in os.environ


@pytest.mark.parametrize("disabled", ["1", "TRUE", "yes"])
def test_injected_environment_can_disable_file_loading(env_file, monkeypatch, disabled):
    env_file.write_text("JC_TEST_VALUE=local\n")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", disabled)
    environment.load_environment()
    assert "JC_TEST_VALUE" not in os.environ


def test_api_launcher_loads_bind_settings_before_starting(env_file, monkeypatch):
    monkeypatch.delenv("JOBCOMPASS_HOST", raising=False)
    monkeypatch.delenv("JOBCOMPASS_PORT", raising=False)
    env_file.write_text("JOBCOMPASS_HOST=127.0.0.1\nJOBCOMPASS_PORT=8767\n")
    start = Mock()
    monkeypatch.setattr(serve.uvicorn, "run", start)
    serve.main()
    start.assert_called_once_with("jobcompass.api:app", host="127.0.0.1", port=8767)


@pytest.mark.parametrize("port", ["0", "65536", "invalid"])
def test_api_launcher_rejects_bad_port_without_echoing_value(env_file, monkeypatch, port):
    monkeypatch.setenv("JOBCOMPASS_PORT", port)
    with pytest.raises(SystemExit, match="JOBCOMPASS_PORT must be an integer from 1 to 65535"):
        serve.main()
