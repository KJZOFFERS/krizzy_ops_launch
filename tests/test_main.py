"""Tests for main Flask application."""

import pytest
from unittest.mock import patch
from main import app


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert "ts" in data


@patch("main.run_rei")
@patch("main.kpi")
@patch("main.post_err")
def test_rei_endpoint_success(mock_post_err, mock_kpi, mock_run_rei, client):
    """Test REI endpoint success."""
    mock_run_rei.return_value = 5

    response = client.post("/ops/rei")
    data = response.get_json()

    assert response.status_code == 200
    assert data["REI_Leads"] == 5
    mock_run_rei.assert_called_once()


@patch("main.run_rei")
@patch("main.kpi")
@patch("main.post_err")
def test_rei_endpoint_error(mock_post_err, mock_kpi, mock_run_rei, client):
    """Test REI endpoint error handling."""
    mock_run_rei.side_effect = Exception("Test error")

    response = client.post("/ops/rei")
    data = response.get_json()

    assert response.status_code == 500
    assert "error" in data
    mock_post_err.assert_called_once()


@patch("main.run_govcon")
@patch("main.kpi")
@patch("main.post_err")
def test_govcon_endpoint_success(mock_post_err, mock_kpi, mock_run_govcon, client):
    """Test GovCon endpoint success."""
    mock_run_govcon.return_value = 3

    response = client.post("/ops/govcon")
    data = response.get_json()

    assert response.status_code == 200
    assert data["GovCon_Opportunities"] == 3
    mock_run_govcon.assert_called_once()


@patch("main.run_watchdog")
@patch("main.kpi")
@patch("main.post_err")
def test_watchdog_endpoint_success(mock_post_err, mock_kpi, mock_run_watchdog, client):
    """Test watchdog endpoint success."""
    mock_run_watchdog.return_value = 2

    response = client.post("/ops/watchdog")
    data = response.get_json()

    assert response.status_code == 200
    assert data["Invalid_Records"] == 2
    mock_run_watchdog.assert_called_once()
