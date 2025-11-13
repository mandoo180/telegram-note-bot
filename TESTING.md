# Testing the Web App Note Editor

This guide will help you test the Web App note editor functionality.

## Prerequisites

1. **ngrok installed** - Download from https://ngrok.com/
2. **Bot token configured** in `.env` file
3. **Database initialized** - Run `python init_db.py`

## Setup Steps

### 1. Start ngrok

Open a terminal and run:
```bash
ngrok http 8000
```

You should see output like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

### 2. Update .env file

Edit your `.env` file and set:
```
WEBAPP_BASE_URL=https://abc123.ngrok-free.app
```

Replace with your actual ngrok URL.

### 3. Start the bot

In another terminal:
```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python src/main.py
```

You should see:
```
WebApp server started on http://0.0.0.0:8000
Bot commands registered for auto-completion
Starting Telegram Note bot...
Application started
```

## Testing the Web App

### 1. Create a new note

1. Open Telegram and find your bot
2. Send: `/note test-note`
3. You should see a message with a button "📝 Edit Note"
4. Click the button
5. A Web App should open in Telegram

### 2. Edit the note

In the Web App editor:
1. **Title field**: Enter "My First Note"
2. **Tags field**: Enter "test, personal"
3. **Content field**: Type some content with Markdown:
   ```
   This is **bold** and this is *italic*

   # Heading
   - List item 1
   - List item 2
   ```
4. Watch the preview update in real-time

### 3. Save the note

1. Click the **"Save Note"** button at the bottom
2. The Web App should close
3. You should see a success message in the chat:
   ```
   ✅ Note saved successfully!

   📝 My First Note
   🏷 Tags: test, personal

   (content preview...)
   ```

### 4. Verify the note was saved

1. Send: `/notes`
2. You should see your note listed
3. Send: `/note test-note` again
4. The editor should open with your saved content

## Troubleshooting

### Save button does nothing

Check the bot logs for errors:
```bash
# Look for lines containing "Received Web App data" or errors
```

Common issues:
- **ngrok URL not set**: Make sure `WEBAPP_BASE_URL` in `.env` is correct
- **ngrok not running**: ngrok terminal should show requests
- **Bot not restarted**: Restart the bot after changing `.env`

### Web App doesn't open

- Check that ngrok is running and URL is HTTPS
- Verify `WEBAPP_BASE_URL` is set correctly in `.env`
- Check bot logs for "WebApp server started"

### Getting "Invalid data" error

- Check bot logs for JSON parsing errors
- Look for the "Raw data:" log line to see what was received

## Debug Mode

To see detailed logs, check the bot output. You should see:
```
INFO - Received Web App data for note 'test-note' from user 123456
DEBUG - Data: title=My First Note, tags=test,personal, content_len=89
INFO - Note 'test-note' saved successfully for user 123456 via Web App
```

## Testing Without ngrok

If you want to test without Web App:

1. Don't set up ngrok
2. Use text-based editing instead:
   ```
   /note test-note
   My Title | tag1,tag2 | This is the content
   ```

The bot will work fine, just without the rich editor UI.
