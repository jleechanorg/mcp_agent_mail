# Slack Integration for MCP Agent Mail

Full bidirectional integration between MCP Agent Mail and Slack, enabling agents to send notifications, post messages, and sync communications with Slack channels.

## Table of Contents

- [Features](#features)
- [Setup](#setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [MCP Tools](#mcp-tools)
- [Automatic Notifications](#automatic-notifications)
- [Webhook Integration](#webhook-integration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Features

### ✅ Implemented

- **Outbound Notifications**: Automatically send Slack notifications when MCP messages are created
- **Manual Slack Posting**: Use MCP tools to post messages to any Slack channel
- **Channel Discovery**: List and get information about available Slack channels
- **Thread Mapping**: Map MCP message threads to Slack threads for conversation continuity
- **Rich Formatting**: Support for Slack Block Kit for enhanced message presentation
- **Webhook Endpoint**: Receive and verify Slack events for future bidirectional sync

### 🚧 Future Enhancements

- Full bidirectional sync: Create MCP messages from Slack messages
- Reaction-based acknowledgments: Mark messages as read via Slack reactions
- User mention mapping: Map Slack users to MCP agents
- File attachments: Sync file uploads between Slack and MCP

## Setup

### 1. Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Name your app (e.g., "MCP Agent Mail")
4. Select your workspace

### 2. Configure OAuth & Permissions

1. Navigate to **"OAuth & Permissions"**
2. Add the following **Bot Token Scopes**:
   - `chat:write` - Post messages to channels
   - `chat:write.public` - Post to public channels without joining
   - `channels:read` - List public channels
   - `groups:read` - List private channels
   - `files:write` - Upload files (optional)
   - `reactions:write` - Add reactions (optional)
3. Click **"Install to Workspace"**
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### 3. Get Signing Secret

1. Navigate to **"Basic Information"**
2. Under **"App Credentials"**, copy the **Signing Secret**

### 4. Configure Event Subscriptions (Optional for Bidirectional Sync)

1. Navigate to **"Event Subscriptions"**
2. Enable Events
3. Set **Request URL** to: `https://your-server.com/slack/events`
4. Subscribe to bot events:
   - `message.channels` - Messages in public channels
   - `message.groups` - Messages in private channels
   - `reaction_added` - Reactions to messages
5. Save Changes

### 5. Invite Bot to Channels

Invite your bot to the channels where you want it to post:

```
/invite @MCP Agent Mail
```

## Configuration

Add the following to your `.env` file:

```bash
# Enable Slack Integration
SLACK_ENABLED=true

# Slack API Credentials
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Default channel for notifications (channel name or ID)
SLACK_DEFAULT_CHANNEL=general

# Notification Settings
SLACK_NOTIFY_ON_MESSAGE=true
SLACK_NOTIFY_ON_ACK=false
SLACK_NOTIFY_MENTION_FORMAT=agent_name

# Advanced Features
SLACK_USE_BLOCKS=true
SLACK_INCLUDE_ATTACHMENTS=true

# Bidirectional Sync (Future)
SLACK_SYNC_ENABLED=false
SLACK_SYNC_CHANNELS=
SLACK_SYNC_THREAD_REPLIES=true
SLACK_SYNC_REACTIONS=true
```

### Configuration Options

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SLACK_ENABLED` | boolean | `false` | Enable/disable Slack integration |
| `SLACK_BOT_TOKEN` | string | - | Bot User OAuth Token (required) |
| `SLACK_APP_TOKEN` | string | - | App-Level Token for Socket Mode (optional) |
| `SLACK_SIGNING_SECRET` | string | - | Signing secret for webhook verification |
| `SLACK_DEFAULT_CHANNEL` | string | `general` | Default channel for notifications |
| `SLACK_NOTIFY_ON_MESSAGE` | boolean | `true` | Send notification when MCP message is created |
| `SLACK_NOTIFY_ON_ACK` | boolean | `false` | Send notification when message is acknowledged |
| `SLACK_NOTIFY_MENTION_FORMAT` | string | `agent_name` | How to format agent mentions (`agent_name`, `real_name`, `display_name`) |
| `SLACK_SYNC_ENABLED` | boolean | `false` | Enable bidirectional message sync |
| `SLACK_SYNC_CHANNELS` | string | - | Comma-separated channel IDs to sync |
| `SLACK_SYNC_THREAD_REPLIES` | boolean | `true` | Sync Slack threads to MCP thread_id |
| `SLACK_SYNC_REACTIONS` | boolean | `true` | Use Slack reactions for acknowledgments |
| `SLACK_USE_BLOCKS` | boolean | `true` | Use Block Kit for rich formatting |
| `SLACK_INCLUDE_ATTACHMENTS` | boolean | `true` | Include MCP attachments in Slack posts |
| `SLACK_WEBHOOK_URL` | string | - | Legacy incoming webhook URL (optional) |

## Usage

### Restart the Server

After configuring Slack, restart the MCP Agent Mail server:

```bash
./scripts/run_server_with_token.sh
```

You should see in the logs:

```
Slack integration initialized successfully
```

## MCP Tools

### `slack_post_message`

Post a message to a Slack channel.

**Parameters:**
- `channel` (string, required): Channel ID or name (e.g., `"general"` or `"C1234567890"`)
- `text` (string, required): Message text (supports Slack mrkdwn formatting)
- `thread_ts` (string, optional): Thread timestamp to reply in a specific thread

**Returns:**
```json
{
  "ok": true,
  "channel": "C1234567890",
  "ts": "1503435956.000247",
  "permalink": "https://example.slack.com/archives/C1234567890/p1503435956000247"
}
```

**Example:**
```python
# Post a simple message
slack_post_message(
    channel="general",
    text="🚀 Deployment to production completed successfully!"
)

# Reply in a thread
slack_post_message(
    channel="C1234567890",
    text="Review completed, looks good!",
    thread_ts="1503435956.000247"
)
```

### `slack_list_channels`

List all Slack channels the bot has access to.

**Returns:**
```json
{
  "channels": [
    {
      "id": "C1234567890",
      "name": "general",
      "is_private": false,
      "is_archived": false,
      "num_members": 42
    }
  ],
  "count": 10
}
```

**Example:**
```python
result = slack_list_channels()
for channel in result["channels"]:
    print(f"#{channel['name']} - {channel['num_members']} members")
```

### `slack_get_channel_info`

Get detailed information about a specific channel.

**Parameters:**
- `channel` (string, required): Channel ID or name

**Returns:**
```json
{
  "id": "C1234567890",
  "name": "general",
  "is_private": false,
  "topic": "General discussion",
  "purpose": "Company-wide announcements",
  "num_members": 42
}
```

**Example:**
```python
info = slack_get_channel_info(channel="general")
print(f"Topic: {info['topic']}")
```

## Automatic Notifications

When `SLACK_NOTIFY_ON_MESSAGE=true`, MCP Agent Mail automatically sends a Slack notification whenever a new message is created.

### Notification Format

Notifications use Slack Block Kit for rich formatting:

```
┌─────────────────────────────────────────────┐
│ 📧 Deploy Status Update                     │
├─────────────────────────────────────────────┤
│ From: BlueWhale                             │
│ To: GreenCastle, RedFox                     │
│ Message ID: abc12345                        │
├─────────────────────────────────────────────┤
│ Production deployment completed at 14:30    │
│ UTC. All services are healthy.              │
│                                             │
│ Next steps:                                 │
│ - Monitor logs for 1 hour                   │
│ - Update status page                        │
└─────────────────────────────────────────────┘
```

### Thread Continuity

When an MCP message has a `thread_id`, the Slack notification is posted as a reply in the corresponding Slack thread, maintaining conversation context.

### Importance Indicators

Messages are tagged with emoji based on importance:

- 🚨 **urgent**: Critical issues
- ❗ **high**: Important updates
- 📧 **normal**: Regular messages
- ℹ️ **low**: Informational

## Webhook Integration

The Slack webhook endpoint at `/slack/events` handles inbound events from Slack.

### Supported Events

- **URL Verification**: Automatic challenge response during app setup
- **Message Events**: Logged and ready for future bidirectional sync
- **Reaction Events**: Logged for future acknowledgment tracking

### Signature Verification

All webhook requests are verified using HMAC-SHA256 signature validation to ensure they originate from Slack. Requests with invalid signatures are rejected with HTTP 401.

### Testing the Webhook

1. Use Slack's Event Subscriptions URL validator
2. Or test with curl:

```bash
curl -X POST http://localhost:8765/slack/events \
  -H "Content-Type: application/json" \
  -d '{"type": "url_verification", "challenge": "test123"}'
```

Response:
```json
{"challenge": "test123"}
```

## Examples

### Example 1: Notify Team of Build Failure

```python
# Create MCP message (automatically notifies Slack)
send_message(
    project_key="myproject",
    agent_name="BlueWhale",
    to=["GreenCastle"],
    subject="Build Failed: main branch",
    body_md="Build #1234 failed on main branch.\n\nError: Unit tests failed in auth module.",
    importance="urgent"
)
```

Slack notification appears in the default channel with 🚨 indicator.

### Example 2: Manual Slack Post

```python
# Post directly to Slack without creating MCP message
slack_post_message(
    channel="deployments",
    text="✅ Production deployment successful\n\n*Duration*: 5m 32s\n*Version*: v2.1.0"
)
```

### Example 3: Thread Conversation

```python
# Start a conversation
result = slack_post_message(
    channel="code-reviews",
    text="Review request for PR #456"
)

thread_ts = result["ts"]

# Reply in thread
slack_post_message(
    channel="code-reviews",
    text="LGTM! Approved.",
    thread_ts=thread_ts
)
```

### Example 4: Discover Channels

```python
# List all channels
channels = slack_list_channels()

# Find a specific channel
dev_channel = next(
    (ch for ch in channels["channels"] if ch["name"] == "development"),
    None
)

if dev_channel:
    # Post to that channel
    slack_post_message(
        channel=dev_channel["id"],
        text="Hello from MCP Agent Mail!"
    )
```

## Troubleshooting

### Issue: "Slack integration is not enabled"

**Solution:** Ensure `SLACK_ENABLED=true` in your `.env` file and restart the server.

### Issue: "Failed to initialize Slack integration"

**Cause:** Missing or invalid `SLACK_BOT_TOKEN`.

**Solution:**
1. Verify your bot token starts with `xoxb-`
2. Check the token hasn't expired
3. Ensure the token has the required scopes
4. Check server logs for specific error messages

### Issue: "channel_not_found" error

**Cause:** Bot doesn't have access to the channel.

**Solution:**
1. Invite the bot to the channel: `/invite @YourBotName`
2. Or use the channel ID instead of name
3. For private channels, ensure the bot is a member

### Issue: Notifications not appearing

**Checklist:**
- [ ] `SLACK_ENABLED=true`
- [ ] `SLACK_NOTIFY_ON_MESSAGE=true`
- [ ] Valid `SLACK_BOT_TOKEN`
- [ ] Bot invited to `SLACK_DEFAULT_CHANNEL`
- [ ] Server restarted after config changes

### Issue: Webhook verification fails

**Cause:** Invalid signing secret or timestamp issues.

**Solution:**
1. Verify `SLACK_SIGNING_SECRET` matches your app's signing secret
2. Check server time is synchronized (NTP)
3. Ensure webhook requests are reaching the server within 5 minutes

### Debug Logging

Enable detailed logging to troubleshoot issues:

```bash
LOG_LEVEL=DEBUG
TOOLS_LOG_ENABLED=true
```

Check logs for Slack-specific messages:

```bash
grep -i slack /tmp/mcp_agent_mail_server.log
```

## Security Considerations

1. **Keep Tokens Secret**: Never commit `SLACK_BOT_TOKEN` to version control
2. **Use Signing Secret**: Always configure `SLACK_SIGNING_SECRET` for webhook security
3. **Restrict Permissions**: Grant only necessary OAuth scopes to your bot
4. **Monitor Usage**: Review Slack app analytics for unusual activity
5. **Rotate Tokens**: Periodically regenerate tokens as a security best practice

## Architecture

### Components

```
┌──────────────────────────────────────────────────────────┐
│                   MCP Agent Mail Server                   │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ app.py                                              │  │
│  │  - Message delivery hook → notify_slack_message()  │  │
│  │  - Slack MCP tools registration                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                           ↓                                │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ slack_integration.py                                │  │
│  │  - SlackClient (async API wrapper)                 │  │
│  │  - Message formatting helpers                      │  │
│  │  - Thread mapping utilities                        │  │
│  │  - Signature verification                          │  │
│  └─────────────────────────────────────────────────────┘  │
│                           ↓                                │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ http.py                                             │  │
│  │  - POST /slack/events (webhook handler)            │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                           ↕
                    Slack Web API
                    Slack Events API
```

### Data Flow

**Outbound (MCP → Slack):**
```
MCP send_message() → _deliver_message() → notify_slack_message()
  → SlackClient.post_message() → Slack API
```

**Inbound (Slack → MCP):**
```
Slack Events → /slack/events webhook → verify_signature()
  → [Future: create MCP message]
```

## FAQ

**Q: Can I use this with Slack Connect for cross-workspace messaging?**

A: Yes, if your Slack app has Slack Connect permissions and the bot is added to shared channels.

**Q: Does this work with Slack threads?**

A: Yes! MCP message threads are mapped to Slack threads automatically when `thread_id` is provided.

**Q: Can I customize the notification format?**

A: Yes, modify `format_mcp_message_for_slack()` in `slack_integration.py` to customize Block Kit formatting.

**Q: What's the rate limit for Slack API calls?**

A: Slack has a Tier 1 rate limit of ~1 request per second per workspace. The client uses async operations to respect these limits.

**Q: Can I post to multiple channels simultaneously?**

A: Yes, call `slack_post_message()` multiple times with different channels, or configure channel-specific routing logic.

**Q: How do I disable Slack integration temporarily?**

A: Set `SLACK_ENABLED=false` in `.env` and restart the server.

## Contributing

To extend the Slack integration:

1. **Add new tools**: Define new `@mcp.tool` functions in `app.py`
2. **Enhance formatting**: Update `format_mcp_message_for_slack()` in `slack_integration.py`
3. **Implement bidirectional sync**: Add event handlers in the `/slack/events` webhook
4. **Add tests**: Create test cases in `tests/test_slack_integration.py`

## Support

For issues or questions:

- Check the [Troubleshooting](#troubleshooting) section
- Review server logs for error details
- File an issue at the project repository
- Consult [Slack API documentation](https://api.slack.com/docs)

---

**Last Updated:** 2025-11-05
**Version:** 1.0.0
**Status:** Production Ready ✅
