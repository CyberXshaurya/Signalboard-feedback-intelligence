from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

pytest.importorskip('playwright.sync_api')
from playwright.sync_api import Route, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'src' / 'feedback_intelligence_engine' / 'web'


@pytest.mark.ui
def test_reviewer_ui_keyboard_modals_and_product_memory():
    memory: dict[str, dict] = {
        'history-1': {
            'id': 'history-1',
            'title': 'Large report exports time out',
            'description': 'Previous release notes recorded slow or failed exports for larger date ranges.',
            'product_area': 'Reporting',
            'notes': 'Observed before the export worker migration.',
            'active_from': '2025-01-01',
            'active_until': '2025-06-30',
        },
        'history-2': {
            'id': 'history-2',
            'title': 'Disputed debt remains unresolved',
            'description': 'Support summaries reported repeated disputes about debt ownership and validation.',
            'product_area': 'Debt collection',
            'notes': 'Monitor whether the evidence has evolved.',
            'active_from': '2025-03-01',
            'active_until': None,
        },
        'history-3': {
            'id': 'history-3',
            'title': 'Autopay status is unclear',
            'description': 'Customers previously struggled to confirm whether automatic payments were active.',
            'product_area': 'Loan servicing',
            'notes': 'Historical product note.',
            'active_from': '2025-05-01',
            'active_until': None,
        },
    }

    def handler(route: Route) -> None:
        request = route.request
        parsed = urlparse(request.url)
        path = parsed.path
        if path == '/':
            route.fulfill(status=200, content_type='text/html', body=(WEB / 'index.html').read_text())
            return
        if path == '/app/app.js':
            route.fulfill(status=200, content_type='text/javascript', body=(WEB / 'app.js').read_text())
            return
        if path == '/app/styles.css':
            route.fulfill(status=200, content_type='text/css', body=(WEB / 'styles.css').read_text())
            return
        if path == '/app/cfpb_feedback_sample.csv':
            route.fulfill(status=200, content_type='text/csv', body=(WEB / 'cfpb_feedback_sample.csv').read_bytes())
            return
        if path == '/api/v1/providers/self-test':
            route.fulfill(
                status=200,
                content_type='application/json',
                body=json.dumps(
                    {
                        'status': 'ok',
                        'provider': 'github',
                        'model': 'openai/gpt-4.1-mini',
                        'llm_operational': True,
                        'latency_ms': 184,
                        'message': 'GitHub Models returned a live inference response.',
                        'request_id': 'browser-check',
                    }
                ),
            )
            return
        if '/historical-themes' in path:
            parts = path.rstrip('/').split('/')
            historical_id = parts[-1] if parts[-1] != 'historical-themes' else None
            payload = json.loads(request.post_data or '{}')
            if request.method == 'POST':
                item = {'id': 'history-new', **payload}
                memory[item['id']] = item
                route.fulfill(status=201, content_type='application/json', body=json.dumps(item))
                return
            if request.method == 'PATCH' and historical_id:
                item = {**memory[historical_id], **payload}
                memory[historical_id] = item
                route.fulfill(status=200, content_type='application/json', body=json.dumps(item))
                return
            if request.method == 'DELETE' and historical_id:
                memory.pop(historical_id, None)
                route.fulfill(status=204)
                return
        route.fulfill(status=404, content_type='application/json', body='{"detail":"not mocked"}')

    with sync_playwright() as runner:
        executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE')
        if not executable and Path('/usr/bin/chromium').exists():
            executable = '/usr/bin/chromium'
        browser = runner.chromium.launch(
            headless=True,
            executable_path=executable,
            args=['--no-sandbox', '--disable-setuid-sandbox'],
        )
        page = browser.new_page(viewport={'width': 1480, 'height': 1000})
        page.route('https://signalboard.test/**', handler)
        page.route('https://fonts.googleapis.com/**', lambda route: route.fulfill(status=200, content_type='text/css', body=''))
        page.route('https://fonts.gstatic.com/**', lambda route: route.fulfill(status=204))
        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
        page.on('pageerror', lambda error: page_errors.append(str(error)))

        html = (WEB / 'index.html').read_text()
        html = html.replace('<link rel="stylesheet" href="/app/styles.css" />', f'<style>{(WEB / "styles.css").read_text()}</style>')
        html = html.replace('<script type="module" src="/app/app.js"></script>', '<script>window.__SIGNALBOARD_PREVIEW__=true;</script>')
        html = html.replace('<head>', '<head><base href="https://signalboard.test/">', 1)
        page.set_content(html, wait_until='domcontentloaded')
        page.add_script_tag(content=(WEB / 'app.js').read_text(), type='module')
        page.get_by_role('button', name='Provider settings').wait_for()
        page.get_by_role('button', name='Provider settings').click()
        page.get_by_role('button', name='Done').click()
        assert page.locator('[role="dialog"]').count() == 0

        page.get_by_role('button', name='Provider settings').click()
        page.get_by_role('button', name='Run live provider check').click()
        page.get_by_text('Live inference verified').wait_for()
        page.keyboard.press('Escape')
        assert page.locator('[role="dialog"]').count() == 0

        page.get_by_role('button', name='History').click()
        page.get_by_role('button', name='Add product note').click()
        page.locator('#history-title').fill('Export history')
        page.locator('#history-description').fill('Earlier customers reported timeouts for large report exports.')
        page.locator('#history-area').fill('Reporting')
        page.get_by_role('button', name='Add to product memory').click()
        page.get_by_role('heading', name='Export history').wait_for()

        page.get_by_role('button', name='Edit Export history').click()
        page.locator('#history-title').fill('Large export history')
        page.get_by_role('button', name='Save changes').click()
        page.get_by_role('heading', name='Large export history').wait_for()

        page.get_by_role('button', name='Delete Large export history').click()
        page.get_by_role('button', name='Keep record').click()
        assert page.get_by_role('heading', name='Large export history').count() == 1

        page.get_by_role('button', name='Themes').click()
        page.get_by_role('button', name='Reject').click()
        page.get_by_role('button', name='Close dialog').click()
        assert page.locator('[role="dialog"]').count() == 0

        page.keyboard.press('i')
        page.get_by_role('heading', name='Import product feedback').wait_for()
        page.keyboard.press('Escape')
        assert page.locator('[role="dialog"]').count() == 0

        browser.close()
        assert page_errors == []
        assert console_errors == []
