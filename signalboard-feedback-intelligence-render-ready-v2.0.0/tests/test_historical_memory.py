def test_historical_theme_crud(client):
    project = client.post('/api/v1/projects', json={'name': 'Product memory'}).json()
    created = client.post(
        f"/api/v1/projects/{project['id']}/historical-themes",
        json={
            'title': 'Export delays',
            'description': 'Previous releases had long export completion times.',
            'product_area': 'Reporting',
            'notes': 'Release retrospective',
            'active_from': '2025-01-01',
        },
    )
    assert created.status_code == 201
    item = created.json()

    listed = client.get(f"/api/v1/projects/{project['id']}/historical-themes")
    assert listed.status_code == 200
    assert listed.json()[0]['id'] == item['id']

    updated = client.patch(
        f"/api/v1/projects/{project['id']}/historical-themes/{item['id']}",
        json={'title': 'Large export delays', 'notes': 'Updated after review'},
    )
    assert updated.status_code == 200
    assert updated.json()['title'] == 'Large export delays'
    assert updated.json()['notes'] == 'Updated after review'

    deleted = client.delete(
        f"/api/v1/projects/{project['id']}/historical-themes/{item['id']}"
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/projects/{project['id']}/historical-themes").json() == []


def test_provider_self_test_reports_deterministic_fallback(client):
    response = client.post('/api/v1/providers/self-test', json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload['provider'] == 'heuristic'
    assert payload['llm_operational'] is False
    assert payload['status'] == 'degraded'
