"""Tests for kpi module"""

import pytest
from unittest.mock import Mock, patch
from kpi import kpi_push, track_cycle_start, track_cycle_end, track_error, track_boot


class TestKPI:
    """Test cases for KPI tracking"""
    
    @patch('kpi.safe_airtable_write')
    def test_kpi_push_success(self, mock_safe_write):
        """Test successful KPI push"""
        # Setup
        mock_safe_write.return_value = {"id": "kpi_id"}
        
        # Test
        kpi_push("test_event", {"count": 5, "status": "success"})
        
        # Assertions
        mock_safe_write.assert_called_once()
        call_args = mock_safe_write.call_args
        assert call_args[0][0] == "KPI_Log"
        assert call_args[0][1]["Event"] == "test_event"
        assert "count" in call_args[0][1]["Data"]
        assert "status" in call_args[0][1]["Data"]
        assert "timestamp" in call_args[0][1]
        assert call_args[0][1]["Status"] == "success"
        assert call_args[0][1]["Environment"] == "production"
        assert call_args[0][1]["Version"] == "3.0.0"
    
    @patch('kpi.safe_airtable_write')
    def test_kpi_push_with_timestamp(self, mock_safe_write):
        """Test KPI push with existing timestamp"""
        # Setup
        mock_safe_write.return_value = {"id": "kpi_id"}
        test_data = {
            "count": 5,
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        # Test
        kpi_push("test_event", test_data)
        
        # Assertions
        call_args = mock_safe_write.call_args
        assert call_args[0][1]["Timestamp"] == "2024-01-01T12:00:00Z"
    
    @patch('kpi.safe_airtable_write')
    def test_kpi_push_failure_handling(self, mock_safe_write):
        """Test KPI push failure handling"""
        # Setup
        mock_safe_write.side_effect = Exception("Airtable error")
        
        # Test - should not raise exception
        kpi_push("test_event", {"count": 5})
        
        # Assertions
        mock_safe_write.assert_called_once()
    
    @patch('kpi.kpi_push')
    def test_track_cycle_start(self, mock_kpi_push):
        """Test cycle start tracking"""
        # Test
        track_cycle_start("REI")
        
        # Assertions
        mock_kpi_push.assert_called_once_with("cycle_start", {
            "engine": "REI",
            "count": 0,
            "status": "started"
        })
    
    @patch('kpi.kpi_push')
    def test_track_cycle_end_success(self, mock_kpi_push):
        """Test cycle end tracking with success"""
        # Test
        track_cycle_end("REI", 5, success=True)
        
        # Assertions
        mock_kpi_push.assert_called_once_with("cycle_end", {
            "engine": "REI",
            "count": 5,
            "status": "completed",
            "success": True
        })
    
    @patch('kpi.kpi_push')
    def test_track_cycle_end_failure(self, mock_kpi_push):
        """Test cycle end tracking with failure"""
        # Test
        track_cycle_end("REI", 0, success=False)
        
        # Assertions
        mock_kpi_push.assert_called_once_with("cycle_end", {
            "engine": "REI",
            "count": 0,
            "status": "failed",
            "success": False
        })
    
    @patch('kpi.kpi_push')
    def test_track_error_basic(self, mock_kpi_push):
        """Test error tracking with basic error"""
        # Test
        track_error("REI", "API Error")
        
        # Assertions
        mock_kpi_push.assert_called_once_with("error", {
            "engine": "REI",
            "error": "API Error",
            "count": 0,
            "status": "error"
        })
    
    @patch('kpi.kpi_push')
    def test_track_error_with_context(self, mock_kpi_push):
        """Test error tracking with context"""
        # Test
        context = {"url": "https://api.example.com", "status_code": 500}
        track_error("REI", "API Error", context)
        
        # Assertions
        expected_data = {
            "engine": "REI",
            "error": "API Error",
            "count": 0,
            "status": "error",
            "url": "https://api.example.com",
            "status_code": 500
        }
        mock_kpi_push.assert_called_once_with("error", expected_data)
    
    @patch('kpi.kpi_push')
    def test_track_boot(self, mock_kpi_push):
        """Test boot tracking"""
        # Test
        track_boot()
        
        # Assertions
        mock_kpi_push.assert_called_once_with("boot", {
            "count": 0,
            "status": "started",
            "components": ["main", "health", "watchdog", "rei_engine", "govcon_engine"]
        })