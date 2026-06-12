"""
e2e_test.py — End-to-end test for SimpleBrain
Runs setup, server, ingest, and processing. Reports pass/fail per step.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ── config ────────────────────────────────────────────────────────────────────
TEST_DIR   = Path(__file__).parent / "test-e2e"
PORT       = 8765
BASE_URL   = f"http://127.0.0.1:{PORT}"
WAIT_SECS  = 300  # max seconds to wait for worker to process

os.environ.setdefault("BRAIN_ROOT",   str(TEST_DIR))
os.environ.setdefault("BRAIN_USER",   "e2e-test")
os.environ.setdefault("BRAIN_DEVICE", "ci")

# ── helpers ───────────────────────────────────────────────────────────────────
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
WARN = "\033[33mWARN\033[0m"
INFO = "\033[36mINFO\033[0m"

results: list[tuple[str, str, str]] = []   # (step, status, detail)

def check(step: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    results.append((step, "PASS" if ok else "FAIL", detail))
    print(f"  [{status}] {step}" + (f" — {detail}" if detail else ""))
    return ok

def info(msg: str):
    print(f"  [{INFO}] {msg}")

# ── Phase 0: clean slate ──────────────────────────────────────────────────────
print("\n" + "="*60)
print("  SimpleBrain E2E Test")
print("="*60)

if TEST_DIR.exists():
    # Robust cleanup: retry on Windows file lock
    import time as _time
    for attempt in range(3):
        try:
            shutil.rmtree(TEST_DIR)
            break
        except PermissionError:
            if attempt < 2:
                info(f"test-e2e dir locked, retrying in 2s... (attempt {attempt+1})")
                _time.sleep(2)
            else:
                info("WARNING: could not fully clean test-e2e — Windows file lock. Continuing anyway.")
    else:
        pass
    info(f"Cleaned existing {TEST_DIR.name}/")

# Snapshot dirs that exist at project root BEFORE the test
_PROJECT_ROOT = Path(__file__).parent
_BRAIN_DIRS   = ["knowledge","_queue","_raw","_meta","_index","_conflicts"]
_PRE_EXISTING = {d for d in _BRAIN_DIRS if (_PROJECT_ROOT / d).exists()}

# ── Phase 1: Setup (wizard) ───────────────────────────────────────────────────
print("\n[Phase 1] Setup — LLM-designed folder structure")
print("-"*60)

try:
    from dotenv import load_dotenv
    load_dotenv()

    from simplebrain.config import BrainConfig
    from simplebrain.setup.wizard import SetupWizard

    cfg = BrainConfig(
        brain_root=TEST_DIR,
        user="e2e-test",
        device="ci",
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        llm_api_base=os.getenv("LLM_API_BASE") or None,
        llm_api_key=os.getenv("LLM_API_KEY") or None,
    )
    cfg.init_dirs()
    check("BrainConfig created + dirs initialised", True, str(TEST_DIR))

    wizard = SetupWizard(cfg)
    description = (
        "A test knowledge base for a software team. "
        "We store project notes, technical research, meeting summaries, "
        "and code architecture decisions."
    )
    info(f"Calling wizard.propose() with LLM ({cfg.llm_provider}/{cfg.llm_model})")
    proposal = wizard.propose(description)
    check("wizard.propose() returned valid proposal",
          isinstance(proposal.get("folders"), list) and len(proposal["folders"]) > 0,
          f"{len(proposal['folders'])} folders, schedule={proposal.get('healer_schedule')}")

    folders = wizard.apply(proposal)
    check("wizard.apply() created folders", len(folders) > 0, str(folders))

    # Verify on disk
    meta_ok  = (TEST_DIR / "_meta" / "setup.json").exists()
    struc_ok = (TEST_DIR / "_meta" / "structure.json").exists()
    check("_meta/setup.json written",     meta_ok)
    check("_meta/structure.json written", struc_ok)

    # Check no brain dirs leaked to project root *due to this test*.
    # We compare against the pre-existing snapshot; dirs from the running
    # brain server are expected and excluded.
    leaked = [d for d in _BRAIN_DIRS
              if (_PROJECT_ROOT / d).exists() and d not in _PRE_EXISTING]
    # Further exclude dirs that were created by the real brain server
    # (they won't contain test-generated content)
    leaked = [
        d for d in leaked
        if any(((_PROJECT_ROOT / d).rglob(f"*{name}*"))
               for name in ["e2e-test", str(TEST_DIR.name)])
    ]
    check("No dirs leaked to project root", leaked == [], str(leaked) if leaked else "clean")

except Exception as exc:
    check("Phase 1 setup", False, str(exc))
    traceback.print_exc()

# ── Phase 2: Server startup ───────────────────────────────────────────────────
print("\n[Phase 2] Server startup")
print("-"*60)

server_proc = None
try:
    import httpx

    cmd = [sys.executable, "-m", "simplebrain",
           "--dir", str(TEST_DIR), "--port", str(PORT), "--host", "127.0.0.1"]
    server_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(Path(__file__).parent),
        env={**os.environ,
             "PYTHONIOENCODING": "utf-8",
             "WHISPER_DEVICE":   os.getenv("WHISPER_DEVICE",  "cpu"),
             "WHISPER_COMPUTE":  os.getenv("WHISPER_COMPUTE", "int8"),
             "LLM_PROVIDER": os.getenv("LLM_PROVIDER","openai"),
             "LLM_MODEL":    os.getenv("LLM_MODEL","gpt-4o-mini"),
             "LLM_API_BASE": os.getenv("LLM_API_BASE",""),
             "LLM_API_KEY":  os.getenv("LLM_API_KEY",""),
             "BRAIN_ROOT":   str(TEST_DIR),
             "BRAIN_USER":   "e2e-test",
             "BRAIN_DEVICE": "ci",
             "PYTHONPATH":   str(Path(__file__).parent),
             # Keep stderr quiet so the pipe buffer never fills up.
             # The file log (brain.log) captures DEBUG regardless.
             "BRAIN_LOG_LEVEL": "WARNING",
             "BRAIN_LOG_LLM":   "0",
        }
    )

    # Drain stderr in background so the pipe never blocks the server.
    import threading as _threading, collections as _collections
    _stderr_lines: list = []
    def _drain_stderr():
        for raw in server_proc.stderr:
            try:
                _stderr_lines.append(raw.decode("utf-8", errors="replace").rstrip())
            except Exception:
                pass
    _t = _threading.Thread(target=_drain_stderr, daemon=True)
    _t.start()
    info(f"Server PID {server_proc.pid} starting on port {PORT}…")

    # Wait for /health
    alive = False
    for _ in range(20):
        time.sleep(1)
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                alive = True
                break
        except Exception:
            pass

    check("Server /health responded 200", alive)

    if alive:
        r = httpx.get(f"{BASE_URL}/status", timeout=5)
        check("/status endpoint works", r.status_code == 200, r.text[:80])

except Exception as exc:
    check("Server startup", False, str(exc))
    traceback.print_exc()

# ── Phase 3: Ingest ───────────────────────────────────────────────────────────
print("\n[Phase 3] Ingest text notes")
print("-"*60)

job_ids: list[str] = []
try:
    import httpx
    notes = [
        "We decided to use PostgreSQL for the main datastore. The key reasons are ACID compliance, "
        "JSON support via JSONB, and the team's existing familiarity with it.",

        "Meeting notes 2026-06-11: discussed Q3 roadmap. Three priorities agreed: "
        "authentication refactor, mobile API v2, and improved onboarding flow.",

        "Research spike on vector databases. Compared Pinecone, Weaviate, and pgvector. "
        "Decision: use pgvector since we are already on Postgres. Simpler ops, good enough performance.",
    ]

    for i, text in enumerate(notes):
        r = httpx.post(f"{BASE_URL}/notes/text",
                       json={"text": text, "user": "e2e-test", "device": "ci"},
                       timeout=10)
        ok = r.status_code == 200
        jid = r.json().get("job_id", "?") if ok else "?"
        job_ids.append(jid)
        check(f"POST /notes/text [{i+1}]", ok, f"job_id={jid}")

    # Check queue depth
    r = httpx.get(f"{BASE_URL}/status", timeout=5)
    qd = r.json().get("queue_depth", -1)
    info(f"Queue depth after ingest: {qd}")

    # Verify raw files exist
    raw_files = list((TEST_DIR / "_raw" / "transcripts").glob("*.txt"))
    check("Raw transcript files written", len(raw_files) == len(notes),
          f"{len(raw_files)}/{len(notes)} files")

except Exception as exc:
    check("Ingest phase", False, str(exc))
    traceback.print_exc()

# ── Phase 3b: Ingest voice note ─────────────────────────────────────────────
print("\n[Phase 3b] Ingest voice note")
print("-"*60)

try:
    import httpx, base64, struct, math

    # Build a minimal valid WAV: 1 second of 440 Hz sine, 16-bit mono 16kHz
    sample_rate  = 16000
    duration_s   = 1
    num_samples  = sample_rate * duration_s
    samples      = [int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
                    for i in range(num_samples)]
    pcm          = struct.pack(f"<{num_samples}h", *samples)

    def _wav(pcm_data: bytes, rate: int) -> bytes:
        n = len(pcm_data)
        hdr = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + n, b"WAVE",
            b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16,
            b"data", n,
        )
        return hdr + pcm_data

    wav_bytes = _wav(pcm, sample_rate)
    audio_b64 = base64.b64encode(wav_bytes).decode()

    r = httpx.post(
        f"{BASE_URL}/notes/voice",
        json={"audio_b64": audio_b64, "filename": "test-note.wav",
              "user": "e2e-test", "device": "ci"},
        timeout=15,
    )
    ok = r.status_code == 200
    voice_job_id = r.json().get("job_id", "?") if ok else "?"
    check("POST /notes/voice", ok, f"job_id={voice_job_id}")

    if ok:
        # Verify audio file saved to _raw/audio/
        audio_files = list((TEST_DIR / "_raw" / "audio").glob("*.wav"))
        check("Audio file saved to _raw/audio/", len(audio_files) == 1,
              audio_files[0].name if audio_files else "missing")

        # Don't wait here — all voice checks happen in Phase 5 after queue drains
        info("Voice note queued — transcript + chunk checks are in Phase 5")

except Exception as exc:
    check("Voice ingest phase", False, str(exc))
    traceback.print_exc()


print(f"\n[Phase 4] Worker processing (waiting up to {WAIT_SECS}s)")
print("-"*60)

try:
    import httpx

    info("Waiting for queue to drain…")
    deadline = time.time() + WAIT_SECS
    last_depth = -1
    while time.time() < deadline:
        time.sleep(3)
        r = httpx.get(f"{BASE_URL}/status", timeout=5)
        depth = r.json().get("queue_depth", -1)
        if depth != last_depth:
            info(f"  queue_depth={depth}")
            last_depth = depth
        if depth == 0:
            break

    failed_jobs = list((TEST_DIR / "_queue" / "failed").glob("*.json"))
    check("Queue drained to 0", last_depth == 0, f"depth={last_depth}")
    check("No failed jobs", len(failed_jobs) == 0,
          f"{len(failed_jobs)} failed: {[f.name for f in failed_jobs]}")

except Exception as exc:
    check("Worker wait", False, str(exc))
    traceback.print_exc()

# ── Phase 5: Verify knowledge output ─────────────────────────────────────────
print("\n[Phase 5] Verify knowledge files and index")
print("-"*60)

try:
    import httpx

    # Count .md files in knowledge/
    all_chunks = list((TEST_DIR / "knowledge").rglob("*.md"))
    readme_files = [f for f in all_chunks if f.name == "README.md"]
    chunk_files  = [f for f in all_chunks if f.name != "README.md"]

    check("Chunk .md files created", len(chunk_files) > 0,
          f"{len(chunk_files)} chunks across {len(set(f.parent for f in chunk_files))} folders")

    # Show where each chunk landed
    for cf in chunk_files:
        folder = cf.parent.name
        info(f"  {folder}/{cf.name}")

    # Check unfiled vs filed
    unfiled = list((TEST_DIR / "knowledge" / "_unfiled").glob("*.md"))
    filed   = [f for f in chunk_files if f.parent.name != "_unfiled"]
    check("At least some chunks filed (not all unfiled)",
          len(filed) > 0, f"{len(filed)} filed, {len(unfiled)} unfiled")

    # Check frontmatter
    import frontmatter as fm
    if chunk_files:
        sample = fm.load(str(chunk_files[0]))
        has_id      = "id"      in sample
        has_tags    = "tags"    in sample
        has_created = "created" in sample
        has_user    = "user"    in sample
        check("Chunk frontmatter has id/tags/created/user",
              all([has_id, has_tags, has_created, has_user]),
              f"id={has_id} tags={has_tags} created={has_created} user={has_user}")
        info(f"  Sample tags: {sample.get('tags', [])}")

    # Voice note checks — run here after queue drains
    if 'voice_job_id' in dir() and voice_job_id != "?":
        all_transcripts = list((TEST_DIR / "_raw" / "transcripts").glob("*.txt"))
        voice_txts = [f for f in all_transcripts if voice_job_id[:6] in f.name]
        check("Transcript saved to _raw/transcripts/",
              len(voice_txts) >= 1,
              voice_txts[0].name if voice_txts else "missing")
        if voice_txts:
            info(f"  Transcript content: '{voice_txts[0].read_text(encoding='utf-8')[:60]}'")

        voice_chunks = []
        for cf in chunk_files:
            post = fm.load(str(cf))
            sr = post.get("source_raw", "")
            if voice_job_id[:6] in str(sr) or "audio" in str(sr):
                voice_chunks.append((cf, sr))
        check("Voice note produced knowledge chunk",
              len(voice_chunks) >= 1,
              voice_chunks[0][0].name if voice_chunks else "no chunk found")
        if voice_chunks:
            check("Chunk source_raw points to original audio",
                  "audio" in str(voice_chunks[0][1]),
                  f"source_raw={voice_chunks[0][1]}")

    # Check index
    r = httpx.get(f"{BASE_URL}/tags", timeout=5)
    check("/tags endpoint works", r.status_code == 200)
    tags = r.json().get("tags", {})
    check("Tags index populated", len(tags) > 0, f"{len(tags)} unique tags")

    # Search
    r = httpx.get(f"{BASE_URL}/search?query=roadmap", timeout=5)
    check("/search works", r.status_code == 200)
    results_data = r.json().get("results", [])
    check("Search returns results", len(results_data) > 0, f"{len(results_data)} hits")

    # Proposals
    r = httpx.get(f"{BASE_URL}/proposals", timeout=5)
    check("/proposals endpoint works", r.status_code == 200)
    props = r.json().get("proposals", [])
    if props:
        info(f"  {len(props)} new folder proposal(s): {[p.get('proposed_folder') for p in props]}")

except Exception as exc:
    check("Knowledge verification", False, str(exc))
    traceback.print_exc()

# ── Failed job details ────────────────────────────────────────────────────────
failed_jobs = list((TEST_DIR / "_queue" / "failed").glob("*.json")) if TEST_DIR.exists() else []
if failed_jobs:
    print("\n[Failed Job Details]")
    print("-"*60)
    for fj in failed_jobs:
        data = json.loads(fj.read_text())
        print(f"  Job {data.get('id','?')}: {data.get('error','?')[:120]}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  E2E Test Summary")
print("="*60)

passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
print(f"\n  Total: {len(results)}  Passed: {passed}  Failed: {failed}\n")

if failed:
    print("  Failed steps:")
    for step, status, detail in results:
        if status == "FAIL":
            print(f"    - {step}" + (f": {detail}" if detail else ""))

print()

# ── Shutdown ──────────────────────────────────────────────────────────────────
if server_proc:
    server_proc.terminate()
    try:
        server_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_proc.kill()
    info("Server stopped")
    # Print last stderr lines collected by the drain thread
    if _stderr_lines:
        last = _stderr_lines[-20:]
        print("\n  [Server stderr (last 20 lines)]")
        for ln in last:
            print("  " + ln)

sys.exit(0 if failed == 0 else 1)
