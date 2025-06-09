import pytest
from fastapi.testclient import TestClient
from fastapi import status # For status codes
import time # To allow background tasks to process
import uuid # To generate non-existent job_ids for testing

# Assuming 'client' fixture is available from conftest.py

# Basic valid settings for /api/backtest/run
VALID_BACKTEST_SETTINGS = {
    "initial_capital": 100000,
    "markets": ["EUR/USD"], # Ensure historical_data.csv is suitable for EUR/USD
    "entry_donchian_period": 20,
    "take_profit_long_exit_period": 10,
    "take_profit_short_exit_period": 10,
    "atr_period": 14,
    "stop_loss_atr_multiplier": 2.0,
    "risk_per_trade": 0.01,
    "total_portfolio_risk_limit": 0.05,
    "slippage_pips": 0.5,
    "commission_per_lot": 4.0,
    "pip_point_value": {"EUR/USD": 0.0001},
    "lot_size": {"EUR/USD": 100000},
    "max_units_per_market": {"EUR/USD": 500000}
}

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
    # Further checks for job processing will be in integration tests

def test_run_backtest_invalid_input(client: TestClient):
    invalid_settings = VALID_BACKTEST_SETTINGS.copy()
    del invalid_settings["initial_capital"] # Make it invalid
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

# The following tests depend on a job being submitted and processed.
# These are more like integration tests but are placed here for API behavior.
# A more robust way might involve mocking the background task for pure unit tests.

def test_get_status_and_results_flow(client: TestClient):
    # 1. Submit a job
    run_response = client.post("/api/backtest/run", json=VALID_BACKTEST_SETTINGS)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id = run_response.json()["job_id"]

    # 2. Check status while pending (might be too fast for TestClient)
    status_response_pending = client.get(f"/api/backtest/status/{job_id}")
    assert status_response_pending.status_code == status.HTTP_200_OK
    pending_data = status_response_pending.json()
    assert pending_data["job_id"] == job_id

    # Check the status
    if pending_data["status"] == "failed":
        error_message = pending_data.get("message", "No error message provided by API for failed job.")
        pytest.fail(f"Job {job_id} failed immediately. Error: {error_message}")

    # Depending on TestClient's handling of background tasks, it might be "completed" already
    # or "pending". This assertion is thus somewhat flexible.
    assert pending_data["status"] in ["pending", "completed", "running"]


    # 3. Poll for completion (max ~10-20 seconds for typical test data)
    # Note: TestClient runs background tasks typically before returning response from the
    # endpoint that spawned them if they are simple. If run_strategy is quick,
    # it might already be completed.
    # This loop is more for "real" async behavior or longer tasks.
    max_wait_time = 20  # seconds
    poll_interval = 0.5 # seconds
    start_time = time.time()
    job_completed = False

    while time.time() - start_time < max_wait_time:
        status_response = client.get(f"/api/backtest/status/{job_id}")
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        if status_data["status"] == "completed":
            job_completed = True
            break
        if status_data["status"] == "failed":
            pytest.fail(f"Job {job_id} failed during test: {status_data.get('message', 'No error message')}")
        time.sleep(poll_interval)

    assert job_completed, f"Job {job_id} did not complete within {max_wait_time} seconds."

    # 4. Get results for the completed job
    results_response = client.get(f"/api/backtest/results/{job_id}")
    assert results_response.status_code == status.HTTP_200_OK
    results_data = results_response.json()

    assert results_data["job_id"] == job_id
    assert results_data["status"] == "completed"
    assert results_data["results"] is not None
    assert "Initial Capital" in results_data["results"] # Check for a sample KPI
    assert "equity_curve" in results_data
    assert isinstance(results_data["equity_curve"], list)
    assert "trade_log" in results_data
    assert isinstance(results_data["trade_log"], list)

    if results_data["equity_curve"]: # If not empty
        assert "timestamp" in results_data["equity_curve"][0]
        assert "equity" in results_data["equity_curve"][0]

    # 5. Test getting results for a pending job (by submitting another one and not waiting)
    # This is tricky because the job might complete very fast.
    # For a true "pending" state test, one might need to mock the duration of run_backtest_task.
    # For now, we'll just check the structure if we query immediately.
    run_response_2 = client.post("/api/backtest/run", json=VALID_BACKTEST_SETTINGS)
    job_id_2 = run_response_2.json()["job_id"]
    results_response_pending = client.get(f"/api/backtest/results/{job_id_2}")
    assert results_response_pending.status_code == status.HTTP_200_OK
    pending_results_data = results_response_pending.json()
    assert pending_results_data["job_id"] == job_id_2
    # It could be 'pending' or 'completed' if the task was very fast.
    if pending_results_data["status"] == "pending":
        assert pending_results_data["results"] is None
        assert pending_results_data["equity_curve"] is None
        assert pending_results_data["trade_log"] is None
        assert "still processing" in pending_results_data["message"].lower()
    elif pending_results_data["status"] == "running": # It could also be running
        assert pending_results_data["results"] is None
        assert pending_results_data["equity_curve"] is None
        assert pending_results_data["trade_log"] is None
        assert "still processing" in pending_results_data["message"].lower()
    elif pending_results_data["status"] == "completed":
        # This is also acceptable if the task finished instantly.
        assert pending_results_data["results"] is not None
    else:
        pytest.fail(f"Unexpected status for job_id_2: {pending_results_data['status']}")


# To test a "failed" job scenario properly, we would need to:
# 1. Introduce a way to make a job fail predictably (e.g., specific input, or mock a failure).
# 2. Submit such a job.
# 3. Poll status until "failed".
# 4. Check /api/backtest/results/{job_id} for the failed status and error message.
# This is more advanced and might be part of a dedicated integration test for failures.
# For now, this set of tests covers the primary success paths and non-existent job IDs.


def test_run_backtest_and_fail_missing_data_file(client: TestClient, monkeypatch):
    # 1. Setup: Intentionally use settings that will cause a failure
    # We'll achieve this by making the data_loader fail.
    # We can mock data_loader.load_csv_data to raise FileNotFoundError.

    original_data_loader_path = 'main.data_loader.load_csv_data' # Path to data_loader in main.py context

    def mock_load_csv_data_fails(file_path):
        raise FileNotFoundError(f"Mocked error: File not found at {file_path}")

    monkeypatch.setattr(original_data_loader_path, mock_load_csv_data_fails)

    # 2. Submit a job that will now fail due to the mocked data loading error
    run_response = client.post("/api/backtest/run", json=VALID_BACKTEST_SETTINGS)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id = run_response.json()["job_id"]

    # 3. Poll for "failed" status
    max_wait_time = 10  # seconds
    poll_interval = 0.5 # seconds
    start_time = time.time()
    job_failed = False

    while time.time() - start_time < max_wait_time:
        status_response = client.get(f"/api/backtest/status/{job_id}")
        assert status_response.status_code == status.HTTP_200_OK # Status endpoint should still work
        status_data = status_response.json()
        if status_data["status"] == "failed":
            job_failed = True
            assert "Mocked error: File not found" in status_data.get("message", "")
            break
        # It should not complete successfully
        assert status_data["status"] != "completed", "Job unexpectedly completed when failure was expected."
        time.sleep(poll_interval)

    assert job_failed, f"Job {job_id} did not fail within {max_wait_time} seconds as expected."

    # 4. Check results endpoint for the failed job
    results_response = client.get(f"/api/backtest/results/{job_id}")
    assert results_response.status_code == status.HTTP_200_OK # Results endpoint should also work
    results_data = results_response.json()

    assert results_data["job_id"] == job_id
    assert results_data["status"] == "failed"
    assert "Mocked error: File not found" in results_data.get("message", "")
    assert results_data["results"] is None
    assert results_data["equity_curve"] is None
    assert results_data["trade_log"] is None
