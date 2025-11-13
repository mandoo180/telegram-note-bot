# Cloud Server Troubleshooting Guide

This guide helps diagnose and fix issues when running the Telegram Note bot on a cloud server.

## Quick Diagnostic Script

Upload and run the `check_reminders.py` script on your cloud server:

```bash
# On your cloud server
cd /path/to/telegram-note
python3 check_reminders.py
```

This will show you:
- Pending reminders status
- Timezone configuration
- Bot process status
- Recommendations

## Common Issues

### 1. Reminders Not Firing

**Symptoms:**
- Bot is running but reminders don't send
- No error messages in logs

**Causes & Solutions:**

#### A. Bot Not Running Continuously
```bash
# Check if bot is running
ps aux | grep "python.*main.py"

# If not running, start it
nohup python3 src/main.py > bot.log 2>&1 &

# Verify it started
tail -f bot.log
```

**Best Practice:** Use a process manager like systemd or supervisor:

```bash
# Create systemd service
sudo tee /etc/systemd/system/telegram-note.service > /dev/null <<EOF
[Unit]
Description=Telegram Note Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/telegram-note
Environment="PATH=/path/to/telegram-note/venv/bin"
ExecStart=/path/to/telegram-note/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable telegram-note
sudo systemctl start telegram-note

# Check status
sudo systemctl status telegram-note

# View logs
sudo journalctl -u telegram-note -f
```

#### B. Timezone Issues (FIXED in latest version)
The bot now correctly handles timezones using `datetime('now', 'localtime')`.

**To verify timezone:**
```bash
# Check server timezone
timedatectl

# Should show your local timezone (e.g., Asia/Seoul)
# If wrong, set it:
sudo timedatectl set-timezone Asia/Seoul
```

**Check database times:**
```bash
sqlite3 telegram_note.db "SELECT datetime('now') as utc, datetime('now', 'localtime') as local"
```

#### C. Scheduler Not Running
```bash
# Check logs for scheduler startup
grep -i "scheduler\|reminder" bot.log

# Should see:
# - "Scheduler started"
# - "Reminder service started"
# - "Loaded pending reminder for schedule X at Y"
```

If you don't see these messages:
1. Check for errors in `bot.log`
2. Verify APScheduler is installed: `pip show apscheduler`
3. Restart the bot

#### D. Reminders in the Past
```bash
# Check reminder times
sqlite3 telegram_note.db "
SELECT s.name, s.start_datetime, r.reminder_time,
       datetime('now', 'localtime') as current_time
FROM schedules s
JOIN reminders r ON s.id = r.schedule_id
WHERE r.sent = FALSE
ORDER BY r.reminder_time"
```

If `reminder_time < current_time`, the reminder won't fire because it's in the past.

**Solution:** Create a new schedule with a reminder time in the future.

### 2. Bot Crashes or Restarts

**Check logs:**
```bash
tail -100 bot.log | grep -i error
```

**Common causes:**
- Out of memory
- Network issues
- Database locked
- Missing dependencies

**Solutions:**
```bash
# Check memory
free -h

# Check disk space
df -h

# Reinstall dependencies
pip install -r requirements.txt

# Check database integrity
sqlite3 telegram_note.db "PRAGMA integrity_check"
```

### 3. Web App Not Accessible

**Check if web server is running:**
```bash
netstat -tlnp | grep :8000

# Or
lsof -i :8000
```

**Check if ngrok/tunnel is running:**
```bash
ps aux | grep ngrok

# If using ngrok
curl http://localhost:4040/api/tunnels | jq
```

**Verify WEBAPP_BASE_URL in .env:**
```bash
grep WEBAPP_BASE_URL .env

# Should be your public HTTPS URL
# Example: https://abc123.ngrok.io
```

### 4. Database Issues

**Backup before troubleshooting:**
```bash
cp telegram_note.db telegram_note.db.backup.$(date +%Y%m%d)
```

**Check database:**
```bash
# Open database
sqlite3 telegram_note.db

# Check tables
.tables

# Check reminders
SELECT * FROM reminders;

# Check schedules
SELECT * FROM schedules;

# Exit
.quit
```

**Fix corrupted database:**
```bash
# Dump and restore
sqlite3 telegram_note.db ".dump" | sqlite3 telegram_note_fixed.db
mv telegram_note.db telegram_note_broken.db
mv telegram_note_fixed.db telegram_note.db
```

## Testing Reminders

Create a test reminder that fires in 2 minutes:

1. **Create a test schedule:**
   ```
   /schedule test-reminder
   ```

2. **Fill in the form:**
   - Title: Test Reminder
   - Start time: (current time + 3 minutes)
   - End time: (current time + 4 minutes)
   - Reminder: 1 minute before

3. **Monitor logs:**
   ```bash
   tail -f bot.log | grep -i reminder
   ```

4. **You should see:**
   - `Scheduled reminder for schedule test-reminder at YYYY-MM-DD HH:MM`
   - (After 2 minutes) `Sent reminder for schedule test-reminder to user XXXXX`

## Monitoring

### Real-time Logs
```bash
# All logs
tail -f bot.log

# Only reminders
tail -f bot.log | grep -i reminder

# Errors only
tail -f bot.log | grep -i error
```

### System Health
```bash
# CPU and memory
top -bn1 | grep python

# Process status
ps aux | grep python.*main.py

# Network
netstat -tlnp | grep python
```

### Check Upcoming Reminders
```bash
python3 check_reminders.py
```

## Performance Tips

1. **Log Rotation:**
```bash
# Rotate logs daily
cat > /etc/logrotate.d/telegram-note <<EOF
/path/to/telegram-note/bot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

2. **Database Maintenance:**
```bash
# Vacuum database periodically
sqlite3 telegram_note.db "VACUUM"

# Clean old reminders
sqlite3 telegram_note.db "DELETE FROM reminders WHERE sent = TRUE AND sent_at < datetime('now', '-30 days')"
```

3. **Resource Limits:**
```bash
# Check limits
ulimit -a

# Increase if needed (in systemd service)
[Service]
LimitNOFILE=4096
LimitNPROC=512
```

## Getting Help

If issues persist:

1. **Collect diagnostic info:**
   ```bash
   python3 check_reminders.py > diagnostic.txt
   tail -100 bot.log >> diagnostic.txt
   timedatectl >> diagnostic.txt
   ```

2. **Check GitHub issues:** https://github.com/YOUR_REPO/issues

3. **Include in your report:**
   - Output of `check_reminders.py`
   - Relevant log excerpts
   - Server timezone and OS
   - Steps to reproduce

## Quick Reference

```bash
# Start bot
nohup python3 src/main.py > bot.log 2>&1 &

# Stop bot
pkill -f "python.*main.py"

# Restart bot
pkill -f "python.*main.py" && sleep 2 && nohup python3 src/main.py > bot.log 2>&1 &

# Check status
ps aux | grep "python.*main.py" && tail -5 bot.log

# View recent logs
tail -50 bot.log

# Check reminders
python3 check_reminders.py

# Database backup
cp telegram_note.db telegram_note.db.backup

# Test reminder (create schedule with 2-minute reminder)
/schedule test && (wait 2 minutes)
```
