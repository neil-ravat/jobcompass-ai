import sys

import requests

from jobcompass import __main__ as cli


def test_cli_returns_error_without_hiding_failure(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["jobcompass"])

    def fail(*args):
        raise requests.Timeout("Source unavailable")

    monkeypatch.setattr(cli, "ingest", fail)
    assert cli.main() == 1
    assert "Ingestion failed" in capsys.readouterr().err


def test_cli_reports_degraded_result(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["jobcompass", "--data-dir", str(tmp_path)])
    monkeypatch.setattr(cli, "ingest", lambda *args: {
        "records": [], "status_errors": [{"reason": "Unavailable"}], "rejected_records": [],
    })
    assert cli.main() == 2
    assert "Himalayas" in capsys.readouterr().out
