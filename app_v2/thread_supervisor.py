import threading
import time
from typing import Dict, Callable
from app_v2 import config
from app_v2.models.system_state import system_state
from app_v2.utils.logger import get_logger
from app_v2.utils.discord_client import post_system_alert

logger = get_logger(__name__)


class ThreadSupervisor:
    """
    Monitors engine threads and restarts them if they crash.
    Self-healing system component.
    """

    def __init__(self):
        self.threads: Dict[str, threading.Thread] = {}
        self.engine_functions: Dict[str, Callable] = {}
        self.logger = get_logger(self.__class__.__name__)

    def register_engine(self, name: str, func: Callable):
        """Register an engine function to be supervised"""
        self.engine_functions[name] = func
        self.logger.info(f"Registered engine: {name}")

    def start_engine(self, name: str):
        """Start an engine thread"""
        if name not in self.engine_functions:
            self.logger.error(f"Engine {name} not registered")
            return

        func = self.engine_functions[name]
        thread = threading.Thread(
            target=self._wrapped_engine,
            args=(name, func),
            daemon=True,
            name=f"Engine-{name}"
        )
        thread.start()
        self.threads[name] = thread

        system_state.update_engine_state(name, running=True)
        self.logger.info(f"Started engine: {name}")

    def _wrapped_engine(self, name: str, func: Callable):
        """Wrapper that catches errors and updates state"""
        while True:
            try:
                func()  # Run engine loop
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                self.logger.error(f"Engine {name} crashed: {error_msg}", exc_info=True)

                system_state.record_engine_run(name, success=False, error=error_msg)

                # Check if too many consecutive errors
                engine_state = system_state.engines.get(name)
                if engine_state and engine_state.consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
                    alert_msg = (
                        f"Engine {name} has failed {engine_state.consecutive_errors} times. "
                        f"Last error: {error_msg}"
                    )
                    post_system_alert("ENGINE_CRITICAL_FAILURE", alert_msg)
                    self.logger.critical(alert_msg)

                # Wait before restarting
                time.sleep(config.THREAD_RESTART_DELAY)

    def start_all_engines(self):
        """Start all registered engines"""
        for name in self.engine_functions:
            self.start_engine(name)

    def health_check(self):
        """Check health of all engine threads"""
        for name, thread in self.threads.items():
            if not thread.is_alive():
                self.logger.warning(f"Engine {name} thread died, restarting")
                post_system_alert("THREAD_RESTART", f"Engine {name} restarted")
                system_state.update_engine_state(name, running=False)
                self.start_engine(name)

    def run_health_check_loop(self):
        """Run periodic health checks"""
        self.logger.info("Thread supervisor health check started")

        while True:
            try:
                self.health_check()
                time.sleep(config.HEARTBEAT_INTERVAL)
            except Exception as e:
                self.logger.error(f"Health check error: {e}", exc_info=True)
                time.sleep(config.HEARTBEAT_INTERVAL)

    def start_supervisor(self):
        """Start the supervisor thread"""
        thread = threading.Thread(
            target=self.run_health_check_loop,
            daemon=True,
            name="ThreadSupervisor"
        )
        thread.start()
        self.logger.info("Thread supervisor started")


# Global supervisor instance
supervisor = ThreadSupervisor()
