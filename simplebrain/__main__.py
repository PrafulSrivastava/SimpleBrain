"""SimpleBrain entry point — python -m simplebrain"""
from __future__ import annotations
import argparse
import threading
import uvicorn
from simplebrain.config import BrainConfig


def main():
    parser = argparse.ArgumentParser(
        description="SimpleBrain — self-organising, self-growing, self-healing second brain"
    )
    parser.add_argument("--setup", action="store_true", help="Run the interactive setup wizard")
    parser.add_argument("--mcp", action="store_true", help="Run as MCP server over stdio")
    parser.add_argument("--host", default="0.0.0.0", help="API host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="API port (default: 8000)")
    args = parser.parse_args()

    config = BrainConfig.from_env()

    if args.setup:
        _run_setup(config)
        return

    if args.mcp:
        _run_mcp(config)
        return

    _run_all(config, args.host, args.port)


def _run_setup(config: BrainConfig) -> None:
    """Interactive setup wizard."""
    from simplebrain.setup.wizard import SetupWizard

    print("🧠 SimpleBrain Setup\n")
    purpose = input("What is this knowledge base about?\n> ").strip()
    users_raw = input("Who will use it? (comma-separated usernames)\n> ")
    users = [u.strip() for u in users_raw.split(",") if u.strip()]
    topics_raw = input("What are the main topics? (comma-separated)\n> ")
    topics = [t.strip() for t in topics_raw.split(",") if t.strip()]
    schedule = input("Healer schedule? (daily/weekly/manual) [daily]\n> ").strip() or "daily"
    provider = input("LLM provider? (openai/anthropic/ollama) [openai]\n> ").strip() or "openai"
    model = input("LLM model? (e.g. gpt-4o-mini) [gpt-4o-mini]\n> ").strip() or "gpt-4o-mini"

    answers = {
        "purpose": purpose,
        "users": users,
        "topics": topics,
        "healer_schedule": schedule,
        "llm_provider": provider,
        "llm_model": model,
    }

    wizard = SetupWizard(config)
    folders = wizard.run(answers)
    print(f"\n✅ Setup complete! Created folders: {', '.join(folders)}")
    print(f"\nRun the brain:  python -m simplebrain")
    print(f"Run MCP server: python -m simplebrain --mcp")


def _run_mcp(config: BrainConfig) -> None:
    """Run SimpleBrain as a stdio MCP server (for Claude Desktop / MCP CLI)."""
    import asyncio
    from mcp.server.stdio import stdio_server
    from simplebrain.mcp.server import create_mcp_server

    sb_server = create_mcp_server(config)

    async def _serve():
        async with stdio_server() as (read_stream, write_stream):
            await sb_server.mcp_server.run(
                read_stream,
                write_stream,
                sb_server.mcp_server.create_initialization_options(),
            )

    asyncio.run(_serve())


def _run_all(config: BrainConfig, host: str, port: int) -> None:
    """Start the background worker + FastAPI server."""
    import socket
    from simplebrain.pipeline.worker import BackgroundWorker
    from simplebrain.api.routes import create_app

    # Background worker in a daemon thread
    worker = BackgroundWorker(config)
    worker_thread = threading.Thread(target=worker.run_forever, daemon=True)
    worker_thread.start()

    # Determine a reachable IP for the banner
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = host

    print(f"\n🧠 SimpleBrain v0.1.0")
    print(f"   Brain root: {config.brain_root}")
    print(f"   API:        http://{ip}:{port}")
    print(f"   UI:         http://{ip}:{port}/ui/index.html")
    print(f"   Docs:       http://{ip}:{port}/docs\n")

    app = create_app(config)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
