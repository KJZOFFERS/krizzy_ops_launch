from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading


@dataclass
class EngineState:
    """Tracks state of a single engine"""

    name: str
    running: bool = False
    last_run: Optional[datetime] = None
    interval_seconds: int = 60
    consecutive_errors: int = 0
    total_runs: int = 0
    total_errors: int = 0
    last_error: Optional[str] = None


@dataclass
class SystemState:
    """Global system state for dynamic orchestration"""

    # Engine states
    engines: Dict[str, EngineState] = field(default_factory=dict)

    # System metrics
    inbound_velocity_last_hour: int = 0
    buyer_response_rate_24h: float = 0.0
    outbound_deliverability_score: float = 1.0
    govcon_deadlines_approaching: int = 0

    # ZIP intelligence
    hot_zips: list = field(default_factory=list)
    cold_zips: list = field(default_factory=list)

    # Thread safety
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update_engine_state(self, name: str, **kwargs):
        """Thread-safe update of engine state"""
        with self.lock:
            if name not in self.engines:
                self.engines[name] = EngineState(name=name)

            engine = self.engines[name]
            for key, value in kwargs.items():
                if hasattr(engine, key):
                    setattr(engine, key, value)

    def get_engine_interval(self, name: str) -> int:
        """Get current interval for engine"""
        with self.lock:
            if name in self.engines:
                return self.engines[name].interval_seconds
            return 60  # Default

    def record_engine_run(self, name: str, success: bool, error: Optional[str] = None):
        """Record engine execution"""
        with self.lock:
            if name not in self.engines:
                self.engines[name] = EngineState(name=name)

            engine = self.engines[name]
            engine.last_run = datetime.utcnow()
            engine.total_runs += 1

            if success:
                engine.consecutive_errors = 0
            else:
                engine.consecutive_errors += 1
                engine.total_errors += 1
                engine.last_error = error

    def get_status(self) -> Dict[str, Any]:
        """Get system status snapshot"""
        with self.lock:
            return {
                "engines": {
                    name: {
                        "running": e.running,
                        "interval": e.interval_seconds,
                        "total_runs": e.total_runs,
                        "total_errors": e.total_errors,
                        "consecutive_errors": e.consecutive_errors,
                        "last_run": e.last_run.isoformat() if e.last_run else None,
                    }
                    for name, e in self.engines.items()
                },
                "metrics": {
                    "inbound_velocity_last_hour": self.inbound_velocity_last_hour,
                    "buyer_response_rate_24h": self.buyer_response_rate_24h,
                    "outbound_deliverability_score": self.outbound_deliverability_score,
                    "govcon_deadlines_approaching": self.govcon_deadlines_approaching,
                },
                "market_intel": {
                    "hot_zips": self.hot_zips,
                    "cold_zips": self.cold_zips,
                },
            }


# Global system state instance
system_state = SystemState()
