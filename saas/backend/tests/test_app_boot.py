def test_fastapi_app_imports_with_routes_registered():
    """Catch startup-time route registration errors before deployment."""
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/api/health" in paths
