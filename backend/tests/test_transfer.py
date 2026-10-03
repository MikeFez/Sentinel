def test_export_then_import_into_an_empty_instance(client):
    owned = client.post("/api/tags", json={"name": "Owned", "color": "#123456"}).json()
    c = client.post("/api/companies", json={"name": "Rocket Lab", "ticker": "RKLB", "shares_owned": 950, "alert_above": 150}).json()
    client.post(f"/api/companies/{c['id']}/tags", json={"tag_ids": [owned["id"]]})
    client.post("/api/companies", json={"name": "Quaise", "status": "private", "description": "Geothermal"})
    client.put("/api/settings", json={"news_count": "15"})

    data = client.get("/api/export").json()
    assert data["format"] == "sentinel-export" and data["version"] == 1
    assert {x["name"] for x in data["companies"]} == {"Rocket Lab", "Quaise"}
    assert data["settings"] == {"news_count": "15"}

    # Wipe and re-import
    for x in client.get("/api/companies").json():
        client.delete(f"/api/companies/{x['id']}")
    client.delete(f"/api/tags/{owned['id']}")
    client.put("/api/settings", json={"news_count": "10"})

    preview = client.post("/api/import", json={"data": data, "dry_run": True}).json()
    assert sorted(preview["created"]) == ["Quaise", "Rocket Lab"] and preview["settings_changed"] == 1
    assert client.get("/api/companies").json() == []  # dry run saved nothing

    result = client.post("/api/import", json={"data": data}).json()
    assert sorted(result["created"]) == ["Quaise", "Rocket Lab"] and result["tags_created"] == 1
    rklb = next(x for x in client.get("/api/companies").json() if x["ticker"] == "RKLB")
    assert rklb["shares_owned"] == 950 and rklb["alert_above"] == 150 and [t["name"] for t in rklb["tags"]] == ["Owned"]
    assert client.get("/api/settings").json()["news_count"] == "15"


def test_import_merges_by_ticker_and_never_deletes(client):
    client.post("/api/companies", json={"name": "Rocket Lab USA", "ticker": "RKLB", "shares_owned": 10})
    client.post("/api/companies", json={"name": "Keep Me", "ticker": "KEEP"})
    data = {"format": "sentinel-export", "version": 1, "companies": [{"name": "Rocket Lab", "ticker": "rklb", "shares_owned": 950}]}
    result = client.post("/api/import", json={"data": data, "include_settings": False}).json()
    assert result["created"] == [] and result["updated"] == ["Rocket Lab"]
    names = sorted(x["name"] for x in client.get("/api/companies").json())
    assert names == ["Keep Me", "Rocket Lab"]


def test_rejects_other_files(client):
    r = client.post("/api/import", json={"data": {"format": "something-else", "version": 1}})
    assert r.status_code == 400
