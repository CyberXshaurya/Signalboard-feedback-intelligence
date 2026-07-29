import io


def _csv() -> bytes:
    return b"""feedback_text,source,user_type,product_area,date,rating
Exporting large reports takes several minutes,Support,Enterprise,Reporting,2025-01-02,2
The report export freezes when the date range is long,Survey,Power user,Reporting,2025-01-09,2
CSV reports are extremely slow to download,App review,Enterprise,Reporting,2025-01-16,1
I cannot understand why the invoice total changed,Support,New user,Billing,2025-02-01,2
The billing screen does not explain extra charges,Survey,New user,Billing,2025-02-08,2
Invoice charges are confusing and have no breakdown,Email,Administrator,Billing,2025-02-15,3
I like the new dashboard colours,Survey,Power user,Dashboard,2025-03-01,5
"""


def test_complete_engine_workflow(client):
    project = client.post("/api/v1/projects", json={"name": "Demo feedback"}).json()
    history = client.post(
        f"/api/v1/projects/{project['id']}/historical-themes",
        json={
            "title": "Large report exports time out",
            "description": "Customers previously reported slow or failed exports for large reports.",
            "product_area": "Reporting",
        },
    )
    assert history.status_code == 201

    upload = client.post(
        f"/api/v1/projects/{project['id']}/datasets",
        files={"file": ("feedback.csv", io.BytesIO(_csv()), "text/csv")},
    )
    assert upload.status_code == 201, upload.text
    dataset = upload.json()
    assert dataset["valid_rows"] == 7

    analysis = client.post(f"/api/v1/datasets/{dataset['id']}/analysis-runs")
    assert analysis.status_code == 201, analysis.text
    run = analysis.json()
    assert run["status"] == "ready_for_review"

    themes_response = client.get(f"/api/v1/analysis-runs/{run['id']}/themes")
    themes = themes_response.json()
    assert len(themes) >= 2

    first = client.get(f"/api/v1/themes/{themes[0]['id']}").json()
    assert first["metrics"]["feedback_count"] >= 1
    assert first["evidence"]
    assert any(item["is_primary_evidence"] for item in first["evidence"])

    summary = client.get(f"/api/v1/analysis-runs/{run['id']}/summary")
    assert summary.status_code == 200
    assert summary.json()["coverage_percentage"] == 100.0

    logs = client.get(f"/api/v1/analysis-runs/{run['id']}/logs")
    assert logs.status_code == 200
    assert any(item["event_type"] == "analysis.completed" for item in logs.json())

    renamed = client.patch(
        f"/api/v1/themes/{themes[0]['id']}/rename", json={"title": "Reviewed theme"}
    )
    assert renamed.status_code == 200

    for theme in themes[:2]:
        approved = client.post(f"/api/v1/themes/{theme['id']}/approve")
        assert approved.status_code == 200

    report = client.post(
        f"/api/v1/analysis-runs/{run['id']}/reports", json={"title": "Reviewed synthesis"}
    )
    assert report.status_code == 201, report.text
    detail = client.get(f"/api/v1/reports/{report.json()['id']}")
    assert detail.status_code == 200
    saved_titles = [item["theme_title"] for item in detail.json()["themes"]]
    assert len(saved_titles) == 2

    client.patch(
        f"/api/v1/themes/{themes[0]['id']}/rename", json={"title": "Changed after report"}
    )
    immutable = client.get(f"/api/v1/reports/{report.json()['id']}").json()
    assert [item["theme_title"] for item in immutable["themes"]] == saved_titles

    history = client.get(f"/api/v1/themes/{themes[0]['id']}/history")
    assert history.status_code == 200
    assert any(item["action_type"] == "rename" for item in history.json())
