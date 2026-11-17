"""Synthetic responses are confined to tests; browser smoke uses real HTTP data."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep as real_sleep
import time
from urllib.parse import urlsplit

import pytest
import requests
from fastapi.testclient import TestClient
AppTest = pytest.importorskip("streamlit.testing.v1", reason="Install the frontend extra for UI tests").AppTest

from frontend import client
from frontend.presentation import locations, safe_url, salary, text, timezones
from jobcompass.api import app
from jobcompass import api as api_module
from jobcompass.descriptions import plain_description
from jobcompass.normalize import normalize_job
from jobcompass.store import load_snapshot


def test_plain_description_preserves_readability_without_source_markup():
    result = plain_description({"description_html": '<h3>Role</h3><p>Python &amp; SQL<br>Remote</p><ul><li>Build APIs</li></ul><script>bad()</script><style>bad{}</style>'})
    assert 'Role\n\nPython & SQL\nRemote' in result
    assert '• Build APIs' in result
    assert '<' not in result and 'bad' not in result
    assert plain_description({"excerpt": "Summary only"}) == "Summary only"
    assert plain_description({}) == ""


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,test", "//example.com", "https://user:secret@example.com", None])
def test_application_links_reject_unsafe_schemes_or_credentials(url):
    assert safe_url(url) is None


def test_display_helpers_preserve_unknowns_and_original_application_url():
    url = 'https://himalayas.app/companies/test/jobs/test?utm_source=api'
    assert safe_url(url) == url
    assert text('<script>"test"</script>') == '&lt;script&gt;&quot;test&quot;&lt;/script&gt;'
    assert salary({}) == 'Salary not provided'
    assert locations({}) == 'Location not specified'
    assert locations({'location_restrictions': []}) == 'No country restriction'
    assert timezones({'timezone_restrictions': [5.5, -3.75]}) == 'UTC+05:30, UTC-03:45'
    assert salary({'salary_min': '1000.50', 'salary_max': '2000', 'currency': 'INR', 'salary_period': 'monthly'}) == 'INR 1,000.50–2,000 / month'


def test_filter_translation_does_not_invent_constraints():
    values = {'mode': 'Keyword match', 'q': ' python ', 'role': '', 'country': '', 'remote_only': False}
    assert client.search_params(values, offset=10, limit=5) == {'q': 'python', 'remote_only': False, 'offset': 10, 'limit': 5}
    with pytest.raises(ValueError, match='currency and pay period'):
        client.search_params({**values, 'min_salary': 0})
    with pytest.raises(ValueError, match='Enter a keyword'):
        client.search_params({**values, 'mode': 'Semantic match', 'q': ''})


@pytest.mark.parametrize('error, message', [(requests.Timeout(), 'too long'), (requests.ConnectionError(), 'Cannot reach')])
def test_client_connection_failures_are_actionable(monkeypatch, error, message):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(client.requests, 'get', fail)
    with pytest.raises(client.APIError, match=message):
        client.get_json('/health')


@pytest.mark.parametrize('status, body, message', [(422, {}, 'filters'), (503, {'code': 'semantic_unavailable'}, 'Keyword match'),
                                                 (503, {}, 'refresh'), (500, {}, 'HTTP 500'), (200, [], 'unexpected')])
def test_client_http_and_response_errors(monkeypatch, status, body, message):
    class Response:
        ok = status < 400
        status_code = status
        def json(self): return body
    monkeypatch.setattr(client.requests, 'get', lambda *a, **k: Response())
    with pytest.raises(client.APIError, match=message):
        client.get_json('/jobs')


def test_invalid_results_page_is_not_rendered(monkeypatch):
    monkeypatch.setattr(client, 'get_json', lambda *a, **k: {'items': [{}], 'total': 1, 'attribution': {}})
    with pytest.raises(client.APIError, match='incomplete job'):
        client.search('Browse jobs', {})


@pytest.fixture
def ui(monkeypatch, raw_job):
    # Ingestion tests remove sleep globally; AppTest needs cooperative thread waits.
    # External HTTP remains disabled by conftest's offline fixture.
    monkeypatch.setattr(time, 'sleep', real_sleep)
    now = datetime.now(timezone.utc)
    records = []
    for index in range(12):
        raw = {**raw_job, 'guid': f'https://himalayas.app/companies/unit-test/jobs/test-{index:02d}',
               'title': f'Python developer {index:02d}', 'description': '<h3>Requirements</h3><p>Build real Python services.</p>',
               'expiryDate': int((now + timedelta(days=1)).timestamp())}
        records.append({**normalize_job(raw, now).to_record(), 'is_active': True, 'status': 'open', 'status_checked_at': now.isoformat()})
    snapshot = {'records': records, 'attribution': {'label': 'Jobs sourced from Himalayas', 'url': 'https://himalayas.app'},
                'feed_fetched_at': now.isoformat(), 'feed_complete': False}
    app.dependency_overrides[load_snapshot] = lambda: snapshot
    monkeypatch.setattr(api_module, 'load_snapshot', lambda: snapshot)
    calls = []
    with TestClient(app) as api:
        def request(url, params=None, **kwargs):
            calls.append((urlsplit(url).path, params))
            observed = api.get(urlsplit(url).path, params=params)
            response = requests.Response()
            response.status_code = observed.status_code
            response._content = observed.content
            return response
        monkeypatch.setattr(client.requests, 'get', request)
        try:
            yield AppTest.from_file(str(Path('frontend/app.py').resolve()), default_timeout=20), calls
        finally:
            app.dependency_overrides.clear()


def button(ui, label):
    return next(b for b in ui.button if b.label == label)


def test_streamlit_actual_api_contract_search_reset_and_selection(ui):
    screen, calls = ui
    screen.run()
    assert not screen.exception
    assert any(b.label == 'Python developer 00' for b in screen.button)
    button(screen, 'Python developer 01').click().run()
    assert screen.session_state.selected_id.endswith('test-01')
    screen.text_input(key='q').set_value('unmatchedphrase')
    button(screen, 'Search jobs').click().run()
    assert not screen.exception and any(b.label == 'Reset search' for b in screen.button)
    assert calls[-1][1]['q'] == 'unmatchedphrase'
    button(screen, 'Clear filters').click().run()
    assert screen.text_input(key='q').value == ''
    assert screen.session_state.offset == 0 and any(b.label == 'Python developer 00' for b in screen.button)


def test_streamlit_country_salary_and_semantic_validation(ui):
    screen, calls = ui
    screen.run()
    screen.selectbox(key='country').set_value('US')
    button(screen, 'Search jobs').click().run()
    assert any(b.label == 'Reset search' for b in screen.button)
    button(screen, 'Clear filters').click().run()
    screen.number_input(key='min_salary').set_value(50000)
    button(screen, 'Search jobs').click().run()
    assert 'currency and pay period' in screen.error[0].value
    assert 'min_salary' not in calls[-1][1]
    button(screen, 'Clear filters').click().run()
    screen.radio(key='mode').set_value('Semantic match')
    button(screen, 'Search jobs').click().run()
    assert 'Enter a keyword' in screen.error[0].value


def test_streamlit_pagination_and_filter_reset(ui):
    screen, calls = ui
    screen.run()
    screen.selectbox(key='page_size').set_value(5).run()
    button(screen, 'Next').click().run()
    assert screen.session_state.offset == 5
    assert calls[-1][1]['offset'] == 5
    assert screen.session_state.selected_id.endswith('test-05')
    screen.text_input(key='role').set_value('developer 00')
    button(screen, 'Search jobs').click().run()
    assert screen.session_state.offset == 0
    assert button(screen, 'Next').disabled


def test_streamlit_unavailable_clears_previous_results(ui, monkeypatch):
    screen, _ = ui
    screen.run()
    def fail(*a, **k): raise client.APIError('Cannot reach the job service.')
    monkeypatch.setattr(client, 'get_json', fail)
    screen.run()
    assert not screen.exception and 'Cannot reach' in screen.error[0].value
    assert not any(str(b.key).startswith('select_job_') for b in screen.button)
    assert any(b.label == 'Retry connection' for b in screen.button)
