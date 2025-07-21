"""Main entry point for the Voicemeeter MCP Server."""

import asyncio
import sys
from .server import main


def cli_main():
    """CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down Voicemeeter MCP Server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
