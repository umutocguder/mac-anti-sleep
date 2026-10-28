# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Command-Line Interface (CLI) for mac-anti-sleep / ai-sleep-guard.
Provides commands for status reporting, manual overrides, daemon execution, and command wrapping.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time

from .daemon import SleepGuardDaemon, STATUS_FILE, PID_FILE
from .detectors import (
    set_signal_active,
    clear_signal,
    is_signal_active,
    check_antigravity_activity,
    check_claude_activity,
    check_codex_activity
)
from .caffeinate_manager import CaffeinateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai-sleep-guard")


def cmd_daemon(args: argparse.Namespace) -> None:
    """Runs the persistent background daemon."""
    daemon = SleepGuardDaemon(
        poll_interval=args.poll_interval,
        cooldown_seconds=args.cooldown
    )
    daemon.run()


def cmd_status(args: argparse.Namespace) -> None:
    """Displays real-time status of detectors, agents, and caffeinate assertions."""
    print("=" * 64)
    print("  🌙 11Hopem AI Sleep Guard — Live Status")
    print("=" * 64)

    # 1. Check daemon PID
    daemon_running = False
    daemon_pid = None
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                daemon_pid = int(f.read().strip())
            # Check if alive
            os.kill(daemon_pid, 0)
            daemon_running = True
        except (ValueError, OSError):
            daemon_running = False

    daemon_badge = f"\033[92m● ACTIVE (PID: {daemon_pid})\033[0m" if daemon_running else "\033[91m● STOPPED\033[0m"
    print(f"Daemon Service:       {daemon_badge}")

    # 2. Check Display Sleep Assertion
    display_assertion = CaffeinateManager.check_system_display_assertion()
    display_badge = (
        "\033[92m● DISPLAY SLEEP PREVENTED (Awake)\033[0m"
        if display_assertion else
        "\033[90m○ Normal Display Sleep Allowed\033[0m"
    )
    print(f"Screen Sleep Status:  {display_badge}")
    print("-" * 64)

    # 3. Live Detectors
    ag_active, ag_det = check_antigravity_activity()
    cl_active, cl_det = check_claude_activity()
    cx_active, cx_det = check_codex_activity()
    manual_active, manual_age = is_signal_active("manual")

    def format_badge(active: bool, detail: str) -> str:
        if active:
            return f"\033[92m● RUNNING\033[0m  ({detail})"
        return f"\033[90m○ IDLE\033[0m     ({detail})"

    print(f"1. Antigravity (Burda): {format_badge(ag_active, ag_det.get('reason', ''))}")
    print(f"2. Claude Code:         {format_badge(cl_active, cl_det.get('reason', ''))}")
    print(f"3. OpenAI Codex:        {format_badge(cx_active, cx_det.get('reason', ''))}")
    if manual_active:
        print(f"4. Manual Override:     \033[93m● FORCED AWAKE\033[0m ({manual_age:.1f}s ago)")

    print("-" * 64)

    # 4. Snapshot File Details
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                snap = json.load(f)
            caff = snap.get("caffeinate", {})
            if caff.get("caffeinate_running"):
                duration = caff.get("active_duration_seconds", 0)
                pid = caff.get("pid", "N/A")
                print(f"Caffeinate Process:   PID {pid} | Active Duration: {duration}s")
            cooldown_left = caff.get("cooldown_remaining_seconds", 0)
            if cooldown_left > 0 and not (ag_active or cl_active or cx_active or manual_active):
                print(f"Cooldown Buffer:      {cooldown_left}s remaining before sleep restored")
        except Exception:
            pass

    print("=" * 64)


def cmd_ping(args: argparse.Namespace) -> None:
    """Marks an agent active by touching its signal."""
    set_signal_active(args.agent)
    print(f"Active signal recorded for: {args.agent}")


def cmd_done(args: argparse.Namespace) -> None:
    """Clears the active signal for an agent."""
    clear_signal(args.agent)
    print(f"Active signal cleared for: {args.agent}")


def cmd_on(args: argparse.Namespace) -> None:
    """Manually enables sleep prevention override."""
    set_signal_active("manual")
    print(f"Manual sleep prevention ENABLED. Screen will stay awake.")


def cmd_off(args: argparse.Namespace) -> None:
    """Disables manual sleep prevention override."""
    clear_signal("manual")
    print("Manual sleep prevention DISABLED.")


def cmd_wrap(args: argparse.Namespace) -> None:
    """Runs a command while keeping sleep prevention active until completion."""
    agent = args.agent or "wrapped_command"
    cmd = args.command
    if not cmd:
        print("Error: No command specified to wrap.", file=sys.stderr)
        sys.exit(1)

    set_signal_active(agent)
    # Also start temporary caffeinate process just in case daemon is not running
    mgr = CaffeinateManager()
    mgr.start(reason=f"wrapped: {' '.join(cmd)}")

    try:
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    finally:
        clear_signal(agent)
        mgr.stop()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-sleep-guard",
        description="Prevents Mac display sleep while AI agents (Antigravity, Claude, Codex) run prompts."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # daemon
    daemon_parser = subparsers.add_parser("daemon", help="Run the background sleep guard daemon")
    daemon_parser.add_argument("--poll-interval", type=float, default=2.5, help="Poll interval in seconds (default: 2.5)")
    daemon_parser.add_argument("--cooldown", type=float, default=45.0, help="Idle cooldown buffer in seconds (default: 45.0)")

    # status
    subparsers.add_parser("status", help="Show current live status of detectors and screen assertion")

    # ping
    ping_parser = subparsers.add_parser("ping", help="Record an active prompt turn for an agent")
    ping_parser.add_argument("agent", choices=["antigravity", "claude", "codex", "custom"], help="Agent identifier")

    # done
    done_parser = subparsers.add_parser("done", help="Clear active turn signal for an agent")
    done_parser.add_argument("agent", choices=["antigravity", "claude", "codex", "custom"], help="Agent identifier")

    # on
    subparsers.add_parser("on", help="Manually force screen awake")

    # off
    subparsers.add_parser("off", help="Release manual force awake")

    # wrap
    wrap_parser = subparsers.add_parser("wrap", help="Wrap a command to keep display awake while it runs")
    wrap_parser.add_argument("--agent", choices=["antigravity", "claude", "codex"], default="claude", help="Agent name")
    wrap_parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute")

    args = parser.parse_args()

    if args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "ping":
        cmd_ping(args)
    elif args.command == "done":
        cmd_done(args)
    elif args.command == "on":
        cmd_on(args)
    elif args.command == "off":
        cmd_off(args)
    elif args.command == "wrap":
        cmd_wrap(args)
    else:
        # Default action is status
        cmd_status(args)


if __name__ == "__main__":
    main()
