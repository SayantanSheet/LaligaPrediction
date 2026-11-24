"""Holds the live model. Loads the persisted artifact at startup (fast) and only trains when the
artifact is missing or was built from different data. Retraining happens in a background thread
and the new model is swapped in atomically, so requests are never blocked."""
from __future__ import annotations

import logging
import threading

from ..services.data_store import get_store
from .ensemble import EnsembleModel
from .train import MODEL_PATH, train_and_save

log = logging.getLogger("registry")


class ModelRegistry:
    def __init__(self):
        self.model: EnsembleModel | None = None
        self.status = "loading"
        self.error: str | None = None
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self.model is not None

    def load_or_train(self) -> None:
        store = get_store()
        try:
            if MODEL_PATH.exists():
                import joblib
                model = joblib.load(MODEL_PATH)
                if getattr(model, "data_version", None) == store.version:
                    self.model, self.status = model, "ready"
                    log.info("Loaded model artifact (%s)", model.data_version)
                    return
                log.info("Model artifact is stale (%s != %s); retraining", model.data_version, store.version)
                self.model = model  # serve the stale model while retraining
            self.retrain_async()
        except Exception as exc:  # corrupted artifact, version mismatch...
            log.exception("Could not load model artifact")
            self.error = str(exc)
            self.retrain_async()

    def retrain_async(self) -> bool:
        if not self._lock.acquire(blocking=False):
            return False  # already training
        self.status = "training"

        def run():
            try:
                model = train_and_save(get_store())
                self.model, self.status, self.error = model, "ready", None
            except Exception as exc:
                log.exception("Training failed")
                self.status, self.error = "error", str(exc)
            finally:
                self._lock.release()

        threading.Thread(target=run, daemon=True, name="trainer").start()
        return True


registry = ModelRegistry()
