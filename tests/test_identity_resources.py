from __future__ import annotations

import json

import pytest
from fastmcp import Client

from mcp_agent_mail.app import build_mcp_server


@pytest.mark.asyncio
async def test_whois_and_projects_resources(isolated_env):
    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/backend"})
        await client.call_tool(
            "register_agent",
            {"project_key": "Backend", "program": "codex", "model": "gpt-5", "name": "BlueLake", "task_description": "dir"},
        )

        who = await client.call_tool(
            "whois",
            {"project_key": "Backend", "agent_name": "BlueLake"},
        )
        assert who.data.get("name") == "BlueLake"
        assert who.data.get("program") == "codex"

        # Projects list
        blocks = await client.read_resource("resource://projects")
        assert blocks and "backend" in (blocks[0].text or "")

        # Project detail
        blocks2 = await client.read_resource("resource://project/backend")
        assert blocks2 and "BlueLake" in (blocks2[0].text or "")


@pytest.mark.asyncio
async def test_register_agent_accepts_freeform_names(isolated_env):
    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/backend"})
        result = await client.call_tool(
            "register_agent",
            {
                "project_key": "Backend",
                "program": "codex",
                "model": "gpt-5",
                "name": "Backend-Harmonizer!!",
            },
        )
        stored = result.data or {}
        assert stored.get("name") == "BackendHarmonizer"

        who = await client.call_tool(
            "whois",
            {"project_key": "Backend", "agent_name": "BackendHarmonizer"},
        )
        assert who.data.get("name") == "BackendHarmonizer"


@pytest.mark.asyncio
async def test_project_resource_hides_inactive_agents(isolated_env):
    server = build_mcp_server()
    async with Client(server) as client:
        backend_key = "/backend"
        other_key = "/other"
        backend = await client.call_tool("ensure_project", {"human_key": backend_key})
        await client.call_tool("ensure_project", {"human_key": other_key})

        # Active agent in backend
        await client.call_tool(
            "register_agent",
            {"project_key": backend_key, "program": "codex", "model": "gpt-5", "name": "BlueLake"},
        )

        # Register Convo in backend, then reclaim in other project to retire the backend copy
        await client.call_tool(
            "register_agent",
            {"project_key": backend_key, "program": "codex", "model": "gpt-5", "name": "Convo"},
        )
        await client.call_tool(
            "register_agent",
            {"project_key": other_key, "program": "codex", "model": "gpt-5", "name": "Convo"},
        )

        slug = backend.data.get("slug", "backend")
        blocks = await client.read_resource(f"resource://project/{slug}")
        assert blocks, "project resource returned no blocks"
        payload = json.loads(blocks[0].text or "{}")
        names = [agent.get("name") for agent in payload.get("agents", [])]
        assert "BlueLake" in names
        assert "Convo" not in names, "Inactive agent was returned by project resource"


@pytest.mark.asyncio
async def test_register_agent_auto_creates_project(isolated_env):
    """Test that register_agent automatically creates project if it doesn't exist."""
    server = build_mcp_server()
    async with Client(server) as client:
        # Register agent without calling ensure_project first
        result = await client.call_tool(
            "register_agent",
            {
                "project_key": "auto-created-project",
                "program": "claude-code",
                "model": "opus-4.1",
                "name": "TestAgent1",
                "task_description": "Testing auto-create",
            },
        )

        stored = result.data or {}
        assert stored.get("name") == "TestAgent1"
        assert stored.get("program") == "claude-code"
        assert stored.get("model") == "opus-4.1"
        assert stored.get("task_description") == "Testing auto-create"
        assert stored.get("project_id") is not None

        # Verify the project was created
        who = await client.call_tool(
            "whois",
            {"project_key": "auto-created-project", "agent_name": "TestAgent1"},
        )
        assert who.data.get("name") == "TestAgent1"


@pytest.mark.asyncio
async def test_register_agent_accepts_any_project_key_string(isolated_env):
    """Test that register_agent accepts any string as project_key and auto-creates it."""
    server = build_mcp_server()
    async with Client(server) as client:
        test_keys = [
            "/absolute/path/to/project",
            "simple-project-name",
            "Project With Spaces",
            "/tmp/test-123",
            "my_repo_v2",
        ]

        for idx, project_key in enumerate(test_keys):
            agent_name = f"Agent{idx}"
            result = await client.call_tool(
                "register_agent",
                {
                    "project_key": project_key,
                    "program": "test-program",
                    "model": "test-model",
                    "name": agent_name,
                },
            )

            stored = result.data or {}
            assert stored.get("name") == agent_name
            assert stored.get("project_id") is not None

            # Verify via whois
            who = await client.call_tool(
                "whois",
                {"project_key": project_key, "agent_name": agent_name},
            )
            assert who.data.get("name") == agent_name


@pytest.mark.asyncio
async def test_register_agent_idempotent_with_ensure_project(isolated_env):
    """Test that calling ensure_project before register_agent still works (backward compatibility)."""
    server = build_mcp_server()
    async with Client(server) as client:
        # Explicitly create project first
        project_result = await client.call_tool("ensure_project", {"human_key": "explicit-project"})
        project_id = project_result.data.get("id")

        # Register agent (should use existing project)
        agent_result = await client.call_tool(
            "register_agent",
            {
                "project_key": "explicit-project",
                "program": "test-prog",
                "model": "test-model",
                "name": "ExplicitAgent",
            },
        )

        stored = agent_result.data or {}
        assert stored.get("name") == "ExplicitAgent"
        # Should use the same project_id from ensure_project
        assert stored.get("project_id") == project_id


@pytest.mark.asyncio
async def test_register_agent_same_slug_different_human_keys(isolated_env):
    """Test that different human_keys that normalize to same slug use same project."""
    server = build_mcp_server()
    async with Client(server) as client:
        # These should all normalize to the same slug
        result1 = await client.call_tool(
            "register_agent",
            {
                "project_key": "My-Project",
                "program": "prog1",
                "model": "model1",
                "name": "Agent1",
            },
        )

        result2 = await client.call_tool(
            "register_agent",
            {
                "project_key": "my-project",  # Same slug, different case
                "program": "prog2",
                "model": "model2",
                "name": "Agent2",
            },
        )

        # Both agents should be in the same project
        assert result1.data.get("project_id") == result2.data.get("project_id")

        # Verify both agents exist in the same project
        who1 = await client.call_tool(
            "whois",
            {"project_key": "My-Project", "agent_name": "Agent1"},
        )
        who2 = await client.call_tool(
            "whois",
            {"project_key": "my-project", "agent_name": "Agent2"},
        )

        assert who1.data.get("name") == "Agent1"
        assert who2.data.get("name") == "Agent2"


@pytest.mark.asyncio
async def test_delete_agent_basic(isolated_env):
    """Test basic agent deletion."""
    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test"})
        
        # Register an agent
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "TestAgent"},
        )
        
        # Verify agent exists
        who = await client.call_tool(
            "whois",
            {"project_key": "Test", "agent_name": "TestAgent"},
        )
        assert who.data.get("name") == "TestAgent"
        
        # Delete the agent
        result = await client.call_tool(
            "delete_agent",
            {"project_key": "Test", "name": "TestAgent"},
        )
        
        # Verify deletion stats
        stats = result.data
        assert stats.get("agent_name") == "TestAgent"
        
        # Verify agent no longer exists
        with pytest.raises(Exception):  # Should raise error when agent doesn't exist
            await client.call_tool(
                "whois",
                {"project_key": "Test", "agent_name": "TestAgent"},
            )


@pytest.mark.asyncio
async def test_delete_agent_with_messages(isolated_env):
    """Test deleting an agent that has sent and received messages."""
    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test"})
        
        # Register two agents
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "Sender"},
        )
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "Receiver"},
        )
        
        # Send messages from Sender to Receiver
        await client.call_tool(
            "send_message",
            {
                "project_key": "Test",
                "sender_name": "Sender",
                "to": ["Receiver"],
                "subject": "Test Message 1",
                "body_md": "Hello from sender",
            },
        )
        await client.call_tool(
            "send_message",
            {
                "project_key": "Test",
                "sender_name": "Sender",
                "to": ["Receiver"],
                "subject": "Test Message 2",
                "body_md": "Another message",
            },
        )
        
        # Send a message from Receiver to Sender
        await client.call_tool(
            "send_message",
            {
                "project_key": "Test",
                "sender_name": "Receiver",
                "to": ["Sender"],
                "subject": "Reply",
                "body_md": "Hello back",
            },
        )
        
        # Delete the Sender agent
        result = await client.call_tool(
            "delete_agent",
            {"project_key": "Test", "name": "Sender"},
        )
        
        # Verify deletion stats include messages and recipients
        stats = result.data
        assert stats.get("agent_name") == "Sender"
        assert stats.get("messages_deleted") == 2  # Two messages sent by Sender
        assert stats.get("message_recipients_deleted") >= 2  # At least recipients of those messages
        
        # Verify Sender no longer exists
        with pytest.raises(Exception):
            await client.call_tool(
                "whois",
                {"project_key": "Test", "agent_name": "Sender"},
            )
        
        # Verify Receiver still exists and can be queried
        who = await client.call_tool(
            "whois",
            {"project_key": "Test", "agent_name": "Receiver"},
        )
        assert who.data.get("name") == "Receiver"


@pytest.mark.asyncio
async def test_delete_agent_with_agent_links(isolated_env):
    """Test deleting an agent that has agent links (contacts)."""
    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test"})
        
        # Register three agents
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "Agent1"},
        )
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "Agent2"},
        )
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "Agent3"},
        )
        
        # Create agent links using request_contact and respond_contact
        # Agent1 requests contact with Agent2
        await client.call_tool(
            "request_contact",
            {"project_key": "Test", "requester_name": "Agent1", "target_name": "Agent2"},
        )
        await client.call_tool(
            "respond_contact",
            {"project_key": "Test", "responder_name": "Agent2", "requester_name": "Agent1", "action": "approve"},
        )
        
        # Agent1 requests contact with Agent3
        await client.call_tool(
            "request_contact",
            {"project_key": "Test", "requester_name": "Agent1", "target_name": "Agent3"},
        )
        await client.call_tool(
            "respond_contact",
            {"project_key": "Test", "responder_name": "Agent3", "requester_name": "Agent1", "action": "approve"},
        )
        
        # Delete Agent1
        result = await client.call_tool(
            "delete_agent",
            {"project_key": "Test", "name": "Agent1"},
        )
        
        # Verify deletion stats include agent links
        stats = result.data
        assert stats.get("agent_name") == "Agent1"
        assert stats.get("agent_links_deleted") >= 2  # At least the two contacts
        
        # Verify Agent1 no longer exists
        with pytest.raises(Exception):
            await client.call_tool(
                "whois",
                {"project_key": "Test", "agent_name": "Agent1"},
            )
        
        # Verify Agent2 and Agent3 still exist
        who2 = await client.call_tool(
            "whois",
            {"project_key": "Test", "agent_name": "Agent2"},
        )
        assert who2.data.get("name") == "Agent2"
        
        who3 = await client.call_tool(
            "whois",
            {"project_key": "Test", "agent_name": "Agent3"},
        )
        assert who3.data.get("name") == "Agent3"


@pytest.mark.asyncio
async def test_delete_agent_cascading_deletes(isolated_env):
    """Test that deleting an agent properly cascades to all related records."""
    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test"})
        
        # Register two agents
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "Alice"},
        )
        await client.call_tool(
            "register_agent",
            {"project_key": "Test", "program": "codex", "model": "gpt-5", "name": "Bob"},
        )
        
        # Alice sends messages to Bob
        for i in range(3):
            await client.call_tool(
                "send_message",
                {
                    "project_key": "Test",
                    "sender_name": "Alice",
                    "to": ["Bob"],
                    "subject": f"Message {i}",
                    "body_md": f"Content {i}",
                },
            )
        
        # Bob sends messages to Alice
        for i in range(2):
            await client.call_tool(
                "send_message",
                {
                    "project_key": "Test",
                    "sender_name": "Bob",
                    "to": ["Alice"],
                    "subject": f"Reply {i}",
                    "body_md": f"Reply content {i}",
                },
            )
        
        # Create bidirectional contact relationship
        await client.call_tool(
            "request_contact",
            {"project_key": "Test", "requester_name": "Alice", "target_name": "Bob"},
        )
        await client.call_tool(
            "respond_contact",
            {"project_key": "Test", "responder_name": "Bob", "requester_name": "Alice", "action": "approve"},
        )
        
        # Delete Alice
        result = await client.call_tool(
            "delete_agent",
            {"project_key": "Test", "name": "Alice"},
        )
        
        # Verify all related records were deleted
        stats = result.data
        assert stats.get("agent_name") == "Alice"
        assert stats.get("messages_deleted") == 3  # Alice sent 3 messages
        # MessageRecipient: 3 records for Alice's messages to Bob + 2 records where Alice was recipient of Bob's messages
        assert stats.get("message_recipients_deleted") >= 5
        assert stats.get("agent_links_deleted") >= 1  # At least the Alice-Bob contact
        
        # Verify Alice no longer exists
        with pytest.raises(Exception):
            await client.call_tool(
                "whois",
                {"project_key": "Test", "agent_name": "Alice"},
            )
        
        # Verify Bob still exists and can access his messages
        who_bob = await client.call_tool(
            "whois",
            {"project_key": "Test", "agent_name": "Bob"},
        )
        assert who_bob.data.get("name") == "Bob"

