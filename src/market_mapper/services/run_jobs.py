"""Managed background execution for workflow runs using subprocess workers."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from threading import Lock, Thread

logger = logging.getLogger("market_mapper.run_jobs")


class RunJobManager:
    """Own a small process launcher for workflow execution."""

    def __init__(self) -> None:
        self._processes: dict[str, subprocess.Popen] = {}
        self._lock = Lock()

    def submit(self, run_id: str) -> None:
        """Submit a workflow run if it is not already active."""

        with self._lock:
            existing = self._processes.get(run_id)
            if existing and existing.poll() is None:
                logger.info("Run %s is already active; skipping duplicate submit.", run_id)
                return
            logger.info("Submitting workflow run %s to subprocess worker.", run_id)
            process = subprocess.Popen(
                [sys.executable, "-m", "market_mapper.worker", run_id],
                stdout=sys.stdout,
                stderr=sys.stderr,
                start_new_session=True,
                cwd=str(Path(__file__).resolve().parents[3]),
            )
            self._processes[run_id] = process
            Thread(
                target=self._watch_process,
                args=(run_id, process),
                name=f"market-mapper-run-watch-{run_id[:8]}",
                daemon=True,
            ).start()

    def _watch_process(self, run_id: str, process: subprocess.Popen) -> None:
        return_code = process.wait()
        if return_code == 0:
            logger.info("Workflow run %s completed successfully in subprocess worker.", run_id)
        else:
            logger.error(
                "Workflow run %s exited from subprocess worker with code %s.",
                run_id,
                return_code,
            )
        with self._lock:
            current = self._processes.get(run_id)
            if current is process:
                self._processes.pop(run_id, None)

    def shutdown(self) -> None:
        """Shut down the active worker processes."""

        with self._lock:
            for run_id, process in list(self._processes.items()):
                if process.poll() is None:
                    logger.info("Terminating active workflow subprocess for run %s.", run_id)
                    process.terminate()
            self._processes.clear()


_RUN_JOB_MANAGER = RunJobManager()


def get_run_job_manager() -> RunJobManager:
    """Return the process-wide workflow job manager."""

    return _RUN_JOB_MANAGER
