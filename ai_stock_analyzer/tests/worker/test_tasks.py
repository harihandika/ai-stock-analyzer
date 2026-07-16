import pytest
from unittest.mock import patch, MagicMock
from app.worker.tasks import task_sync_and_analyze, task_daily_batch_analysis

@patch("app.worker.tasks.asyncio.get_event_loop")
@patch("app.worker.tasks._async_sync_and_analyze")
def test_task_sync_and_analyze(mock_async_func, mock_get_loop):
    # Mock loop and its method
    mock_loop = MagicMock()
    mock_get_loop.return_value = mock_loop
    mock_loop.is_closed.return_value = False
    mock_loop.run_until_complete.return_value = {"status": "success"}
    
    res = task_sync_and_analyze("BBCA.JK")
    
    assert res["status"] == "success"
    mock_loop.run_until_complete.assert_called_once()

@patch("app.worker.tasks.asyncio.get_event_loop")
@patch("app.worker.tasks._async_daily_batch")
def test_task_daily_batch_analysis(mock_async_func, mock_get_loop):
    mock_loop = MagicMock()
    mock_get_loop.return_value = mock_loop
    mock_loop.is_closed.return_value = False
    mock_loop.run_until_complete.return_value = {"message": "Triggered 2 tasks"}
    
    res = task_daily_batch_analysis()
    
    assert "Triggered" in res["message"]
    mock_loop.run_until_complete.assert_called_once()
