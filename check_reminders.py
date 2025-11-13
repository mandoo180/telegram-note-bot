#!/usr/bin/env python3
"""Diagnostic script to check reminder service status."""

import sys
import sqlite3
from datetime import datetime

def check_reminders():
    """Check reminder status and scheduling."""
    print("=" * 60)
    print("REMINDER SERVICE DIAGNOSTIC")
    print("=" * 60)

    # Check database
    conn = sqlite3.connect('telegram_note.db')
    cursor = conn.cursor()

    print("\n1. DATABASE STATUS:")
    print("-" * 60)

    # Get pending reminders
    cursor.execute("""
        SELECT r.id, s.user_id, s.name, s.title,
               s.start_datetime, r.reminder_time, r.sent,
               datetime('now', 'localtime') as current_local
        FROM reminders r
        JOIN schedules s ON r.schedule_id = s.id
        WHERE r.sent = FALSE
        ORDER BY r.reminder_time
    """)

    pending = cursor.fetchall()

    if not pending:
        print("❌ No pending reminders found")
    else:
        print(f"✅ Found {len(pending)} pending reminder(s):\n")

        current_time = datetime.now()
        for row in pending:
            rid, user_id, name, title, start, reminder_time, sent, current_local = row
            reminder_dt = datetime.fromisoformat(reminder_time)
            time_diff = (reminder_dt - current_time).total_seconds()
            hours = int(time_diff // 3600)
            minutes = int((time_diff % 3600) // 60)

            print(f"  Reminder ID: {rid}")
            print(f"  Schedule: {name} - {title}")
            print(f"  User ID: {user_id}")
            print(f"  Start time: {start}")
            print(f"  Reminder time: {reminder_time}")

            if time_diff > 0:
                print(f"  ✅ Will fire in: {hours}h {minutes}m")
            else:
                print(f"  ❌ PAST DUE by: {-hours}h {-minutes}m")
            print()

    # Check timezone info
    print("\n2. TIMEZONE INFORMATION:")
    print("-" * 60)
    cursor.execute("SELECT datetime('now') as utc, datetime('now', 'localtime') as local")
    utc, local = cursor.fetchone()
    print(f"SQLite UTC time:   {utc}")
    print(f"SQLite local time: {local}")
    print(f"Python local time: {datetime.now()}")

    # Check for timezone mismatch
    print("\n3. TIMEZONE ISSUE CHECK:")
    print("-" * 60)
    cursor.execute("""
        SELECT COUNT(*)
        FROM reminders r
        WHERE r.sent = FALSE
          AND r.reminder_time > datetime('now')
          AND r.reminder_time <= datetime('now', 'localtime')
    """)
    mismatch_count = cursor.fetchone()[0]

    if mismatch_count > 0:
        print(f"⚠️  WARNING: {mismatch_count} reminder(s) affected by timezone mismatch!")
        print("   The code uses datetime('now') which is UTC.")
        print("   But datetimes are stored in local timezone.")
        print("   This causes incorrect comparisons.")
    else:
        print("✅ No timezone mismatch detected")

    conn.close()

    # Check bot process
    print("\n4. BOT PROCESS STATUS:")
    print("-" * 60)
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'python.*src/main.py'],
                          capture_output=True, text=True)
    if result.stdout:
        print(f"✅ Bot is running (PID: {result.stdout.strip()})")
    else:
        print("❌ Bot is NOT running!")

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)

    if pending:
        has_future = any(datetime.fromisoformat(row[5]) > datetime.now() for row in pending)
        if has_future:
            print("✅ Reminder service appears to be working correctly")
            print("   Future reminders are scheduled and should fire on time")
        else:
            print("⚠️  All reminders are in the past - they won't fire")
            print("   Create a new schedule with a reminder in the future to test")
    else:
        print("ℹ️  No reminders to check - create a schedule with a reminder")

    print("\n")

if __name__ == '__main__':
    try:
        check_reminders()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
