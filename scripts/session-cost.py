"""
session-cost.py
---------------
Reports token usage and cost across all Pi sessions for a given working directory.

Usage:
    python scripts/session-cost.py                    # all sessions in current project
    python scripts/session-cost.py --all              # all sessions across all projects
    python scripts/session-cost.py --dir ~/OtherProject

Pi sessions are stored in:
    ~/.pi/agent/sessions/<encoded-cwd>/<timestamp>_<uuid>.jsonl

Each assistant message contains a usage block:
    { "input": N, "output": N, "cacheRead": N, "cacheWrite": N,
      "cost": { "input": N, "output": N, "cacheRead": N, "cacheWrite": N, "total": N } }
"""

import json
import glob
import os
import argparse
from pathlib import Path


def encode_cwd(path):
    """Match Pi's session folder naming: path separators become --"""
    return path.replace(":", "-").replace("\\", "-").replace("/", "-")


def load_session(filepath):
    session_info = {}
    model_id = None
    provider = None
    name = None
    s_input = 0
    s_output = 0
    s_cache_read = 0
    s_cache_write = 0
    s_cost = 0.0
    msg_count = 0
    first_user_msg = None

    with open(filepath, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                t = d.get("type", "")
                if t == "session":
                    session_info = d
                elif t == "name":
                    name = d.get("name")
                elif t == "model_change":
                    provider = d.get("provider")
                    model_id = d.get("modelId")
                elif t == "message":
                    msg_count += 1
                    msg = d.get("message", {})
                    if isinstance(msg, dict):
                        role = msg.get("role", "")
                        if role == "user" and first_user_msg is None:
                            content = msg.get("content", [])
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    first_user_msg = block.get("text", "")[:60].replace("\n", " ")
                                    break
                        usage = msg.get("usage", {})
                        if usage:
                            s_input += usage.get("input", 0)
                            s_output += usage.get("output", 0)
                            s_cache_read += usage.get("cacheRead", 0)
                            s_cache_write += usage.get("cacheWrite", 0)
                            cost_block = usage.get("cost", {})
                            if isinstance(cost_block, dict):
                                s_cost += cost_block.get("total", 0)
            except Exception:
                pass

    home = str(Path.home()) + os.sep
    cwd = session_info.get("cwd", "?") or "?"
    cwd_short = cwd.replace(home, "~/") if cwd.startswith(home) else cwd

    return {
        "file": filepath,
        "id": session_info.get("id", "?")[:8],
        "started": (session_info.get("timestamp", "?")[:16]).replace("T", " "),
        "cwd": cwd_short,
        "name": name or "(unnamed)",
        "provider": provider or "?",
        "model": model_id or "unknown",
        "msgs": msg_count,
        "first_msg": first_user_msg or "",
        "input": s_input,
        "output": s_output,
        "cache_read": s_cache_read,
        "cache_write": s_cache_write,
        "cost": s_cost,
    }


def print_report(sessions, title):
    total_input = sum(s["input"] for s in sessions)
    total_output = sum(s["output"] for s in sessions)
    total_cache_read = sum(s["cache_read"] for s in sessions)
    total_cache_write = sum(s["cache_write"] for s in sessions)
    total_cost = sum(s["cost"] for s in sessions)
    total_msgs = sum(s["msgs"] for s in sessions)

    W = 130
    print("")
    print("  " + title)
    print("  " + "-" * W)
    header = (
        "  " +
        "Started".ljust(17) +
        "ID".ljust(10) +
        "Model".ljust(26) +
        "Msgs".rjust(5) +
        "In Tok".rjust(10) +
        "Out Tok".rjust(10) +
        "Cache R".rjust(12) +
        "Cache W".rjust(10) +
        "Cost USD".rjust(12)
    )
    print(header)
    print("  " + "-" * W)

    for s in sessions:
        mdl = (s["provider"] + "/" + s["model"])[:26]
        row = (
            "  " +
            s["started"].ljust(17) +
            s["id"].ljust(10) +
            mdl.ljust(26) +
            str(s["msgs"]).rjust(5) +
            str(s["input"]).rjust(10) +
            str(s["output"]).rjust(10) +
            str(s["cache_read"]).rjust(12) +
            str(s["cache_write"]).rjust(10) +
            ("$" + "{:.4f}".format(s["cost"])).rjust(12)
        )
        print(row)
        if s["first_msg"]:
            preview = s["first_msg"]
            if len(preview) >= 60:
                preview += "..."
            print("  " + " " * 27 + "preview: " + preview)

    print("  " + "-" * W)
    totals = (
        "  " +
        "TOTAL".ljust(17) +
        ("-").ljust(10) +
        ("-").ljust(26) +
        str(total_msgs).rjust(5) +
        str(total_input).rjust(10) +
        str(total_output).rjust(10) +
        str(total_cache_read).rjust(12) +
        str(total_cache_write).rjust(10) +
        ("$" + "{:.4f}".format(total_cost)).rjust(12)
    )
    print(totals)
    print("")
    print("  Summary")
    print("  --------")
    print("  Sessions       : " + str(len(sessions)))
    print("  Total messages : " + str(total_msgs))
    print("  Input tokens   : " + "{:,}".format(total_input))
    print("  Output tokens  : " + "{:,}".format(total_output))
    print("  Cache reads    : " + "{:,}".format(total_cache_read))
    print("  Cache writes   : " + "{:,}".format(total_cache_write))

    total_tokens = total_input + total_output + total_cache_read + total_cache_write
    if total_tokens > 0:
        cache_hit_pct = (total_cache_read / total_tokens) * 100
        print("  Cache hit rate : {:.1f}%".format(cache_hit_pct))

    print("  Grand total    : $" + "{:.4f}".format(total_cost) + " USD")
    print("")


def main():
    parser = argparse.ArgumentParser(description="Pi session cost and token reporter")
    parser.add_argument("--all", action="store_true", help="Include all projects, not just current cwd")
    parser.add_argument("--dir", default=None, help="Project directory to filter by (default: current)")
    args = parser.parse_args()

    session_root = Path.home() / ".pi" / "agent" / "sessions"

    if args.all:
        pattern = str(session_root / "**" / "*.jsonl")
        title = "Pi Sessions - All Projects"
    else:
        target_dir = Path(args.dir).resolve() if args.dir else Path.cwd()
        encoded = encode_cwd(str(target_dir))
        # Pi uses -- as separator and removes drive colon
        folder_name = "--" + encoded.lstrip("-")
        session_dir = session_root / folder_name

        if not session_dir.exists():
            # Try to find matching folder
            candidates = [d for d in session_root.iterdir()
                          if d.is_dir() and str(target_dir.name).lower() in d.name.lower()]
            if not candidates:
                print("")
                print("  No sessions found for: " + str(target_dir))
                print("  Session folder would be: " + str(session_dir))
                print("  Use --all to see all sessions.")
                print("")
                return
            session_dir = candidates[0]

        pattern = str(session_dir / "*.jsonl")
        title = "Pi Sessions - " + str(target_dir)

    files = sorted(glob.glob(pattern, recursive=True))

    if not files:
        print("")
        print("  No session files found.")
        print("")
        return

    sessions = []
    for f in files:
        try:
            sessions.append(load_session(f))
        except Exception as e:
            print("  WARN: could not read " + f + " -> " + str(e))

    sessions.sort(key=lambda x: x["started"])
    print_report(sessions, title)


if __name__ == "__main__":
    main()
