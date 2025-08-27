from collections import deque
from statistics import mean
from threading import RLock
from typing import Any, Deque, Dict

WINDOW = 100

class _ModelStats:
    def __init__(self, window: int = WINDOW):
        self.count: int = 0
        self.latencies_ms: Deque[float] = deque(maxlen=window)
        self.last_output: Any = None
        self.window: int = window

    @property
    def avg_ms(self) -> float:
        return float(mean(self.latencies_ms)) if self.latencies_ms else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "window": self.window,
            "last_output": self.last_output,
        }

class MetricsStore:
    def __init__(self, window: int = WINDOW):
        self._lock = RLock()
        self._models: Dict[str, _ModelStats] = {
            "player": _ModelStats(window),
            "crowd": _ModelStats(window),
        }
        self._window = window

    def record_inference(self, model: str, latency_ms: float, output: Any) -> None:
        if model not in self._models:
            # lazily create if new model appears
            self._models[model] = _ModelStats(self._window)
        with self._lock:
            m = self._models[model]
            m.count += 1
            m.latencies_ms.append(float(latency_ms))
            m.last_output = output

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "window": self._window,
                "models": {name: st.to_dict() for name, st in self._models.items()},
            }

metrics_store = MetricsStore()

def record_inference(model: str, latency_ms: float, output: Any) -> None:
    metrics_store.record_inference(model, latency_ms, output)

def snapshot() -> Dict[str, Any]:
    return metrics_store.snapshot()