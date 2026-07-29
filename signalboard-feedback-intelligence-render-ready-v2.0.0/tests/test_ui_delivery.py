def test_reviewer_ui_is_served_with_static_assets(client):
    index = client.get("/")
    assert index.status_code == 200
    assert "Signalboard" in index.text
    assert "/app/app.js" in index.text

    script = client.get("/app/app.js")
    styles = client.get("/app/styles.css")
    sample = client.get("/app/cfpb_feedback_sample.csv")

    assert script.status_code == 200
    assert "Run real sample" in script.text
    assert styles.status_code == 200
    assert ".theme-workspace" in styles.text
    assert sample.status_code == 200
    assert b"feedback_text" in sample.content[:200]


def test_every_visible_data_action_has_a_dispatch_handler():
    from pathlib import Path
    import re

    script = Path('src/feedback_intelligence_engine/web/app.js').read_text()
    actions = set(re.findall(r'data-action=\\?"([^"$]+)\\?"', script))
    handlers = set(re.findall(r"action === '([^']+)'", script))
    assert actions <= handlers
    assert {'close-modal', 'add-history', 'edit-history', 'delete-history', 'save-report'} <= actions
