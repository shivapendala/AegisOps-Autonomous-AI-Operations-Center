"""
Standalone Monitoring Agent Daemon.
Collects telemetry at regular intervals and can push to AegisOps Backend API or console.
"""

import asyncio
import logging
import sys
from monitoring.collector import SystemCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegisops.monitoring.agent")


async def run_agent(interval_seconds: float = 3.0, iterations: int = 0):
    """
    Runs the collector loop.
    If iterations == 0, runs indefinitely.
    """
    collector = SystemCollector()
    logger.info("Starting AegisOps Monitoring Agent probe on host '%s'...", collector.host_name)
    count = 0

    try:
        while True:
            snapshot = collector.collect()
            logger.info(
                "Telemetry: CPU=%5.1f%% | RAM=%5.1f%% | Disk=%5.1f%% | Procs=%d",
                snapshot.cpu_percent,
                snapshot.memory_percent,
                snapshot.disk_percent,
                snapshot.process_count,
            )
            count += 1
            if 0 < iterations <= count:
                break
            await asyncio.sleep(interval_seconds)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Monitoring agent halted.")


if __name__ == "__main__":
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    try:
        asyncio.run(run_agent(interval_seconds=interval))
    except KeyboardInterrupt:
        pass
