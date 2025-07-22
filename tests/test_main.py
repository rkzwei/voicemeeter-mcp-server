"""Tests for main entry point."""

import asyncio
import sys
from unittest.mock import Mock, patch

import pytest


class TestMain:
    """Test cases for main entry point."""

    @patch("voicemeeter_mcp_server.main.asyncio.run")
    def test_cli_main_success(self, mock_asyncio_run):
        """Test successful CLI main execution."""
        from voicemeeter_mcp_server.main import cli_main

        mock_asyncio_run.return_value = None

        cli_main()

        # Check that asyncio.run was called once
        mock_asyncio_run.assert_called_once()
        # Verify the argument passed to asyncio.run is a coroutine
        args, kwargs = mock_asyncio_run.call_args
        assert len(args) == 1
        # The argument should be a coroutine object
        coro = args[0]
        assert hasattr(coro, "__await__")
        # Clean up the coroutine to prevent warnings
        coro.close()

    @patch("voicemeeter_mcp_server.main.asyncio.run")
    @patch("voicemeeter_mcp_server.main.sys.exit")
    def test_cli_main_keyboard_interrupt(self, mock_exit, mock_asyncio_run):
        """Test CLI main with KeyboardInterrupt."""
        from voicemeeter_mcp_server.main import cli_main

        def side_effect_with_cleanup(coro):
            # Clean up the coroutine before raising the exception
            coro.close()
            raise KeyboardInterrupt()

        mock_asyncio_run.side_effect = side_effect_with_cleanup

        with patch("builtins.print") as mock_print:
            cli_main()

            mock_print.assert_called_once_with("\nShutdown completed.")
            mock_exit.assert_called_once_with(0)

    @patch("voicemeeter_mcp_server.main.asyncio.run")
    @patch("voicemeeter_mcp_server.main.sys.exit")
    def test_cli_main_exception(self, mock_exit, mock_asyncio_run):
        """Test CLI main with general exception."""
        from voicemeeter_mcp_server.main import cli_main

        test_error = Exception("Test error")

        def side_effect_with_cleanup(coro):
            # Clean up the coroutine before raising the exception
            coro.close()
            raise test_error

        mock_asyncio_run.side_effect = side_effect_with_cleanup

        with patch("builtins.print") as mock_print:
            cli_main()

            mock_print.assert_called_once_with("Error: Test error", file=sys.stderr)
            mock_exit.assert_called_once_with(1)


class TestMainWithCleanup:
    """Test cases for main_with_cleanup function - the actual production logic."""

    @pytest.mark.asyncio
    async def test_graceful_shutdown_initialization(self):
        """Test that GracefulShutdown initializes correctly."""
        from voicemeeter_mcp_server.main import GracefulShutdown

        shutdown_handler = GracefulShutdown()
        assert not shutdown_handler.shutdown_event.is_set()
        assert len(shutdown_handler.tasks) == 0

    def test_graceful_shutdown_signal_handler(self):
        """Test signal handler sets shutdown event."""
        from voicemeeter_mcp_server.main import GracefulShutdown

        shutdown_handler = GracefulShutdown()

        with patch("builtins.print") as mock_print:
            shutdown_handler.signal_handler(15, None)  # SIGTERM

            assert shutdown_handler.shutdown_event.is_set()
            mock_print.assert_called_once_with(
                "\nReceived signal 15, initiating graceful shutdown..."
            )

    @pytest.mark.asyncio
    async def test_graceful_shutdown_cleanup_tasks(self):
        """Test task cleanup functionality."""
        from voicemeeter_mcp_server.main import GracefulShutdown

        shutdown_handler = GracefulShutdown()

        # Create a real task that we can cancel
        async def dummy_task():
            try:
                await asyncio.sleep(10)  # Long sleep to ensure it gets cancelled
            except asyncio.CancelledError:
                raise

        task = asyncio.create_task(dummy_task())
        shutdown_handler.tasks.add(task)

        with patch("builtins.print") as mock_print:
            await shutdown_handler.cleanup_tasks()

            # Verify the task was cancelled
            assert task.cancelled()
            mock_print.assert_called_once_with("Cancelling pending tasks...")

    @pytest.mark.asyncio
    async def test_graceful_shutdown_add_task(self):
        """Test adding tasks to be managed."""
        from voicemeeter_mcp_server.main import GracefulShutdown

        shutdown_handler = GracefulShutdown()

        # Create a real task for this test
        async def dummy_task():
            await asyncio.sleep(0.1)

        task = asyncio.create_task(dummy_task())
        shutdown_handler.add_task(task)

        assert task in shutdown_handler.tasks

        # Wait for task to complete and verify it's removed
        await task
        assert task not in shutdown_handler.tasks

    @pytest.mark.asyncio
    async def test_main_with_cleanup_server_exception(self):
        """Test main_with_cleanup handles server exceptions properly."""
        from unittest.mock import AsyncMock

        from voicemeeter_mcp_server.main import main_with_cleanup

        test_error = Exception("Server error")

        with patch(
            "voicemeeter_mcp_server.main.main", new_callable=AsyncMock
        ) as mock_main:
            # Make the server task raise an exception
            mock_main.side_effect = test_error

            # The production code catches exceptions in the asyncio.wait() call
            # The exception gets logged by asyncio but doesn't crash the main function
            # This tests that the main_with_cleanup function completes gracefully
            # even when the server task fails
            await main_with_cleanup()

            # Verify the main function was called (and failed)
            mock_main.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_cleanup_graceful_shutdown_flow(self):
        """Test the complete graceful shutdown flow."""
        from unittest.mock import AsyncMock

        from voicemeeter_mcp_server.main import main_with_cleanup

        with patch(
            "voicemeeter_mcp_server.main.main", new_callable=AsyncMock
        ) as mock_main:
            # Create a long-running server task that we can interrupt
            shutdown_event = asyncio.Event()

            async def long_running_main():
                await shutdown_event.wait()  # Wait indefinitely

            mock_main.side_effect = long_running_main

            # Start main_with_cleanup in a task so we can control it
            main_task = asyncio.create_task(main_with_cleanup())

            # Give it a moment to start
            await asyncio.sleep(0.1)

            # Simulate shutdown signal by setting the event
            shutdown_event.set()

            # Wait for graceful shutdown
            await main_task

            # Verify main was called
            mock_main.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_cleanup_signal_handling_unix(self):
        """Test signal handling on Unix systems."""
        from unittest.mock import AsyncMock

        from voicemeeter_mcp_server.main import main_with_cleanup

        with patch("sys.platform", "linux"):
            with patch("asyncio.get_running_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop

                with patch(
                    "voicemeeter_mcp_server.main.main", new_callable=AsyncMock
                ) as mock_main:
                    mock_main.return_value = None

                    await main_with_cleanup()

                    # Verify signal handlers were set up
                    assert mock_loop.add_signal_handler.call_count == 2

    @pytest.mark.asyncio
    async def test_main_with_cleanup_windows_no_signals(self):
        """Test that signal handlers are not set up on Windows."""
        from unittest.mock import AsyncMock

        from voicemeeter_mcp_server.main import main_with_cleanup

        with patch("sys.platform", "win32"):
            with patch("asyncio.get_running_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop

                with patch(
                    "voicemeeter_mcp_server.main.main", new_callable=AsyncMock
                ) as mock_main:
                    mock_main.return_value = None

                    await main_with_cleanup()

                    # Verify no signal handlers were set up on Windows
                    mock_loop.add_signal_handler.assert_not_called()
