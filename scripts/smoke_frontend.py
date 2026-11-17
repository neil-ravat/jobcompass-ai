"""Real local HTTP/browser checks; no fixture jobs are supplied to the application.

Run: .venv/bin/python scripts/smoke_frontend.py
Requires the native demo, Streamlit, and installed Google Chrome.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import requests
from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8501')
    parser.add_argument('--api', default='http://127.0.0.1:8765')
    parser.add_argument('--output', type=Path, default=Path('data/evidence/frontend'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    response = requests.get(args.api + '/recommendations', timeout=15)
    response.raise_for_status()
    baseline = response.json()
    assert baseline['items'], 'The real corpus must contain a currently verified job for this acceptance check.'
    first = baseline['items'][0]
    assert isinstance(first['description'], str)
    evidence = {'verified_at': datetime.now(timezone.utc).isoformat(), 'baseline_total': baseline['total'],
                'source': baseline['attribution'], 'checks': [], 'screenshots': []}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='networkidle')
        expect(page.locator('.st-key-select_job_0')).to_be_visible(timeout=20000)
        expect(page.locator('.st-key-results').get_by_role('heading', name=f"{baseline['total']} {'job' if baseline['total'] == 1 else 'jobs'}", exact=True)).to_be_visible()
        expect(page.get_by_role('link', name='Apply on Himalayas')).to_have_attribute('href', first['application_url'])
        expect(page.get_by_role('link', name='Apply on Himalayas')).to_have_attribute('target', '_blank')
        assert not page.get_by_role('textbox', name=re.compile('chat', re.I)).count()
        page.screenshot(path=str(args.output / 'desktop.png'))
        evidence['screenshots'].append('desktop.png')
        evidence['checks'].append('Initial real results and original external application URL')

        if len(baseline['items']) > 1:
            second = baseline['items'][1]
            page.locator('.st-key-select_job_1').click()
            expect(page.locator('.detail-title')).to_have_text(second['title'])
            expect(page.get_by_role('link', name='Apply on Himalayas')).to_have_attribute('href', second['application_url'])
            evidence['checks'].append('Selecting a second real job updates details and Apply URL')

        # Use an actual title as the query, without hardcoding a job record.
        query = first['title']
        page.get_by_label('Keywords or skills', exact=True).fill(query)
        page.get_by_role('button', name='Search jobs').click()
        expected = requests.get(args.api + '/recommendations', params={'q': query, 'remote_only': True}, timeout=30).json()
        expect(page.locator('.st-key-applied_filters')).to_contain_text(query)
        expect(page.locator('.section-heading h2')).to_have_text(f"{expected['total']} {'job' if expected['total'] == 1 else 'jobs'}")
        page.get_by_role('tab', name='Why this match').click()
        expect(page.locator('.score-summary strong')).to_have_text(f"{expected['items'][0]['score']:.2f}")
        evidence['checks'].append('Keyword search and displayed score match the live API')

        page.locator('[data-testid="stSidebar"]').get_by_text('Semantic match', exact=True).click()
        page.get_by_role('button', name='Search jobs').click()
        expect(page.locator('.st-key-applied_filters')).to_contain_text('Semantic match')
        page.get_by_role('tab', name='Why this match').click()
        semantic = requests.get(args.api + '/search', params={'q': query, 'remote_only': True}, timeout=45)
        semantic.raise_for_status()
        expect(page.locator('.score-summary strong')).to_have_text(f"{semantic.json()['items'][0]['score']:.2f}")
        expect(page.locator('.score-row').filter(has_text='Semantic')).to_be_visible()
        page.screenshot(path=str(args.output / 'desktop-match.png'))
        evidence['screenshots'].append('desktop-match.png')
        evidence['checks'].append('Semantic mode and exact backend component explanation')

        page.get_by_role('button', name='Clear filters').click()
        expect(page.get_by_label('Keywords or skills', exact=True)).to_have_value('')
        country_input = page.get_by_role('combobox', name='Country eligibility')
        country_input.fill('India')
        page.get_by_role('option', name='India', exact=True).click()
        page.get_by_role('button', name='Search jobs').click()
        country = requests.get(args.api + '/recommendations', params={'country': 'IN', 'remote_only': True}, timeout=20).json()
        expect(page.locator('.section-heading h2')).to_have_text(f"{country['total']} {'job' if country['total'] == 1 else 'jobs'}")
        evidence['checks'].append('Country filter total matches the real API')
        page.get_by_role('button', name='Clear filters').click()
        page.get_by_text('Salary constraints', exact=True).click()
        page.get_by_role('spinbutton', name='Minimum advertised salary').fill('100000')
        page.get_by_role('button', name='Search jobs').click()
        expect(page.get_by_text('Choose a currency and pay period for your minimum salary.', exact=False)).to_be_visible()
        page.get_by_role('combobox', name='Currency', exact=True).fill('USD')
        page.get_by_role('option', name='USD', exact=True).click()
        page.get_by_role('combobox', name='Pay period', exact=True).click()
        page.get_by_role('option', name='Annual', exact=True).click()
        page.get_by_role('button', name='Search jobs').click()
        salary = requests.get(args.api + '/recommendations', params={'min_salary': 100000, 'currency': 'USD', 'salary_period': 'annual'}, timeout=20).json()
        expect(page.locator('.section-heading h2')).to_have_text(f"{salary['total']} {'job' if salary['total'] == 1 else 'jobs'}")
        evidence['checks'].append('Salary units validation and valid salary filtering match the real API')
        page.get_by_role('button', name='Clear filters').click()
        page.get_by_label('Keywords or skills', exact=True).fill('zzjobcompassnomatchzz')
        page.get_by_role('button', name='Search jobs').click()
        expect(page.get_by_role('heading', name='No jobs match these filters')).to_be_visible()
        page.screenshot(path=str(args.output / 'desktop-empty.png'))
        evidence['screenshots'].append('desktop-empty.png')
        page.get_by_role('button', name='Reset search', exact=True).click()
        expect(page.locator('.st-key-select_job_0')).to_be_visible()
        evidence['checks'].append('Useful empty state and reset restores real results')

        mobile = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, device_scale_factor=1)
        mobile.goto(args.url, wait_until='networkidle')
        expect(mobile.locator('.st-key-select_job_0')).to_be_visible(timeout=20000)
        expect(mobile.locator('.st-key-detail')).not_to_be_visible()
        expect(mobile.get_by_role('button', name='Expand sidebar', exact=True)).to_be_visible()
        mobile.screenshot(path=str(args.output / 'narrow-results.png'))
        evidence['screenshots'].append('narrow-results.png')
        mobile.locator('.st-key-select_job_0').click()
        expect(mobile.locator('.st-key-detail')).to_be_visible()
        expect(mobile.locator('.st-key-results')).not_to_be_visible()
        mobile.screenshot(path=str(args.output / 'narrow-details.png'))
        evidence['screenshots'].append('narrow-details.png')
        assert not mobile.evaluate('document.documentElement.scrollWidth > innerWidth'), 'Horizontal overflow'
        mobile.get_by_role('button', name='Expand sidebar', exact=True).click()
        expect(mobile.get_by_role('button', name='Collapse sidebar', exact=True)).to_be_visible()
        mobile.get_by_label('Role in job title', exact=True).fill(first['title'].split()[0])
        mobile.get_by_role('button', name='Search jobs').click()
        mobile.get_by_role('button', name='Collapse sidebar', exact=True).click()
        expect(mobile.locator('.st-key-results')).to_be_visible()
        evidence['checks'].append('390px layout: results/details switch, usable filter drawer, no horizontal overflow')
        # Keyboard activation of an actual result must reach the detail panel too.
        mobile.get_by_role('button', name=first['title'], exact=True).focus()
        mobile.keyboard.press('Enter')
        expect(mobile.locator('.st-key-detail')).to_be_visible()
        evidence['checks'].append('Keyboard activation selects a real job')
        mobile.set_viewport_size({'width': 320, 'height': 740})
        assert not mobile.evaluate('document.documentElement.scrollWidth > innerWidth'), '320px horizontal overflow'
        evidence['checks'].append('320px layout has no horizontal document overflow')
        assert not errors, errors
        evidence['browser_errors'] = errors
        browser.close()
    (args.output / 'browser-results.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
