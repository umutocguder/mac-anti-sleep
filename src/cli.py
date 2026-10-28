# Created by 11Hopem
# Copyright (c) 2026 11Hopem. All rights reserved.
# Licensed under 11Hopem Proprietary License.

"""
Command-Line Interface (CLI) for mac-anti-sleep / ai-sleep-guard.
Provides commands for status reporting, manual overrides, daemon execution,
thermal health diagnostics, sudoers setup, and command wrapping.
"""

import argparse
import getpass
import json
import logging
import os
import subprocess
import sys
import time

from src.daemon import SleepGuardDaemon, STATUS_FILE, PID_FILE
from src.detectors import (
    set_signal_active,
    clear_signal,
    is_signal_active,
    check_antigravity_activity,
    check_claude_activity,
    check_codex_activity
)
from src.caffeinate_manager import CaffeinateManager
from src.clamshell_manager import ClamshellManager
from src.thermal import ThermalGuard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai-sleep-guard")


def cmd_daemon(args: argparse.Namespace) -> None:
    """Runs the persistent background daemon."""
    daemon = SleepGuardDaemon(
        poll_interval=args.poll_interval,
        cooldown_seconds=args.cooldown,
        enable_clamshell=not args.no_clamshell
    )
    daemon.run()


def cmd_status(args: argparse.Namespace) -> None:
    """Displays real-time status of detectors, thermal guard, and sleep assertions."""
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

    # 3. Check Clamshell / Lid-Closed Sleep Prevention
    clamshell = ClamshellManager()
    clam_status = clamshell.get_status()
    if clam_status["clamshell_preventing_sleep"]:
        clam_badge = "\033[92m● ACTIVE (Lid-closed will NOT sleep)\033[0m"
    elif clam_status["sudoers_configured"]:
        clam_badge = "\033[96m○ READY (Sudoers configured)\033[0m"
    else:
        clam_badge = "\033[93m△ REQUIRES SUDOERS SETUP (Run: ai-sleep-guard setup-sudo)\033[0m"
    print(f"Lid-Close Sleep Guard:{clam_badge}")

    # 4. Thermal Safety Status
    thermal = ThermalGuard()
    therm_status = thermal.get_thermal_status()
    code = therm_status.get("thermal_state_code", 0)
    name = therm_status.get("thermal_state_name", "Unknown")

    if code == 0:
        therm_badge = f"\033[92m● SAFE ({name})\033[0m"
    elif code == 1:
        therm_badge = f"\033[93m● FAIR ({name})\033[0m"
    elif code == 2:
        therm_badge = f"\033[91m▲ SERIOUS (High Temp)\033[0m"
    else:
        therm_badge = f"\033[91;1m🔴 CRITICAL (Emergency Halt)\033[0m"

    cpu_lim = therm_status.get("cpu_speed_limit")
    if cpu_lim is not None:
        therm_badge += f" | CPU Limit: {cpu_lim}%"
    print(f"Thermal Protection:   {therm_badge}")
    print("-" * 64)

    # 5. Live Detectors
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

    # 6. Snapshot File Details
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
            if snap.get("emergency_thermal_halt"):
                print("\033[91;1m⚠️ WARNING: System recently executed an Emergency Thermal Halt!\033[0m")
        except Exception:
            pass

    print("=" * 64)


def cmd_thermal(args: argparse.Namespace) -> None:
    """Displays detailed thermal pressure and CPU limits."""
    tg = ThermalGuard()
    status = tg.get_thermal_status()
    pmset_raw = tg.query_pmset_thermal().get("raw_output", "")

    print("=" * 64)
    print("  🌡️ 11Hopem AI Sleep Guard — Thermal Diagnostics")
    print("=" * 64)
    print(f"macOS Thermal State:  {status['thermal_state_name']} (Code {status['thermal_state_code']})")
    print(f"Overheating Status:   {'YES (Action Required)' if status['is_overheating'] else 'NO (Normal)'}")
    print(f"Critical Danger:      {'YES' if status['is_critical'] else 'NO'}")
    print(f"Thermal Lockout:      {'ACTIVE' if status['lockout_active'] else 'INACTIVE'}")
    if status['cpu_speed_limit'] is not None:
        print(f"CPU Speed Limit:      {status['cpu_speed_limit']}%")
    print("-" * 64)
    print("Raw pmset therm output:")
    print(pmset_raw if pmset_raw else "  (No warnings recorded)")
    print("=" * 64)


def cmd_setup_sudo(args: argparse.Namespace) -> None:
    """Installs or displays instructions for passwordless pmset sudoers configuration."""
    current_user = getpass.getuser()
    sudoers_path = "/etc/sudoers.d/ai-sleep-guard"
    sudoers_rule = f"{current_user} ALL=(ALL) NOPASSWD: /usr/bin/pmset -a disablesleep 1, /usr/bin/pmset -a disablesleep 0, /usr/bin/pmset -g, /usr/bin/pmset sleepnow\n"

    print("=" * 64)
    print("  ⚙️ 11Hopem AI Sleep Guard — Sudoers Configuration")
    print("=" * 64)

    # Check if already working
    cm = ClamshellManager()
    if cm.can_manage_clamshell():
        print("\033[92m● Sudoers is already configured correctly!\033[0m")
        print("ai-sleep-guard can manage lid-closed sleep prevention seamlessly.")
        return

    # Attempt to write if currently running as root, or provide the exact command
    if os.geteuid() == 0:
        try:
            with open(sudoers_path, "w", encoding="utf-8") as f:
                f.write(sudoers_rule)
            os.chmod(sudoers_path, 0o440)
            print(f"\033[92m● Successfully wrote configuration to {sudoers_path}\033[0m")
        except Exception as e:
            print(f"Failed to write {sudoers_path}: {e}")
    else:
        print("To enable lid-close sleep prevention without typing your password every time,")
        print("run the following single command in Terminal:")
        print()
        print(f'  echo "{sudoers_rule.strip()}" | sudo tee {sudoers_path} > /dev/null && sudo chmod 0440 {sudoers_path}')
        print()
        print("After running this, ai-sleep-guard will manage clamshell mode automatically!")
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
    print("Manual sleep prevention ENABLED. Screen and system will stay awake.")


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
        description="Prevents Mac sleep while AI agents run prompts, with thermal safety and lid-close support."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # daemon
    daemon_parser = subparsers.add_parser("daemon", help="Run the background sleep guard daemon")
    daemon_parser.add_argument("--poll-interval", type=float, default=2.5, help="Poll interval in seconds (default: 2.5)")
    daemon_parser.add_argument("--cooldown", type=float, default=45.0, help="Idle cooldown buffer in seconds (default: 45.0)")
    daemon_parser.add_argument("--no-clamshell", action="store_true", help="Disable lid-closed sleep prevention")

    # status
    subparsers.add_parser("status", help="Show current live status of detectors, thermal guard, and assertions")

    # thermal
    subparsers.add_parser("thermal", help="Show detailed thermal state and CPU throttling diagnostics")

    # setup-sudo
    subparsers.add_parser("setup-sudo", help="Configure passwordless pmset sudoers for lid-close sleep guard")

    # ping
    ping_parser = subparsers.add_parser("ping", help="Record an active prompt turn for an agent")
    ping_parser.add_argument("agent", choices=["antigravity", "claude", "codex", "custom"], help="Agent identifier")

    # done
    done_parser = subparsers.add_parser("done", help="Clear active turn signal for an agent")
    done_parser.add_argument("agent", choices=["antigravity", "claude", "codex", "custom"], help="Agent identifier")

    # on
    subparsers.add_parser("on", help="Manually force screen and system awake")

    # off
    subparsers.add_parser("off", help="Release manual force awake")

    # wrap
    wrap_parser = subparsers.add_parser("wrap", help="Wrap a command to keep system awake while it runs")
    wrap_parser.add_argument("--agent", choices=["antigravity", "claude", "codex"], default="claude", help="Agent name")
    wrap_parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute")

    args = parser.parse_args()

    if args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "thermal":
        cmd_thermal(args)
    elif args.command == "setup-sudo":
        cmd_setup_sudo(args)
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
        cmd_status(args)


if __name__ == "__main__":
    main()
