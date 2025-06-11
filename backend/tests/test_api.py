import pytest
from fastapi.testclient import TestClient
from fastapi import status # For status codes
import time # To allow background tasks to process
import uuid # To generate non-existent job_ids for testing
import os # For file system operations in tests
import asyncio # For WebSocket tests and simulated task timing
from datetime import datetime # For checking date formats

from starlette.websockets import WebSocketDisconnect # For WebSocket tests
from unittest.mock import patch, MagicMock
import pandas as pd

# Assuming 'client' fixture is available from conftest.py
import backend.main # Required for monkeypatching elements within the main module
from backend.main import run_backtest_task, job_store, DATA_DIR, BacktestSettings

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
    "max_units_per_market": {"EUR/USD": 500000},
    "data_file_name": "sample.csv" # Added data_file_name for default successful runs
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
    max_wait_time = 35  # seconds
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
    max_wait_time = 20  # seconds
    poll_interval = 0.5 # seconds
    start_time = time.time()
    job_failed = False

    while time.time() - start_time < max_wait_time:
        status_response = client.get(f"/api/backtest/status/{job_id}")
        assert status_response.status_code == status.HTTP_200_OK # Status endpoint should still work
        status_data = status_response.json()
        if status_data["status"] == "failed":
            job_failed = True
            # Updated assertion to match actual error message format
            assert f"Data file {VALID_BACKTEST_SETTINGS['data_file_name']} not found" in status_data.get("message", "")
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
    # Updated assertion to match actual error message format
    assert f"Data file {VALID_BACKTEST_SETTINGS['data_file_name']} not found" in results_data.get("message", "")
    assert results_data["results"] is None
    assert results_data["equity_curve"] is None
    assert results_data["trade_log"] is None


# --- Tests for Data Collection API Endpoints ---

VALID_DATA_COLLECTION_REQUEST = {
    "symbol": "USDJPY",
    "startYear": 2023,
    "startMonth": 1,
    "endYear": 2023,
    "endMonth": 12,
    "apiKey": "test_key_optional"
}

# Path to the data directory from the perspective of this test file
# backend/tests/test_api.py -> project_root/data/
DATA_DIR_TEST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))


def test_collect_data_success(client: TestClient):
    response = client.post("/api/data/collect", json=VALID_DATA_COLLECTION_REQUEST)
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)

def test_collect_data_invalid_input(client: TestClient):
    invalid_payload = VALID_DATA_COLLECTION_REQUEST.copy()
    del invalid_payload["symbol"] # Make it invalid
    response = client.post("/api/data/collect", json=invalid_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_data_collection_job_status_flow(client: TestClient):
    # 1. Submit a data collection job
    run_response = client.post("/api/data/collect", json=VALID_DATA_COLLECTION_REQUEST)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id = run_response.json()["job_id"]

    # 2. Poll for completion (simulated task takes ~5 seconds)
    max_wait_time = 20  # seconds, allowing some buffer
    poll_interval = 0.5 # seconds
    start_time = time.time()
    job_completed_successfully = False
    last_status = None

    while time.time() - start_time < max_wait_time:
        # Assuming /api/backtest/status/{job_id} can fetch status for data_collection jobs too
        status_response = client.get(f"/api/backtest/status/{job_id}")
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        last_status = status_data["status"]

        job_details = client.get(f"/api/backtest/status/{job_id}").json() # A bit redundant, ideally status includes type
        # To check type, we'd ideally have it in the status response.
        # For now, we are inferring based on the happy path of this test.

        if last_status == "completed":
            message = status_data.get("message", "")
            assert message == "Data collection finished." or \
                   message.startswith("Successfully fetched full timeseries") or \
                   message.startswith("MOCK: Successfully fetched full timeseries") or \
                   message.startswith("Data collection and filtering successful.") or \
                   message.startswith("MOCK: Data collection and filtering successful.")
            # Check job type by inspecting job_store directly (test-only, not ideal)
            # Or assume if it completed with the right message, it was a data collection job
            job_completed_successfully = True
            break
        if last_status == "failed":
            pytest.fail(f"Data collection job {job_id} failed during test: {status_data.get('message', 'No error message')}")

        assert last_status in ["pending", "running"], f"Unexpected status: {last_status}"
        time.sleep(poll_interval)

    assert job_completed_successfully, f"Job {job_id} did not complete successfully. Last status: {last_status}"

    # Verify job type if possible (this is a conceptual check, actual job_store access from test is tricky)
    # For now, successful completion of *this* test flow implies it was handled as a data collection job.
    # A better way would be if the status endpoint itself returned the 'type' of the job.

def test_list_data_files_success(client: TestClient):
    # Ensure 'data/sample.csv' exists (created in a previous step or by app logic)
    # For this test, we assume it's there.
    expected_file_name = "sample.csv" # This was the file created in the previous subtask

    # Create the file if it doesn't exist to make test robust
    sample_file_path = os.path.join(DATA_DIR_TEST, expected_file_name)
    if not os.path.exists(DATA_DIR_TEST):
        os.makedirs(DATA_DIR_TEST)
    if not os.path.exists(sample_file_path):
        with open(sample_file_path, "w") as f:
            f.write("col1,col2\nval1,val2\n")

    response = client.get("/api/data/files")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "files" in data
    assert "total_files" in data
    assert isinstance(data["files"], list)
    assert isinstance(data["total_files"], int)

    if data["total_files"] > 0:
        assert any(f["name"] == expected_file_name for f in data["files"]), f"{expected_file_name} not found in response"
        file_info = next((f for f in data["files"] if f["name"] == expected_file_name), None)
        assert file_info is not None
        assert isinstance(file_info["size"], int)
        assert file_info["size"] > 0 # sample.csv has content
        # Validate datetime format
        try:
            datetime.fromisoformat(file_info["created_at"].replace("Z", "+00:00")) # Handle Z for UTC
        except ValueError:
            pytest.fail(f"created_at for {expected_file_name} is not a valid ISO datetime string: {file_info['created_at']}")
    else:
        pytest.fail(f"No files listed, {expected_file_name} was expected.")


def test_list_data_files_empty_directory(client: TestClient, monkeypatch):
    # Mock os.listdir as used in backend.main to return an empty list for DATA_DIR
    def mock_listdir_empty(path):
        if path == backend.main.DATA_DIR: # Compare with DATA_DIR in main.py
            return []
        return os.listdir(path) # Fallback to actual os.listdir for other paths

    monkeypatch.setattr(backend.main.os, "listdir", mock_listdir_empty)

    response = client.get("/api/data/files")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["files"] == []
    assert data["total_files"] == 0

def test_list_data_files_directory_not_found(client: TestClient, monkeypatch):
    # Mock os.path.exists as used in backend.main to return False for DATA_DIR
    original_os_path_exists = os.path.exists
    def mock_path_exists_false_for_data_dir(path):
        if path == backend.main.DATA_DIR:
            return False
        return original_os_path_exists(path) # Fallback for other paths

    monkeypatch.setattr(backend.main.os.path, "exists", mock_path_exists_false_for_data_dir)

    response = client.get("/api/data/files")
    # As per implementation, it should return 200 OK with empty list
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["files"] == []
    assert data["total_files"] == 0


# --- WebSocket Tests for /api/data/stream_log ---

def test_stream_log_success(client: TestClient):
    # 1. Create a data collection job
    run_response = client.post("/api/data/collect", json=VALID_DATA_COLLECTION_REQUEST)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id = run_response.json()["job_id"]

    # Give a moment for the job to be initialized in job_store
    time.sleep(0.2)

    log_lines_received = 0
    completion_message_received = False # For "INFO: Job ... completed"
    final_status_message_received = False # For "Log streaming ended..."

    with client.websocket_connect(f"/api/data/stream_log/{job_id}") as websocket:
        initial_data = websocket.receive_text()
        # Message from backend/main.py: Streaming logs for data collection job {job_id}...
        assert f"Streaming logs for data collection job {job_id}" in initial_data

        max_test_duration = time.time() + 25  # Increased test timeout (job is ~5s)
        while time.time() < max_test_duration:
            try:
                data = websocket.receive_text() # No timeout argument

                if data.startswith("LOG:"): # Check for actual log prefix
                    log_lines_received += 1

                # Check for job completion message relayed by the WebSocket endpoint
                if f"INFO: Job {job_id} completed" in data:
                    completion_message_received = True

                # Check for the stream ending message from the WebSocket endpoint itself
                if "STREAM_END: Job completed." in data: # Check for actual server message
                    final_status_message_received = True
                    # This is the definitive end of the stream from the server's perspective
                    break

                if f"ERROR: Job {job_id} failed" in data:
                    pytest.fail(f"Log stream indicated job {job_id} failed.")

            except WebSocketDisconnect:
                # Server closed connection. This might be expected if it's after all messages.
                # If final_status_message_received is True, this is okay.
                if not final_status_message_received:
                    # If disconnected before final message, check if job actually finished quickly
                    status_resp = client.get(f"/api/data/status/{job_id}").json()
                    if status_resp["status"] == "completed":
                        final_status_message_received = True # Assume it finished and closed stream
                        completion_message_received = True
                break
            except Exception as e:
                pytest.fail(f"Unexpected error during WebSocket communication: {e}")
                break

    assert log_lines_received > 0, "Did not receive any simulated log lines."
    # completion_message_received can be True if the "INFO: Job ... completed" message is caught.
    # The run_datacollection_task sets "Data collection finished." in job_store.
    # The stream_log endpoint sends "INFO: Job {job_id} completed. {message}"
    # So, if the job completes while stream_log is polling, this message will be sent.
    assert completion_message_received or final_status_message_received, \
        "Did not receive job completion message or final stream ended message via WebSocket."
    assert final_status_message_received, "Did not receive the final 'Log streaming ended' message."


def test_stream_log_invalid_job_id(client: TestClient):
    non_existent_job_id = str(uuid.uuid4())
    # Expect WebSocketDisconnect to be raised by the context manager or subsequent calls
    # if server closes connection, which it should.
    with client.websocket_connect(f"/api/data/stream_log/{non_existent_job_id}") as websocket:
        error_message = websocket.receive_text()
        # Message from backend/main.py: ERROR: Job ID {job_id} not found or is not a data collection job.
        assert f"ERROR: Job ID {non_existent_job_id} not found or is not a data collection job." in error_message

        # Expect the server to close the connection after sending the error
        with pytest.raises(WebSocketDisconnect) as excinfo:
            websocket.receive_text() # This should fail as connection is closed
        assert excinfo.value.code == 1008


# --- Tests for run_backtest_task data file loading ---

def get_default_backtest_settings_dict() -> dict:
    """Helper to get a default, valid settings dictionary."""
    return {
        "initial_capital": 100000.0,
        "markets": ["TEST_MARKET"],
        "entry_donchian_period": 20,
        "take_profit_long_exit_period": 10,
        "take_profit_short_exit_period": 10,
        "atr_period": 14,
        "stop_loss_atr_multiplier": 3.0,
        "risk_per_trade": 0.01,
        "total_portfolio_risk_limit": 0.1,
        "slippage_pips": 0.2,
        "commission_per_lot": 5.0,
        "pip_point_value": {"TEST_MARKET": 0.0001},
        "lot_size": {"TEST_MARKET": 100000},
        "max_units_per_market": {"TEST_MARKET": 10},
        "data_file_name": None, # Default to None, specific tests will set this
    }

@patch('backend.main.performance_analyzer.calculate_all_kpis')
@patch('backend.main.trading_logic.run_strategy')
@patch('backend.main.data_loader.load_csv_data')
def test_run_backtest_task_uses_data_file_name(
    mock_load_csv_data: MagicMock,
    mock_run_strategy: MagicMock,
    mock_calculate_kpis: MagicMock
):
    job_id = f"test_job_{uuid.uuid4()}"
    settings = get_default_backtest_settings_dict()
    test_filename = "test_data.csv"
    settings["data_file_name"] = test_filename

    # Initialize job_store for this job
    job_store[job_id] = {"status": "pending", "parameters": settings}

    # Configure mocks
    # Create a mock DataFrame that is not empty and has a DatetimeIndex
    mock_df = pd.DataFrame({'Open': [1, 2], 'High': [1, 2], 'Low': [1, 2], 'Close': [1, 2]},
                           index=pd.to_datetime(['2023-01-01', '2023-01-02']))
    mock_load_csv_data.return_value = mock_df
    mock_run_strategy.return_value = {"equity_curve": [], "trade_log": [], "some_other_metric": 1}
    mock_calculate_kpis.return_value = {"Sharpe Ratio": 1.5}

    try:
        run_backtest_task(job_id, settings)
        expected_path = os.path.join(DATA_DIR, test_filename)
        mock_load_csv_data.assert_called_once_with(expected_path)
        assert job_store[job_id]["status"] == "completed", \
            f"Job status was {job_store[job_id]['status']}, message: {job_store[job_id].get('message')}"
        assert job_store[job_id].get("error_message") is None
    finally:
        job_store.pop(job_id, None) # Cleanup

@patch('backend.main.data_loader.load_csv_data')
def test_run_backtest_task_fails_no_data_file_name(mock_load_csv_data: MagicMock):
    job_id = f"test_job_{uuid.uuid4()}"
    settings = get_default_backtest_settings_dict()
    settings["data_file_name"] = None # Explicitly None

    job_store[job_id] = {"status": "pending", "parameters": settings}

    try:
        run_backtest_task(job_id, settings)
        assert job_store[job_id]["status"] == "failed"
        assert "No data file name provided" in job_store[job_id].get("message", "")
        mock_load_csv_data.assert_not_called()
    finally:
        job_store.pop(job_id, None)

    # Test with empty string for data_file_name
    job_id_empty_str = f"test_job_{uuid.uuid4()}"
    settings_empty_str = get_default_backtest_settings_dict()
    settings_empty_str["data_file_name"] = ""
    job_store[job_id_empty_str] = {"status": "pending", "parameters": settings_empty_str}
    mock_load_csv_data.reset_mock() # Reset call count from previous assert

    try:
        run_backtest_task(job_id_empty_str, settings_empty_str)
        assert job_store[job_id_empty_str]["status"] == "failed"
        assert "No data file name provided" in job_store[job_id_empty_str].get("message", "")
        mock_load_csv_data.assert_not_called()
    finally:
        job_store.pop(job_id_empty_str, None)


@patch('backend.main.data_loader.load_csv_data')
def test_run_backtest_task_fails_file_not_found(mock_load_csv_data: MagicMock):
    job_id = f"test_job_{uuid.uuid4()}"
    settings = get_default_backtest_settings_dict()
    non_existent_file = "non_existent_file.csv"
    settings["data_file_name"] = non_existent_file

    job_store[job_id] = {"status": "pending", "parameters": settings}
    mock_load_csv_data.side_effect = FileNotFoundError(f"File {non_existent_file} not found")

    try:
        run_backtest_task(job_id, settings)
        assert job_store[job_id]["status"] == "failed"
        error_msg = job_store[job_id].get("message", "")
        assert non_existent_file in error_msg
        # Message in main.py for FileNotFoundError is specific: f"Data file {data_file_name} not found."
        assert "not found" in error_msg
        assert "is invalid" not in error_msg # Check it's the more specific message

        expected_path = os.path.join(DATA_DIR, non_existent_file)
        mock_load_csv_data.assert_called_once_with(expected_path)
    finally:
        job_store.pop(job_id, None)

@patch('backend.main.data_loader.load_csv_data')
def test_run_backtest_task_fails_invalid_data_file(mock_load_csv_data: MagicMock):
    job_id = f"test_job_{uuid.uuid4()}"
    settings = get_default_backtest_settings_dict()
    invalid_file = "invalid_file.csv"
    settings["data_file_name"] = invalid_file

    job_store[job_id] = {"status": "pending", "parameters": settings}
    # Simulate an error other than FileNotFoundError, e.g., pd.errors.EmptyDataError
    # This error is raised by data_loader.load_csv_data if the CSV is empty or malformed.
    simulated_error_message = "No columns to parse from file"
    mock_load_csv_data.side_effect = pd.errors.EmptyDataError(simulated_error_message)


    try:
        run_backtest_task(job_id, settings)
        assert job_store[job_id]["status"] == "failed"
        error_msg = job_store[job_id].get("message", "")
        assert invalid_file in error_msg
        # Message in main.py for other exceptions is: f"Data file {data_file_name} not found or is invalid: {str(e)}"
        assert "not found or is invalid" in error_msg
        assert simulated_error_message in error_msg # Specific exception text

        expected_path = os.path.join(DATA_DIR, invalid_file)
        mock_load_csv_data.assert_called_once_with(expected_path)
    finally:
        job_store.pop(job_id, None)


def test_stream_log_job_not_data_collection(client: TestClient):
    # 1. Create a backtest job (which is not 'data_collection' type)
    # This test might require VALID_BACKTEST_SETTINGS to be temporarily modified
    # if it relies on a job that is NOT a data collection job and also needs to pass
    # the data_file_name validation.
    # For now, assuming VALID_BACKTEST_SETTINGS having a data_file_name is fine here.
    # If this test were to fail due to data_file_name logic, it would need specific handling.
    current_valid_settings_for_test = VALID_BACKTEST_SETTINGS.copy()
    # If this test specifically needs to test behavior for a job type mismatch
    # and the presence of data_file_name causes issues, adjust as needed.
    # For example, if it should fail earlier due to being a backtest job type.

    run_response = client.post("/api/backtest/run", json=current_valid_settings_for_test)
    assert run_response.status_code == status.HTTP_202_ACCEPTED
    job_id_backtest = run_response.json()["job_id"]

    time.sleep(0.1) # Ensure job is in job_store

    with client.websocket_connect(f"/api/data/stream_log/{job_id_backtest}") as websocket:
        error_message = websocket.receive_text()
        # Message from backend/main.py: ERROR: Job ID {job_id} not found or is not a data collection job.
        assert f"ERROR: Job ID {job_id_backtest} not found or is not a data collection job." in error_message

        with pytest.raises(WebSocketDisconnect) as excinfo:
            websocket.receive_text()
        assert excinfo.value.code == 1008
