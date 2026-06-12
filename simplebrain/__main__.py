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
    parser.add_argument(
        "--dir",
        default=None,
        metavar="PATH",
        help="Brain root directory (overrides BRAIN_ROOT in .env)",
    )
    args = parser.parse_args()

    config = BrainConfig.from_env()
    if args.dir:
        from pathlib import Path
        config = config.model_copy(update={"brain_root": Path(args.dir).expanduser().resolve()})
    config.init_dirs()  # create dirs once, at the final brain_root only

    from simplebrain.logger import setup_logging
    setup_logging(config.brain_root)

    if args.setup:
        _run_setup(config)
        return

    if args.mcp:
        _run_mcp(config)
        return

    _run_all(config, args.host, args.port)


def _run_setup(config: BrainConfig) -> None:
    """Single-question setup: describe your brain, LLM designs the structure."""
    from simplebrain.setup.wizard import SetupWizard
    from simplebrain.config import SUPPORTED_PROVIDERS

    print()
    print("  SimpleBrain Setup")
    print("  " + "-" * 50)
    print()
    print("  LLM config is read from your .env file.")
    print(f"  Provider : {config.llm_provider}")
    print(f"  Model    : {config.llm_model}")
    if config.llm_api_base:
        print(f"  API base : {config.llm_api_base}")
    print(f"  Supported: {' | '.join(SUPPORTED_PROVIDERS)}")
    print(f"  Brain dir: {config.brain_root}")
    print()

    # Verify LLM key is present for providers that need one
    _warn_if_missing_api_key(config)

    print("  Describe your knowledge base in your own words.")
    print("  Include: what it's for, who will use it, what topics or areas")
    print("  you plan to store, and anything else that would help organise it.")
    print("  (End input with a blank line)")
    print()

    lines: list[str] = []
    while True:
        try:
            line = input("  > ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line == "" and lines:
            break
        lines.append(line)

    description = "\n".join(lines).strip()
    if not description:
        print("\n  No description provided. Setup cancelled.")
        return

    print()
    print("  Thinking...", flush=True)

    wizard = SetupWizard(config)

    try:
        proposal = wizard.propose(description)
    except ValueError as exc:
        print(f"\n  Error: {exc}")
        print("  Check your LLM config in .env and try again.")
        return

    # Pretty-print the proposed structure
    _print_proposal(proposal)

    # Ask for confirmation
    try:
        confirm = input("  Create this structure? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = "n"

    if confirm in ("", "y", "yes"):
        folders = wizard.apply(proposal)
        print()
        print(f"  Setup complete! Created {len(folders)} folders under:")
        print(f"  {config.knowledge_dir}")
        print()
        print("  Next steps:")
        print("    Run the brain:  python -m simplebrain")
        print("    Run MCP server: python -m simplebrain --mcp")
        print()
    else:
        print()
        print("  Setup cancelled. Nothing was created.")
        print()


def _warn_if_missing_api_key(config: BrainConfig) -> None:
    """Print a warning if a real API key is probably needed but not set."""
    from simplebrain.config import _PROVIDERS_REQUIRING_KEY, _PROVIDER_API_KEY_ENV
    import os

    provider = config.llm_provider.lower()
    if provider not in _PROVIDERS_REQUIRING_KEY:
        return  # local providers (ollama, lmstudio) never need a key

    key_set = bool(config.llm_api_key)
    env_var = _PROVIDER_API_KEY_ENV.get(provider, "LLM_API_KEY")
    if not key_set and not os.getenv(env_var):
        print(f"  WARNING: {env_var} is not set. The LLM call may fail.")
        print(f"  Set it in your .env file or as an environment variable.")
        print()


def _print_proposal(proposal: dict) -> None:
    """Print the LLM-proposed structure in a readable format."""
    folders = proposal.get("folders", [])
    summary = proposal.get("summary", "")
    schedule = proposal.get("healer_schedule", "daily")

    print()
    print("  Proposed Knowledge Base")
    print("  " + "-" * 50)
    if summary:
        print(f"  Purpose : {summary}")
    print(f"  Healing : {schedule}")
    print()
    print(f"  {'Folder':<22} Description")
    print(f"  {'------':<22} -----------")
    for f in folders:
        name = f.get("name", "")
        desc = f.get("description", "")
        # Wrap description at 55 chars
        if len(desc) > 55:
            desc = desc[:52] + "..."
        print(f"  {name:<22} {desc}")
        examples = f.get("examples", [])
        if examples:
            ex_str = ", ".join(examples[:3])
            print(f"  {'':22} e.g. {ex_str}")
    print()


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

    print(f"\nSimpleBrain v0.1.0")
    print(f"   Brain root: {config.brain_root}")
    print(f"   API:        http://{ip}:{port}")
    print(f"   UI:         http://{ip}:{port}/ui/index.html")
    print(f"   Docs:       http://{ip}:{port}/docs\n")

    app = create_app(config)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
