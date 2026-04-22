"""Managed background execution for workflow runs."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from market_mapper.services.workflow_service import WorkflowService

logger = logging.getLogger("market_mapper.run_jobs")


class RunJobManager:
    """Own a small in-process worker pool for workflow execution."""

    def __init__(self, *, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="market-mapper-runner",
        )
        self._futures: dict[str, Future] = {}
        self._lock = Lock()

    def submit(self, run_id: str) -> None:
        """Submit a workflow run if it is not already active."""

        with self._lock:
            existing = self._futures.get(run_id)
            if existing and not existing.done():
                logger.info("Run %s is already active; skipping duplicate submit.", run_id)
                return
            logger.info("Submitting workflow run %s to managed executor.", run_id)
            future = self._executor.submit(self._execute_run, run_id)
            self._futures[run_id] = future
            future.add_done_callback(lambda completed, rid=run_id: self._finalize(rid, completed))

    def _execute_run(self, run_id: str) -> None:
        logger.info("Worker picked up workflow run %s.", run_id)
        service = WorkflowService()
        service.execute_run(run_id)

    def _finalize(self, run_id: str, future: Future) -> None:
        try:
            future.result()
            logger.info("Workflow run %s completed successfully.", run_id)
        except Exception:
            logger.exception("Workflow run %s failed inside managed executor.", run_id)
        finally:
            with self._lock:
                self._futures.pop(run_id, None)

    def shutdown(self) -> None:
        """Shut down the worker pool."""

        self._executor.shutdown(wait=False, cancel_futures=False)


_RUN_JOB_MANAGER = RunJobManager()


def get_run_job_manager() -> RunJobManager:
    """Return the process-wide workflow job manager."""

    return _RUN_JOB_MANAGER
