"""Launch the shared MCP server with the same endpoint as Codex hooks."""

import os

from _codex_config import configure


def main():
    configure()
    os.environ["NOISY_STUDIO_REQUIRE_AGENT_ID"] = "1"
    os.environ["NOISY_STUDIO_MCP_TRANSPORT"] = "stdio"
    from noisy_studio.server import main as serve

    serve()


if __name__ == "__main__":
    main()
