"""Entry point for the Bitwise Cloud MCP server."""

import sys


def _run_server() -> None:
    from .server import mcp

    mcp.run(transport="stdio")


def cli() -> None:
    if len(sys.argv) <= 1 or sys.argv[1] == "serve":
        _run_server()
    else:
        print(f"Unknown command: {sys.argv[1]}", file=sys.stderr)
        print("Usage: python -m bitwise_cloud serve", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
