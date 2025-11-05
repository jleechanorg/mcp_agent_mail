# MCP Agent Mail - Comprehensive Codebase Overview

## Project Summary

**mcp_agent_mail** is a FastMCP (Model Context Protocol) HTTP-only server designed to coordinate asynchronous communication between multiple coding agents. It acts as a shared mailbox/directory system enabling agents (Claude Code, Codex, Gemini CLI, etc.) to communicate, reserve files, and track progress without conflicts.

### Key Statistics
- **Total Lines of Code**: ~16,800 (primarily in app.py)
- **Language**: Python 3.14+ (async-first)
- **Framework**: FastMCP 2.10.5+
- **Architecture**: HTTP-only (no STDIO/SSE)
- **Database**: SQLite or PostgreSQL (SQLModel + SQLAlchemy ORM)
- **Storage**: Git-backed archive with markdown messages
- **Status**: Active development (Phase 2 lazy loading in progress)

---

## High-Level Architecture

```
┌──────────────────────────────┐
│   Coding Agents (CLI Tools)  │
│  - Claude Code               │
│  - Codex CLI                 │
│  - Gemini CLI                │
│  - Others                    │
└────────────────┬─────────────┘
                 │ HTTP (FastMCP)
                 │
┌────────────────▼─────────────────────────────┐
│      MCP Agent Mail Server                   │
│  - Tool Execution Engine                    │
│  - Resource Discovery                       │
│  - Message Routing & Delivery               │
│  - File Reservation Management              │
│  - Lazy Tool Loading (Phase 2)              │
└────────────────┬─────────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
┌─────▼──────────┐   ┌──────▼──────────┐
│   SQLite/      │   │  Per-Project    │
│   PostgreSQL   │   │  Git Archives   │
│                │   │  (Markdown      │
│  - Agents      │   │   Messages)     │
│  - Messages    │   │                 │
│  - Contacts    │   │  - agents/*/    │
│  - Leases      │   │  - messages/    │
│  - Links       │   │  - file_res/    │
└────────────────┘   └─────────────────┘
```

---

## Directory Structure

```
/home/user/mcp_agent_mail/
├── src/mcp_agent_mail/
│   ├── __main__.py           # Entry point
│   ├── app.py               # Main FastMCP server (310KB, 7000+ lines)
│   ├── config.py            # Settings/env loading (decouple-based)
│   ├── http.py              # HTTP/ASGI transport layer
│   ├── db.py                # Database initialization
│   ├── models.py            # SQLModel data definitions
│   ├── storage.py           # Git archive + attachment handling
│   ├── llm.py               # LiteLLM integration (summarization)
│   ├── guard.py             # Pre-commit hook installation
│   ├── cli.py               # CLI command interface
│   ├── rich_logger.py       # Rich console logging
│   ├── utils.py             # Utility helpers
│   ├── templates/           # HTML/Jinja2 templates
│   └── viewer_assets/       # Web UI static assets
├── tests/                   # Comprehensive test suite (90+ files)
├── scripts/                 # Helper scripts
├── docs/                    # Documentation
├── roadmap/                 # Phase planning
├── pyproject.toml          # Project metadata & dependencies
├── .env.example            # Configuration template
└── README.md               # Main documentation
```

---

## Core Data Models (SQLModel)

Located in: `/home/user/mcp_agent_mail/src/mcp_agent_mail/models.py`

### Project
```python
class Project(SQLModel, table=True):
    id: Optional[int]           # Primary key
    slug: str                   # Unique identifier (e.g., "/abs/path/backend")
    human_key: str              # Display name
    created_at: datetime        # Registration time
```

### Agent
```python
class Agent(SQLModel, table=True):
    id: Optional[int]
    project_id: int             # Foreign key to Project
    name: str                   # Agent identity (e.g., "GreenCastle", "RedCat")
    program: str                # Tool name (e.g., "Claude Code", "Codex")
    model: str                  # Model name (e.g., "Opus 4.1", "GPT-5")
    task_description: str       # What the agent is working on
    inception_ts: datetime      # Registration time
    last_active_ts: datetime    # Last message/activity time
    attachments_policy: str     # "auto" | "inline" | "file"
    contact_policy: str         # "open" | "auto" | "contacts_only" | "block_all"
```

### Message
```python
class Message(SQLModel, table=True):
    id: Optional[int]
    project_id: int             # Foreign key
    sender_id: int              # Foreign key to Agent
    thread_id: Optional[str]    # Thread grouping
    subject: str                # Message subject
    body_md: str                # GitHub-Flavored Markdown body
    importance: str             # "low" | "normal" | "high" | "urgent"
    ack_required: bool          # Requires acknowledgment
    created_ts: datetime
    attachments: list[dict]     # JSON metadata for images/files
```

### MessageRecipient
```python
class MessageRecipient(SQLModel, table=True):
    message_id: int             # Foreign key
    agent_id: int               # Foreign key
    kind: str                   # "to" | "cc" | "bcc"
    read_ts: Optional[datetime] # When recipient read it
    ack_ts: Optional[datetime]  # When recipient acknowledged
```

### FileReservation (Leases)
```python
class FileReservation(SQLModel, table=True):
    id: Optional[int]
    project_id: int
    agent_id: int
    path_pattern: str           # Glob pattern (e.g., "app/api/*.py")
    exclusive: bool             # Can other agents touch?
    reason: str                 # Why agent reserved this
    created_ts: datetime
    expires_ts: datetime        # TTL lease expiration
    released_ts: Optional[datetime]  # When manually released
```

### AgentLink (Cross-Project Contact)
```python
class AgentLink(SQLModel, table=True):
    # Directed request from agent A → agent B
    a_project_id: int
    a_agent_id: int
    b_project_id: int
    b_agent_id: int
    status: str                 # "pending" | "approved" | "blocked"
    expires_ts: Optional[datetime]  # Contact TTL
```

---

## Tool Clusters & Organization

The codebase organizes tools into **7 semantic clusters** for lazy loading and discovery:

### 1. **CLUSTER_SETUP** (Infrastructure)
- `health_check` - Server readiness probe
- `ensure_project` - Create/initialize project
- `list_extended_tools` - Discover available tools (Phase 2)
- `call_extended_tool` - Invoke extended tools dynamically (Phase 2)

### 2. **CLUSTER_IDENTITY** (Agent Management)
- `register_agent` - Create agent identity
- `whois` - Look up agent details
- `create_agent_identity` - Auto-generate memorable names

### 3. **CLUSTER_MESSAGING** (Core Communication)
- `send_message` - Send markdown message to agents
- `reply_message` - Reply in a thread
- `fetch_inbox` - Get unread messages
- `mark_message_read` - Update read status
- `acknowledge_message` - Signal task completion

### 4. **CLUSTER_CONTACT** (Contact Management)
- `request_contact` - Ask permission to communicate
- `respond_contact` - Approve/deny contact requests
- `list_contacts` - Get approved contacts
- `set_contact_policy` - Configure communication rules
- `macro_contact_handshake` - Auto-approve workflows

### 5. **CLUSTER_SEARCH** (Message Discovery)
- `search_messages` - Full-text search with FTS5
- `summarize_thread` - LLM-powered thread summary
- `summarize_threads` - Bulk thread summaries

### 6. **CLUSTER_FILE_RESERVATIONS** (Concurrency Control)
- `file_reservation_paths` - Reserve file patterns
- `release_file_reservations` - Release leases
- `force_release_file_reservation` - Admin override
- `renew_file_reservations` - Extend TTL

### 7. **CLUSTER_MACROS** (Workflow Automation)
- `macro_start_session` - Initialize multi-agent workflow
- `macro_prepare_thread` - Set up thread context
- `macro_file_reservation_cycle` - Full lease workflow
- `macro_contact_handshake` - Contact request workflow

### Resources (Read-Only Discovery)
- `resource://config/environment` - Server configuration
- `resource://tooling/directory` - Registered agents
- `resource://tooling/schemas` - Tool metadata
- `resource://tooling/metrics` - Performance stats
- `resource://projects` - All projects
- `resource://agents/{project_key}` - Agents in project
- `resource://mailbox/{agent}` - Agent inbox view
- `resource://outbox/{agent}` - Agent outbox view
- `resource://thread/{thread_id}` - Thread view

---

## Key Architectural Patterns

### 1. Tool Registration & Instrumentation

All tools use a consistent decorator pattern:

```python
@mcp.tool(name="tool_name", description="...")
@_instrument_tool(
    "tool_name",
    cluster=CLUSTER_MESSAGING,           # Logical grouping
    capabilities={"messaging"},          # Permission scopes
    complexity="medium",                 # low|medium|high
    agent_arg="agent_name",              # Param name for agent
    project_arg="project_key"            # Param name for project
)
async def tool_name(ctx: Context, ...) -> dict[str, Any]:
    """Tool implementation with async/await."""
    pass
```

**Key aspects:**
- All tools are async functions
- Accept `ctx: Context` for logging/error reporting
- Return `dict[str, Any]` as JSON-serializable payload
- Instrumentation layer handles:
  - Metrics tracking
  - Capability enforcement (RBAC)
  - Tool usage logging
  - Recent tool history
  - Error recording

### 2. Message Delivery Flow

```
send_message() → _deliver_message() → _create_message() + write_message_bundle()
      ↓                                           ↓
   Input validation                     1. Create DB records
   Contact enforcement                  2. Process attachments
   File reservation checking            3. Write canonical .md
                                        4. Write per-agent inbox/outbox
                                        5. Git commit + push
                                        6. Return payload
```

The `_deliver_message` function (lines 2023-2194) is the core:
- Validates recipients exist
- Enforces contact policies
- Checks file reservation conflicts
- Processes markdown & images
- Creates DB message + MessageRecipient records
- Persists to Git archive
- Returns structured delivery payload

### 3. Storage Architecture (Dual Persistence)

**Database (SQLite/PostgreSQL):**
- Metadata queries (agent lookup, message search, contact links)
- FTS5 full-text search over message bodies
- Indexed queries for performance
- Thread management

**Git Archive:**
- Human-auditable markdown message files
- Per-agent inbox/outbox directory structure
- File reservation records (JSON)
- Automatic commits on every write
- Supports diffing, blame, and history review

**Hybrid benefits:**
```
~/.mcp_agent_mail_git_mailbox_repo/
└── projects/
    └── backend_repo/
        ├── agents/
        │   ├── GreenCastle/
        │   │   ├── profile.json        # Agent metadata
        │   │   ├── inbox/
        │   │   │   └── 2025/11/
        │   │   │       └── msg_123.md
        │   │   └── outbox/
        │   │       └── 2025/11/
        │   │           └── msg_456.md
        │   └── RedCat/
        │       └── ...
        ├── messages/                    # Canonical copies
        │   └── 2025/11/
        │       ├── msg_123.md
        │       └── msg_456.md
        └── file_reservations/           # Lease records
            └── abc123.json
```

### 4. Configuration & Settings

Located in: `/home/user/mcp_agent_mail/src/mcp_agent_mail/config.py`

Settings are loaded from `.env` using `python-decouple`:

```python
from decouple import Config as DecoupleConfig, RepositoryEnv
_decouple_config = DecoupleConfig(RepositoryEnv(".env"))

# Inside Settings:
http: HttpSettings          # Host, port, path, bearer token, rate limiting, JWT
database: DatabaseSettings  # SQLite/PostgreSQL URL
storage: StorageSettings    # Git repo root, author name/email
cors: CorsSettings          # CORS enablement
llm: LlmSettings            # LiteLLM model, temperature, caching
# + 20+ boolean/int toggles for features
```

Key environment variables for Slack integration:
```bash
# You could add:
SLACK_INTEGRATION_ENABLED=true
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_CHANNEL_MAPPING=/path/backend:backend-team,/path/frontend:frontend-team
```

### 5. Error Handling & Reporting

Custom exception type: `ToolExecutionError`

```python
raise ToolExecutionError(
    error_type="CONTACT_BLOCKED",           # Machine-readable code
    message="Recipient not accepting messages",  # Human-readable
    recoverable=True,                       # Can caller retry?
    data={"required": [...], "allowed": [...]}  # Structured context
)
```

Tools can also use `ctx.error()` for logging:
```python
await ctx.error("MESSAGE_SEND_FAILED: See details above")
```

---

## Existing Integration: No External Communication Channels

**Current reality:**
- MCP Agent Mail is **entirely self-contained**
- Messages are stored in SQLite + Git only
- **No email integration** (no SMTP, no webhooks)
- **No Slack integration** (no Slack API client)
- **No Discord/Matrix/etc.** 
- **No push notifications**

**Design philosophy:**
Messages are pulled asynchronously via `fetch_inbox`, not pushed. Agents decide when to check for messages as part of their workflow.

---

## Adding Slack Integration: Recommended Patterns

### Option A: Outbound-Only (Simpler)
**When a message is sent in MCP Agent Mail → notify Slack channel**

**Implementation points:**
1. Add Slack configuration to `config.py`:
   ```python
   @dataclass(slots=True, frozen=True)
   class SlackSettings:
       enabled: bool
       bot_token: str | None
       signing_secret: str | None
       channel_mapping: dict[str, str]  # project_slug → slack_channel
       message_sync_enabled: bool
   ```

2. Create new module: `src/mcp_agent_mail/slack_integration.py`
   ```python
   from slack_sdk import WebClient
   
   class SlackNotifier:
       def __init__(self, settings: SlackSettings):
           self.client = WebClient(token=settings.bot_token)
       
       async def notify_message_sent(
           self, 
           project: Project, 
           message: Message, 
           sender: Agent
       ) -> None:
           """Post message to Slack channel after MCP message sent."""
           # Format message for Slack
           # Post to mapped channel
   ```

3. Hook into `_deliver_message` after successful write:
   ```python
   # In app.py, after write_message_bundle():
   if get_settings().slack.enabled:
       await SlackNotifier(...).notify_message_sent(...)
   ```

4. Add to `.env.example`:
   ```bash
   SLACK_INTEGRATION_ENABLED=false
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_SIGNING_SECRET=...
   SLACK_CHANNEL_MAPPING={"/abs/path/backend": "backend-team"}
   ```

### Option B: Bidirectional (Complex)
**Slack messages ↔ MCP Agent Mail messages**

**Additional components:**
1. **Slack Event Handler** (FastAPI endpoint)
   - Webhook endpoint at `/webhooks/slack/events`
   - Verify Slack request signature
   - Convert Slack messages to MCP Message records

2. **Thread Mapping**
   - Slack thread ID ↔ MCP thread ID mapping table
   - Maintain synchronization

3. **User Mapping**
   - Slack user IDs ↔ Agent names
   - Configure in `SLACK_USER_MAPPING`

---

## Development Workflow & Best Practices

### Running the Server
```bash
# Start background server with logging
bash -lc "./scripts/run_server_with_token.sh >/tmp/mcp_agent_mail_server.log 2>&1 & echo \$!"
# Output: <PID>

# Monitor logs
tail -f /tmp/mcp_agent_mail_server.log

# Stop server
kill <PID>
```

### Adding a New Tool

1. **Define in app.py** (after ~line 2000):
   ```python
   @mcp.tool(name="my_tool", description="...")
   @_instrument_tool("my_tool", cluster=CLUSTER_MESSAGING, ...)
   async def my_tool(
       ctx: Context,
       project_key: str,
       agent_name: str,
       **kwargs
   ) -> dict[str, Any]:
       """Docstring with extensive parameter/return documentation."""
       try:
           # Implementation
           project = await _get_project_by_identifier(project_key)
           agent = await _get_agent(project, agent_name)
           # ... business logic ...
           await ctx.info("Operation successful")
           return {"status": "success", ...}
       except Exception as e:
           await ctx.error(f"OPERATION_FAILED: {str(e)}")
           raise ToolExecutionError(...) from e
   ```

2. **Register in cluster mapping** at tool definition (decorator)

3. **Add to EXTENDED_TOOLS constant** if applicable:
   ```python
   EXTENDED_TOOLS = [
       # ... existing ...
       "my_tool",
   ]
   ```

4. **Update EXTENDED_TOOL_METADATA**:
   ```python
   EXTENDED_TOOL_METADATA["my_tool"] = {
       "cluster": CLUSTER_MESSAGING,
       "complexity": "medium",
       "category": "custom",
   }
   ```

5. **Write tests** in `tests/test_my_tool.py`:
   ```python
   @pytest.mark.asyncio
   async def test_my_tool():
       # Setup
       # Call tool
       # Assert
   ```

6. **Test locally**:
   ```bash
   pytest tests/test_my_tool.py -v
   ```

### Code Style & Conventions

**From pyproject.toml:**
- Line length: 120 characters
- Python 3.14+ with strict typing (mypy)
- Ruff linting (E, W, F, B, I, C4, ASYNC, A, RUF, SIM, PTH, FA)
- Async-first (no blocking I/O in async context)
- Always use `await` for async operations
- Use SQLModel + SQLAlchemy ORM patterns

**Type hints required:**
```python
async def function_name(
    ctx: Context,
    param1: str,
    param2: Optional[int] = None,
) -> dict[str, Any]:
    """Always include docstring."""
    pass
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_messaging.py -v

# Run with coverage
pytest --cov=mcp_agent_mail

# Run slow tests
pytest tests/ -m "slow" -v
```

Test patterns in codebase:
- Use `conftest.py` for fixtures (temporary projects, agents, messages)
- Mock FastMCP Context with `AsyncMock`
- Use `pytest-asyncio` for async test support
- Always clean up test data (Git repos, DB records)

---

## Phase 2: Lazy Loading (Current Work)

The codebase is currently implementing **lazy tool loading** to reduce token overhead:

**Status:**
- ✅ Phase 1: Tool categorization foundation (merged)
- 🔄 Phase 2: Meta-tools for discovery & invocation (in progress)
- ⏳ Phase 3: Client-side tool registry caching (planned)

**Current state:**
- `CORE_TOOLS`: 8 essential tools (~10k tokens)
- `EXTENDED_TOOLS`: 19 additional tools (~25k tokens)
- Mode toggle: `MCP_TOOLS_MODE=core|extended` in `.env`

**Phase 2 tools to implement:**
- `list_extended_tools` - Discover available extended tools
- `call_extended_tool` - Dynamically invoke extended tools
- Registry population logic

See: `/home/user/mcp_agent_mail/roadmap/PHASE_2_PROMPT.md`

---

## Configuration Reference

Key `.env` variables for understanding the system:

```bash
# HTTP Server
HTTP_HOST=127.0.0.1
HTTP_PORT=8765
HTTP_PATH=/mcp/
HTTP_BEARER_TOKEN=<auto-generated>

# Database
DATABASE_URL=sqlite+aiosqlite:///./storage.sqlite3
# Or: postgresql+asyncpg://user:pass@localhost/dbname

# Storage / Git
STORAGE_ROOT=~/.mcp_agent_mail_git_mailbox_repo
GIT_AUTHOR_NAME=mcp-agent
GIT_AUTHOR_EMAIL=mcp-agent@example.com

# Messaging
MESSAGING_AUTO_REGISTER_RECIPIENTS=true
MESSAGING_AUTO_HANDSHAKE_ON_BLOCK=true

# Contact Policies
CONTACT_ENFORCEMENT_ENABLED=false
CONTACT_AUTO_TTL_SECONDS=86400

# File Reservations (Leases)
FILE_RESERVATIONS_ENFORCEMENT_ENABLED=true
FILE_RESERVATION_INACTIVITY_SECONDS=1800

# Tool Configuration
MCP_TOOLS_MODE=extended  # or "core"
TOOLS_LOG_ENABLED=true

# LLM (for summarization)
LLM_ENABLED=true
LLM_DEFAULT_MODEL=gpt-4-turbo
```

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | ~7,000 | Core FastMCP server, all tools & resources |
| `models.py` | ~117 | SQLModel data definitions |
| `storage.py` | ~1,300 | Git archive, attachment processing |
| `config.py` | ~331 | Settings loading from `.env` |
| `http.py` | ~3,300 | FastAPI/ASGI transport, auth, rate limiting |
| `db.py` | ~265 | Database initialization, migrations |
| `llm.py` | ~260 | LiteLLM integration for summarization |
| `cli.py` | ~1,500 | Command-line interface |

---

## Common Development Tasks

### Add a new configuration option
1. Add to `Settings` dataclass in `config.py`
2. Add to `get_settings()` function with `_decouple_config(...)`
3. Update `.env.example`
4. Use in code: `get_settings().new_option`

### Add a new tool
1. Implement function in `app.py` with `@mcp.tool` decorator
2. Add `@_instrument_tool` decorator with cluster
3. Add to `EXTENDED_TOOLS` constant if not core
4. Update `EXTENDED_TOOL_METADATA` (Phase 2)
5. Write tests in `tests/`
6. Document parameters/returns thoroughly

### Modify database schema
1. Update SQLModel in `models.py`
2. Database schema auto-migrates via `ensure_schema()`
3. Add test case if adding new relationships

### Debug a tool issue
1. Check server logs: `tail /tmp/mcp_agent_mail_server.log`
2. Enable rich logging: `LOG_RICH_ENABLED=true`
3. Enable JSON logging: `LOG_JSON_ENABLED=true`
4. Add `await ctx.info()` / `await ctx.error()` calls
5. Check tool instrumentation metrics: `resource://tooling/metrics`

---

## Summary: Slack Integration Starting Points

For a Slack integration, the recommended approach is:

1. **Create `src/mcp_agent_mail/slack_integration.py`** with:
   - `SlackSettings` config dataclass
   - `SlackNotifier` async class for message posting
   - `SlackEventHandler` for webhook processing (optional)

2. **Update `config.py`**:
   - Add `slack: SlackSettings` to `Settings`
   - Add slack env var parsing to `get_settings()`

3. **Hook into message flow**:
   - After successful `_deliver_message()`, notify Slack
   - Or create new tool `sync_to_slack` for manual sync

4. **Add HTTP endpoint** (optional):
   - FastAPI route in `http.py` for Slack webhooks
   - Verify Slack request signature
   - Convert Slack messages to MCP messages

5. **Follow existing patterns**:
   - Use SQLModel for any new DB tables
   - Use `@_instrument_tool` for any new tools
   - Async/await throughout
   - Comprehensive error handling
   - Extensive docstrings

The codebase is well-structured, well-tested, and has clear separation of concerns. Add Slack integration as a **loosely-coupled module** that hooks into the existing message delivery pipeline.

