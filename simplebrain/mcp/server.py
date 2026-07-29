"""SimpleBrain MCP server — all tool definitions."""
from __future__ import annotations
import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from simplebrain.config import BrainConfig
from simplebrain.ingest.service import IngestService
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.store.index import IndexStore
from simplebrain.brain.grower import SelfGrower
from simplebrain.brain.healer import SelfHealer
from simplebrain.models import Resolution


# ---------------------------------------------------------------------------
# Thin wrapper so tests can call list_tools() / call_tool() synchronously
# while the underlying mcp.server.Server drives the stdio transport.
# ---------------------------------------------------------------------------

class SimpleBrainMCPServer:
    """Wraps an mcp Server and exposes sync helpers for testing."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self._ingest = IngestService(config)
        self._knowledge = KnowledgeStore(config)
        self._index = IndexStore(config)
        self._grower = SelfGrower(config)
        self._healer = SelfHealer(config)

        # Build the underlying MCP Server and register handlers
        self._server = Server("simplebrain")
        self._tools: list[Tool] = self._build_tools()
        self._register_handlers()

    # ------------------------------------------------------------------
    # Public sync API (used by tests and __main__ stdio bridge)
    # ------------------------------------------------------------------

    def list_tools(self) -> list[Tool]:
        return self._tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(
                self._call_tool_async(name, arguments), loop
            )
            return future.result()
        return asyncio.run(self._call_tool_async(name, arguments))

    @property
    def mcp_server(self) -> Server:
        """The underlying mcp.server.Server (use for stdio transport)."""
        return self._server

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ok(self, data: dict) -> list[TextContent]:
        return [TextContent(type="text", text=json.dumps(data))]

    def _build_tools(self) -> list[Tool]:
        def T(name, description, required=None, properties=None):
            return Tool(
                name=name,
                description=description,
                inputSchema={
                    "type": "object",
                    "properties": properties or {},
                    **({"required": required} if required else {}),
                },
            )

        return [
            T("add_text_note",
              "Add a text note to the brain",
              required=["text", "user"],
              properties={
                  "text": {"type": "string", "description": "Note content"},
                  "user": {"type": "string"},
                  "device": {"type": "string", "default": "unknown"},
              }),
            T("add_voice_note",
              "Add a voice note (base64-encoded audio) to the brain",
              required=["audio_b64", "filename", "user"],
              properties={
                  "audio_b64": {"type": "string", "description": "Base64-encoded audio"},
                  "filename": {"type": "string"},
                  "user": {"type": "string"},
                  "device": {"type": "string", "default": "unknown"},
              }),
            T("add_document",
              "Add a document (base64-encoded PDF, DOCX, PPTX, etc.) to the brain",
              required=["file_b64", "filename", "user"],
              properties={
                  "file_b64": {"type": "string", "description": "Base64-encoded document"},
                  "filename": {"type": "string", "description": "Original filename with extension"},
                  "user": {"type": "string"},
                  "device": {"type": "string", "default": "unknown"},
              }),
            T("job_status",
              "Check the processing status of an ingestion job",
              required=["job_id"],
              properties={
                  "job_id": {"type": "string"},
              }),
            T("search",
              "Full-text search of the knowledge base",
              required=["query"],
              properties={
                  "query": {"type": "string"},
                  "tags": {"type": "array", "items": {"type": "string"}},
              }),
            T("get_chunk",
              "Retrieve a specific knowledge chunk by ID",
              required=["chunk_id"],
              properties={
                  "chunk_id": {"type": "string"},
              }),
            T("list_topics",
              "List all topics in the knowledge base with chunk counts",
              properties={}),
            T("list_tags",
              "List all tags with their usage counts",
              properties={}),
            T("list_pending_folder_proposals",
              "List pending folder-creation proposals from the SelfGrower",
              properties={}),
            T("confirm_folder_proposal",
              "Confirm a folder proposal, creating the new folder",
              required=["proposal_id"],
              properties={
                  "proposal_id": {"type": "string"},
              }),
            T("reject_folder_proposal",
              "Reject a folder proposal",
              required=["proposal_id", "target_folder"],
              properties={
                  "proposal_id": {"type": "string"},
                  "target_folder": {
                      "type": "string",
                      "description": "Existing folder to refile held chunks into",
                  },
              }),
            T("list_conflicts",
              "List all pending knowledge conflicts detected by the SelfHealer",
              properties={}),
            T("resolve_conflict",
              "Resolve a pending conflict",
              required=["conflict_id", "resolution", "resolved_by"],
              properties={
                  "conflict_id": {"type": "string"},
                  "resolution": {
                      "type": "string",
                      "enum": [r.value for r in Resolution],
                  },
                  "resolved_by": {"type": "string"},
              }),
            T("revert_resolution",
              "Revert a previously resolved conflict to its original state",
              required=["conflict_id"],
              properties={
                  "conflict_id": {"type": "string"},
              }),
            T("run_healer",
              "Manually trigger a self-healing scan across all knowledge folders",
              properties={}),
            T("get_brain_status",
              "Get a summary of brain health: queue depth, conflicts, proposals",
              properties={}),
        ]

    def _register_handlers(self):
        server = self._server

        @server.list_tools()
        async def _list_tools() -> list[Tool]:
            return self._tools

        @server.call_tool()
        async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
            return await self._call_tool_async(name, arguments)

    async def _call_tool_async(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        ok = self._ok

        # ---- Ingest -------------------------------------------------------
        if name == "add_text_note":
            job_id = self._ingest.add_text_note(
                arguments["text"],
                arguments["user"],
                arguments.get("device", "unknown"),
            )
            return ok({"job_id": job_id})

        elif name == "add_voice_note":
            import base64
            audio = base64.b64decode(arguments["audio_b64"])
            job_id = self._ingest.add_voice_note(
                audio,
                arguments["filename"],
                arguments["user"],
                arguments.get("device", "unknown"),
            )
            return ok({"job_id": job_id})

        elif name == "add_document":
            import base64 as _base64
            try:
                doc = _base64.b64decode(arguments["file_b64"])
            except Exception:
                return ok({"error": "Invalid base64 in file_b64"})
            job_id = self._ingest.add_document(
                doc,
                arguments["filename"],
                arguments["user"],
                arguments.get("device", "unknown"),
            )
            return ok({"job_id": job_id})

        elif name == "job_status":
            from simplebrain.ingest.queue import FileQueue
            q = FileQueue(self.config)
            job_id = arguments["job_id"]
            # Peek at the queue without consuming jobs
            pending = [f for f in self.config.queue_dir.glob("*.json")
                       if f"-{job_id}.json" in f.name]
            failed = [f for f in (self.config.queue_dir / "failed").glob("*.json")
                      if f"-{job_id}.json" in f.name]
            if pending:
                status = "pending"
            elif failed:
                status = "failed"
            else:
                status = "complete_or_not_found"
            return ok({"job_id": job_id, "status": status})

        # ---- Search / Retrieve --------------------------------------------
        elif name == "search":
            ids = self._index.search(
                arguments["query"], arguments.get("tags", [])
            )
            results = []
            for cid in ids[:10]:
                try:
                    c = self._knowledge.read(cid)
                    results.append({
                        "id": c.id,
                        "content": c.content[:300],
                        "tags": c.tags,
                        "file_path": c.file_path,
                    })
                except FileNotFoundError:
                    continue
            return ok({"results": results})

        elif name == "get_chunk":
            try:
                c = self._knowledge.read(arguments["chunk_id"])
                return ok({
                    "id": c.id,
                    "content": c.content,
                    "tags": c.tags,
                    "links": c.links,
                    "parent": c.parent,
                    "user": c.user,
                    "device": c.device,
                    "created": c.created.isoformat(),
                    "file_path": c.file_path,
                })
            except FileNotFoundError:
                return ok({"error": f"Chunk {arguments['chunk_id']} not found"})

        # ---- Index --------------------------------------------------------
        elif name == "list_topics":
            topics = self._index.load_topics()
            return ok({"topics": {k: len(v) for k, v in topics.items()}})

        elif name == "list_tags":
            tags = self._index.load_tags()
            return ok({"tags": {k: len(v) for k, v in tags.items()}})

        # ---- Grower -------------------------------------------------------
        elif name == "list_pending_folder_proposals":
            proposals = self._grower.list_pending()
            return ok({
                "proposals": [json.loads(p.model_dump_json()) for p in proposals]
            })

        elif name == "confirm_folder_proposal":
            p = self._grower.confirm_proposal(arguments["proposal_id"])
            return ok({
                "confirmed": p is not None,
                "folder": p.proposed_folder if p else None,
            })

        elif name == "reject_folder_proposal":
            p = self._grower.reject_proposal(arguments["proposal_id"])
            return ok({"rejected": p is not None})

        # ---- Healer -------------------------------------------------------
        elif name == "list_conflicts":
            conflicts = self._healer.list_pending()
            return ok({
                "conflicts": [json.loads(c.model_dump_json()) for c in conflicts]
            })

        elif name == "resolve_conflict":
            try:
                self._healer.resolve(
                    arguments["conflict_id"],
                    Resolution(arguments["resolution"]),
                    arguments["resolved_by"],
                )
                return ok({"resolved": True})
            except (FileNotFoundError, ValueError) as exc:
                return ok({"resolved": False, "error": str(exc)})

        elif name == "revert_resolution":
            try:
                self._healer.revert(arguments["conflict_id"])
                return ok({"reverted": True})
            except (FileNotFoundError, ValueError) as exc:
                return ok({"reverted": False, "error": str(exc)})

        elif name == "run_healer":
            conflicts = self._healer.scan()
            return ok({"conflicts_found": len(conflicts)})

        # ---- Status -------------------------------------------------------
        elif name == "get_brain_status":
            queue_files = list(self.config.queue_dir.glob("*.json"))
            return ok({
                "queue_depth": len(queue_files),
                "pending_conflicts": len(self._healer.list_pending()),
                "pending_proposals": len(self._grower.list_pending()),
            })

        # ---- Unknown ------------------------------------------------------
        return ok({"error": f"Unknown tool: {name}"})


# ---------------------------------------------------------------------------
# Factory — used by __main__ and tests
# ---------------------------------------------------------------------------

def create_mcp_server(config: BrainConfig) -> SimpleBrainMCPServer:
    """Create and return a SimpleBrainMCPServer for the given config."""
    return SimpleBrainMCPServer(config)
