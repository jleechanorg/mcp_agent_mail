# Lazy Loading MCP Tools - Foundation

## Overview

MCP Agent Mail exposes 27 tools consuming ~25k tokens by default. This categorization provides the foundation for future lazy loading to reduce context usage to ~10k tokens.

## Tool Categories

### Core Tools (8 tools, ~9k tokens)
Essential for basic coordination:
- `health_check` - Server readiness check
- `ensure_project` - Create/verify project  
- `register_agent` - Register agent identity
- `whois` - Get agent profile info
- `send_message` - Send markdown messages
- `reply_message` - Reply to messages
- `fetch_inbox` - Get recent messages
- `mark_message_read` - Mark messages as read

### Extended Tools (19 tools, ~16k tokens)
Advanced features for specialized workflows:

**Messaging**: `acknowledge_message`

**Search**: `search_messages`, `summarize_thread`, `summarize_threads`

**Identity**: `create_agent_identity`

**Contacts**: `request_contact`, `respond_contact`, `list_contacts`, `set_contact_policy`

**File Reservations**: `file_reservation_paths`, `release_file_reservations`, `force_release_file_reservation`, `renew_file_reservations`

**Macros**: `macro_start_session`, `macro_prepare_thread`, `macro_file_reservation_cycle`, `macro_contact_handshake`

**Infrastructure**: `install_precommit_guard`, `uninstall_precommit_guard`

## Current Implementation

### What's Included (v2 - Meta-Tools)

✅ **Tool Categorization**: Constants define core vs extended tools
✅ **Metadata**: Each extended tool has category and description
✅ **Tool Registry**: `_EXTENDED_TOOL_REGISTRY` populated with all extended tools
✅ **Meta-Tools**: `list_extended_tools` and `call_extended_tool` implemented
✅ **Environment Variable**: `MCP_TOOLS_MODE` support added (behavior in Phase 3)
✅ **Integration Tests**: Comprehensive test suite for lazy loading functionality
✅ **Zero Breaking Changes**: All 29 tools remain functional (27 original + 2 meta)

### What's Not Yet Implemented

⚠️ **Conditional Registration**: Runtime tool filtering based on `MCP_TOOLS_MODE` (Phase 3)
⚠️ **Actual Context Savings**: Requires conditional registration implementation
⚠️ **FastMCP Enhancement**: May need custom filtering or upstream contribution

## Context Reduction Potential

| Mode | Tools Exposed | Approx Tokens | Savings |
|------|--------------|---------------|---------|
| Extended (current) | 29 tools (27 + 2 meta) | ~25k | - |
| Core (Phase 3) | 8 core + 2 meta = 10 tools | ~10k | **60%** |

**Note**: Meta-tools are available now, but conditional registration (Phase 3) is required to achieve actual context savings.

## Roadmap

### Phase 1: Foundation (Current)
- ✅ Tool categorization constants
- ✅ Metadata for discovery
- ✅ Registry placeholder

### Phase 2: Meta-Tools (Complete ✅)
- ✅ Implement `list_extended_tools`
- ✅ Implement `call_extended_tool`
- ✅ Add environment variable support (`MCP_TOOLS_MODE`)
- ✅ Integration tests
- ✅ Populate `_EXTENDED_TOOL_REGISTRY`

### Phase 3: Runtime Filtering (Next)
- [ ] Research FastMCP tool registration capabilities
- [ ] Implement conditional tool registration based on `MCP_TOOLS_MODE`
- [ ] FastMCP enhancement or workaround implementation
- [ ] Full context savings validation
- [ ] Performance benchmarks for both modes

## Design Decisions

**Why Constants First?**
- Documents the categorization
- Zero risk to production
- Enables gradual implementation
- Allows discussion before behavior changes

**Why These Categories?**
- Core = minimum viable agent coordination
- Extended = specialized/advanced workflows
- Categorization based on usage patterns from real deployments

**Why Not Filter Now?**
- Requires FastMCP runtime filtering or decorator refactoring
- Meta-tools provide value independently
- Foundation enables experimentation

## Usage

### Listing Extended Tools

Use the `list_extended_tools` tool to discover available extended tools:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "list_extended_tools",
    "arguments": {}
  }
}
```

Returns:
```json
{
  "total": 19,
  "by_category": {
    "messaging": ["acknowledge_message"],
    "search": ["search_messages", "summarize_thread", "summarize_threads"],
    "identity": ["create_agent_identity"],
    "contact": ["request_contact", "respond_contact", "list_contacts", "set_contact_policy"],
    "file_reservations": ["file_reservation_paths", "release_file_reservations", "force_release_file_reservation", "renew_file_reservations"],
    "workflow_macros": ["macro_start_session", "macro_prepare_thread", "macro_file_reservation_cycle", "macro_contact_handshake"],
    "infrastructure": ["install_precommit_guard", "uninstall_precommit_guard"]
  },
  "tools": [
    {"name": "acknowledge_message", "category": "messaging", "description": "Acknowledge a message (sets both read_ts and ack_ts)"},
    ...
  ]
}
```

### Calling Extended Tools

Use the `call_extended_tool` tool to invoke extended tools dynamically:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "call_extended_tool",
    "arguments": {
      "tool_name": "acknowledge_message",
      "arguments": {
        "project_key": "/data/projects/backend",
        "agent_name": "BackendDev",
        "message_id": 42
      }
    }
  }
}
```

### Environment Variable

Set `MCP_TOOLS_MODE` to control tool exposure (Phase 3 implementation required):

```bash
# Default: all tools exposed
export MCP_TOOLS_MODE=extended

# Future: only core tools + meta-tools (Phase 3)
export MCP_TOOLS_MODE=core
```

## Related Work

- GitHub Issue: anthropics/claude-code#7336
- Community POC: github.com/machjesusmoto/claude-lazy-loading
- Discussion: Lazy loading as MCP protocol enhancement

## For Contributors

This foundation enables multiple implementation paths:

1. **Meta-Tool Approach**: Expose extended tools via proxy tools
2. **Decorator Refactoring**: Conditional `@mcp.tool` registration
3. **Post-Registration Filtering**: Remove tools after FastMCP init
4. **FastMCP Enhancement**: Runtime tool exposure control

The constants in `app.py` serve as the source of truth for all approaches.

---

**Status**: Foundation complete, meta-tools pending
**Risk**: Zero (additive only, no behavior changes)
**Impact**: Documents categorization, enables future work
