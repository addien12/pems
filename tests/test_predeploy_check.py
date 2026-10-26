from scripts import predeploy_check


def test_production_readiness_requires_secure_cookie_and_non_local_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example/pems")
    monkeypatch.setenv("PEMS_COOKIE_SECURE", "true")

    results = predeploy_check.run_checks("production")

    assert all(status == "ok" for _, status, _ in results)


def test_production_readiness_rejects_local_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1/pems")
    monkeypatch.setenv("PEMS_COOKIE_SECURE", "true")

    results = predeploy_check.run_checks("production")

    assert dict((name, status) for name, status, _ in results)["database_url"] == "error"


def test_production_readiness_requires_secure_cookie(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example/pems")
    monkeypatch.setenv("PEMS_COOKIE_SECURE", "false")

    results = predeploy_check.run_checks("production")

    assert dict((name, status) for name, status, _ in results)["cookie_secure"] == "error"


def test_readiness_does_not_include_database_url_in_messages(monkeypatch):
    database_url = "postgresql://secret-user:secret-password@db.example/pems"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("PEMS_COOKIE_SECURE", "true")

    messages = [detail for _, _, detail in predeploy_check.run_checks("production")]

    assert database_url not in " ".join(detail or "" for detail in messages)
