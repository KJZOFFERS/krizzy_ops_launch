import time
from typing import Dict
from app_v2 import config
from app_v2.models.system_state import system_state
from app_v2.utils.logger import get_logger

logger = get_logger(__name__)


class DynamicIntervalController:
    """
    Controls engine intervals dynamically based on system state.
    Adjusts intervals to optimize responsiveness vs resource usage.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def adjust_intervals(self):
        """
        Main loop that periodically adjusts engine intervals
        based on current system metrics
        """
        # Input engine: Speed up if high inbound velocity
        if system_state.inbound_velocity_last_hour > 10:
            self._set_interval("input", 30)  # Fast: every 30 sec
        elif system_state.inbound_velocity_last_hour > 5:
            self._set_interval("input", 60)  # Normal
        else:
            self._set_interval("input", 120)  # Slow

        # Underwriting engine: Follow input pace
        input_interval = system_state.get_engine_interval("input")
        self._set_interval("underwriting", input_interval * 2)

        # Buyer engine: Speed up for hot ZIPs
        if len(system_state.hot_zips) > 5:
            self._set_interval("buyer", 120)  # Fast
        else:
            self._set_interval("buyer", 300)  # Normal

        # Outbound control: Speed up if deliverability drops
        if system_state.outbound_deliverability_score < 0.9:
            self._set_interval("outbound_control", 60)  # Check more often
        else:
            self._set_interval("outbound_control", 300)  # Normal

        # GovCon: Speed up if deadlines approaching
        if system_state.govcon_deadlines_approaching > 3:
            self._set_interval("govcon", 600)  # Every 10 min
        else:
            self._set_interval("govcon", 1800)  # Every 30 min

        # Buyer performance and market intel: Keep stable
        self._set_interval("buyer_performance", 600)
        self._set_interval("market_intel", 900)

    def _set_interval(self, engine_name: str, seconds: int):
        """Set interval for engine, respecting bounds"""
        if engine_name not in config.INTERVAL_BOUNDS:
            return

        min_interval, max_interval = config.INTERVAL_BOUNDS[engine_name]
        clamped = max(min_interval, min(max_interval, seconds))

        system_state.update_engine_state(engine_name, interval_seconds=clamped)

    def run(self):
        """Run interval controller loop"""
        self.logger.info("Dynamic Interval Controller started")

        while True:
            try:
                self.adjust_intervals()
                time.sleep(60)  # Adjust every minute
            except Exception as e:
                self.logger.error(f"Interval controller error: {e}", exc_info=True)
                time.sleep(60)


def start_orchestrator():
    """Start the dynamic interval orchestrator in background"""
    import threading

    controller = DynamicIntervalController()
    thread = threading.Thread(target=controller.run, daemon=True, name="IntervalController")
    thread.start()
    logger.info("Loop orchestrator started")
