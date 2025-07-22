"""Main entry point for the Voicemeeter MCP Server."""

import asyncio
import signal
import sys

from .server import main


class GracefulShutdown:
    """Handle graceful shutdown of async resources."""

    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.tasks: set = set()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def cleanup_tasks(self):
        """Cancel all pending tasks and wait for cleanup."""
        if not self.tasks:
            return

        print("Cancelling pending tasks...")
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete cancellation
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    def add_task(self, task: asyncio.Task):
        """Add a task to be managed."""
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


async def main_with_cleanup():
    """Main entry point with proper async cleanup."""
    shutdown_handler = GracefulShutdown()

    # Set up signal handlers for graceful shutdown
    if sys.platform != "win32":
        # Unix-like systems
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, shutdown_handler.signal_handler, sig, None)

    try:
        # Create the main server task
        server_task = asyncio.create_task(main())
        shutdown_handler.add_task(server_task)

        # Wait for either the server to complete or shutdown signal
        done, pending = await asyncio.wait(
            [server_task, asyncio.create_task(shutdown_handler.shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel any pending tasks
        for task in pending:
            task.cancel()

        # If shutdown was requested, clean up gracefully
        if shutdown_handler.shutdown_event.is_set():
            print("Performing graceful shutdown...")
            await shutdown_handler.cleanup_tasks()

    except Exception as e:
        print(f"Error during execution: {e}", file=sys.stderr)
        await shutdown_handler.cleanup_tasks()
        raise
    finally:
        # Final cleanup
        await shutdown_handler.cleanup_tasks()


def cli_main():
    """CLI entry point."""
    try:
        asyncio.run(main_with_cleanup())
    except KeyboardInterrupt:
        print("\nShutdown completed.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
