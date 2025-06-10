# import pytest # Removed: No longer needed for @pytest.mark.asyncio for this test
from fastapi.testclient import TestClient
from fastapi import status
import time
import uuid
import os
import asyncio # Keep for general async test utilities if other tests use it, or if TestClient implies its need
# from asyncio import Queue # Removed: No longer needed for this test
from datetime import datetime
# from unittest.mock import patch # Ensure this is removed if not used by other tests

from starlette.websockets import WebSocketDisconnect

# Import app from backend.main IF it's needed for module-level overrides by other tests.
# For reverting this specific test, direct app import is not needed by the test itself.
# However, other tests (like test_stream_log_invalid_job_id) might be using it.
# The original prompt for this subtask implied removing main app/dependency imports if solely for this test.
# For safety, I will remove specific imports for get_log_queue etc., but keep `import backend.main`.
import backend.main
# from backend.main import app, get_log_queue # Removed specific DI-related imports

VALID_BACKTEST_SETTINGS = {
    "initial_capital": 100000, "markets": ["EUR/USD"], "entry_donchian_period": 20,
    "take_profit_long_exit_period": 10, "take_profit_short_exit_period": 10,
    "atr_period": 14, "stop_loss_atr_multiplier": 2.0, "risk_per_trade": 0.01,
    "total_portfolio_risk_limit": 0.05, "slippage_pips": 0.5, "commission_per_lot": 4.0,
    "pip_point_value": {"EUR/USD": 0.0001}, "lot_size": {"EUR/USD": 100000},
    "max_units_per_market": {"EUR/USD": 500000}
}

VALID_DATA_COLLECTION_REQUEST = {
    "symbol": "USDJPY", "startYear": 2023, "startMonth": 1, "endYear": 2023, "endMonth": 12,
    "apiKey": "test_key_optional"
}

DATA_DIR_TEST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))

# Removed module-level queue and override function if they were here.
# Removed app.dependency_overrides[...] call if it was at module level.

def test_health_check(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}

def test_run_backtest_success(client: TestClient):
    response = client.post("/api/backtest/run", json=VALID_BACKTEST_SETTINGS)
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)

def test_run_backtest_invalid_input(client: TestClient):
    invalid_settings = VALID_BACKTEST_SETTINGS.copy()
    del invalid_settings["initial_capital"]
    response = client.post("/api/backtest/run", json=invalid_settings)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_get_status_non_existent_job(client: TestClient):
    non_existent_job_id = str(uuid.uuid4())
    response = client.get(f"/api/backtest/status/{non_existent_job_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Job not found"

def test_get_results_non_existent_job(client: TestClient):
    non_existent_job_id = str(uuid.uuid4())
    response = client.get(f"/api/backtest/results/{non_existent_job_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Job not found"

def test_get_status_and_results_flow(client: TestClient):
    run_response = client.post("/api/backtest/run", json=VALID_BACKTEST_SETTINGS)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id = run_response.json()["job_id"]
    status_response_pending = client.get(f"/api/backtest/status/{job_id}")
    assert status_response_pending.status_code == status.HTTP_200_OK
    pending_data = status_response_pending.json()
    assert pending_data["job_id"] == job_id
    if pending_data["status"] == "failed":
        pytest.fail(f"Job {job_id} failed immediately. Error: {pending_data.get('message', 'N/A')}")
    assert pending_data["status"] in ["pending", "completed", "running"]
    max_wait_time = 20; poll_interval = 0.5; start_time = time.time(); job_completed = False
    while time.time() - start_time < max_wait_time:
        s_response = client.get(f"/api/backtest/status/{job_id}")
        s_data = s_response.json()
        if s_data["status"] == "completed": job_completed = True; break
        if s_data["status"] == "failed": pytest.fail(f"Job {job_id} failed: {s_data.get('message', 'N/A')}")
        time.sleep(poll_interval)
    assert job_completed, f"Job {job_id} did not complete in {max_wait_time}s."
    results_response = client.get(f"/api/backtest/results/{job_id}")
    assert results_response.status_code == status.HTTP_200_OK
    res_data = results_response.json()
    assert res_data["job_id"] == job_id and res_data["status"] == "completed"
    assert res_data["results"] is not None and "Initial Capital" in res_data["results"]
    assert isinstance(res_data.get("equity_curve"), list) and isinstance(res_data.get("trade_log"), list)
    if res_data["equity_curve"]: assert "timestamp" in res_data["equity_curve"][0]

def test_run_backtest_and_fail_missing_data_file(client: TestClient, monkeypatch):
    def mock_load_fails(file_path): raise FileNotFoundError("Mocked error")
    monkeypatch.setattr('backend.main.data_loader.load_csv_data', mock_load_fails)
    run_response = client.post("/api/backtest/run", json=VALID_BACKTEST_SETTINGS)
    job_id = run_response.json()["job_id"]
    max_wait=10; poll_interval=0.5; start_time=time.time(); job_failed=False
    while time.time()-start_time < max_wait:
        s_response = client.get(f"/api/backtest/status/{job_id}")
        s_data = s_response.json()
        if s_data["status"] == "failed": job_failed=True; assert "Mocked error" in s_data.get("message",""); break
        assert s_data["status"] != "completed"
        time.sleep(poll_interval)
    assert job_failed, f"Job {job_id} did not fail as expected."
    res_response = client.get(f"/api/backtest/results/{job_id}")
    assert res_response.json()["status"] == "failed" and "Mocked error" in res_response.json().get("message","")

def test_collect_data_success(client: TestClient):
    response = client.post("/api/data/collect", json=VALID_DATA_COLLECTION_REQUEST)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "job_id" in response.json()

def test_collect_data_invalid_input(client: TestClient):
    payload = VALID_DATA_COLLECTION_REQUEST.copy(); del payload["symbol"]
    response = client.post("/api/data/collect", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_data_collection_job_status_flow(client: TestClient):
    job_id = client.post("/api/data/collect",json=VALID_DATA_COLLECTION_REQUEST).json()["job_id"]
    max_wait=10; poll_interval=0.5; start_time=time.time(); completed_ok=False
    while time.time()-start_time < max_wait:
        s_data = client.get(f"/api/backtest/status/{job_id}").json()
        if s_data["status"] == "completed": assert s_data.get("message") == "Data collection finished."; completed_ok=True; break
        if s_data["status"] == "failed": pytest.fail(f"Job {job_id} failed: {s_data.get('message','N/A')}")
        assert s_data["status"] in ["pending", "running"]
        time.sleep(poll_interval)
    assert completed_ok, f"Job {job_id} did not complete successfully."

def test_list_data_files_success(client: TestClient):
    response = client.get("/api/data/files")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "files" in data and "total_files" in data
    assert isinstance(data["files"], list) and isinstance(data["total_files"], int)

def test_list_data_files_empty_directory(client: TestClient, monkeypatch):
    monkeypatch.setattr(backend.main.os, "listdir", lambda path: [])
    response = client.get("/api/data/files")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["files"] == [] and data["total_files"] == 0

def test_list_data_files_directory_not_found(client: TestClient, monkeypatch):
    monkeypatch.setattr(backend.main.os.path, "exists", lambda path: False)
    response = client.get("/api/data/files")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["files"] == [] and data["total_files"] == 0

# --- WebSocket Tests for /api/data/stream_log ---

def test_stream_log_success(client: TestClient):
    # 1. Create a data collection job
    run_response = client.post("/api/data/collect", json=VALID_DATA_COLLECTION_REQUEST)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id = run_response.json()["job_id"]

    # Give a moment for the job to be initialized in job_store
    time.sleep(0.2) # Reverted to 0.2

    log_lines_received = 0
    completion_message_received = False
    final_status_message_received = False

    with client.websocket_connect(f"/api/data/stream_log/{job_id}") as websocket:
        initial_data = websocket.receive_text()
        assert f"Streaming logs for data collection job {job_id}" in initial_data

        max_test_duration = time.time() + 15  # Reverted to 15
        while time.time() < max_test_duration:
            try:
                data = websocket.receive_text()

                if "LOG: Line" in data:
                    log_lines_received += 1

                if f"INFO: Job {job_id} completed" in data:
                    completion_message_received = True

                if f"INFO: Log streaming ended for job {job_id}" in data:
                    final_status_message_received = True
                    break

                if f"ERROR: Job {job_id} failed" in data:
                    pytest.fail(f"Log stream indicated job {job_id} failed.")

            except WebSocketDisconnect:
                if not final_status_message_received:
                    status_resp = client.get(f"/api/backtest/status/{job_id}").json()
                    if status_resp["status"] == "completed":
                        final_status_message_received = True
                        completion_message_received = True
                break
            except Exception as e:
                pytest.fail(f"Unexpected error during WebSocket communication: {e}")
                break

    assert log_lines_received > 0, "Did not receive any simulated log lines."
    assert completion_message_received or final_status_message_received, \
        "Did not receive job completion message or final stream ended message via WebSocket."
    assert final_status_message_received, "Did not receive the final 'Log streaming ended' message."


def test_stream_log_invalid_job_id(client: TestClient):
    non_existent_job_id = str(uuid.uuid4())
    with client.websocket_connect(f"/api/data/stream_log/{non_existent_job_id}") as websocket:
        error_message = websocket.receive_text()
        assert f"ERROR: Job ID {non_existent_job_id} not found or is not a data collection job." in error_message
        with pytest.raises(WebSocketDisconnect) as excinfo:
            websocket.receive_text()
        assert excinfo.value.code == 1008

def test_stream_log_job_not_data_collection(client: TestClient):
    run_response = client.post("/api/backtest/run", json=VALID_BACKTEST_SETTINGS)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id_backtest = run_response.json()["job_id"]
    time.sleep(0.1)
    with client.websocket_connect(f"/api/data/stream_log/{job_id_backtest}") as websocket:
        error_message = websocket.receive_text()
        assert f"ERROR: Job ID {job_id_backtest} not found or is not a data collection job." in error_message
        with pytest.raises(WebSocketDisconnect) as excinfo:
            websocket.receive_text()
        assert excinfo.value.code == 1008
