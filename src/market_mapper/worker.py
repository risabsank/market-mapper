"""Subprocess worker entrypoint for workflow runs."""

from __future__ import annotations

import logging
import sys

from market_mapper.services.workflow_service import WorkflowService

logger = logging.getLogger("market_mapper.worker")


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print("Usage: python -m market_mapper.worker RUN_ID", file=sys.stderr)
        return 2
    run_id = args[0]
    logger.info("Worker process executing run %s.", run_id)
    WorkflowService().execute_run(run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
