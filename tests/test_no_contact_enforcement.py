"""Test that contact enforcement has been removed and messaging works without approval."""

from __future__ import annotations

import contextlib

import pytest
from fastmcp import Client

from mcp_agent_mail import config as _config
from mcp_agent_mail.app import build_mcp_server


@pytest.mark.asyncio
async def test_direct_messaging_without_contact_approval(isolated_env, monkeypatch):
    """Test that agents can send messages directly without contact approval."""
    # Ensure contact enforcement is disabled (default)
    monkeypatch.setenv("CONTACT_ENFORCEMENT_ENABLED", "false")
    with contextlib.suppress(Exception):
        _config.clear_settings_cache()

    server = build_mcp_server()
    async with Client(server) as client:
        # Create project and register two agents
        await client.call_tool("ensure_project", {"human_key": "/test-project"})

        for name in ("AgentA", "AgentB"):
            await client.call_tool(
                "register_agent",
                {
                    "project_key": "/test-project",
                    "program": "pytest",
                    "model": "test-model",
                    "name": name,
                },
            )

        # AgentA should be able to send message to AgentB without any contact approval
        result = await client.call_tool(
            "send_message",
            {
                "project_key": "/test-project",
                "sender_name": "AgentA",
                "to": ["AgentB"],
                "subject": "Test message",
                "body_md": "This should work without contact approval",
            },
        )

        assert result is not None
        assert result["count"] == 1
        assert len(result["deliveries"]) == 1

        # Verify AgentB received the message
        inbox = await client.call_tool(
            "fetch_inbox",
            {
                "project_key": "/test-project",
                "agent_name": "AgentB",
                "limit": 10,
            },
        )

        assert len(inbox) == 1
        assert inbox[0]["subject"] == "Test message"
        assert inbox[0]["sender"] == "AgentA"


@pytest.mark.asyncio
async def test_messaging_with_contacts_only_policy_ignored(isolated_env, monkeypatch):
    """Test that contacts_only policy is ignored and messaging works anyway."""
    monkeypatch.setenv("CONTACT_ENFORCEMENT_ENABLED", "false")
    with contextlib.suppress(Exception):
        _config.clear_settings_cache()

    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test-project"})

        for name in ("AgentA", "AgentB"):
            await client.call_tool(
                "register_agent",
                {
                    "project_key": "/test-project",
                    "program": "pytest",
                    "model": "test-model",
                    "name": name,
                },
            )

        # Set AgentB's policy to contacts_only (should be ignored)
        await client.call_tool(
            "set_contact_policy",
            {
                "project_key": "/test-project",
                "agent_name": "AgentB",
                "policy": "contacts_only",
            },
        )

        # AgentA should still be able to message AgentB without approval
        result = await client.call_tool(
            "send_message",
            {
                "project_key": "/test-project",
                "sender_name": "AgentA",
                "to": ["AgentB"],
                "subject": "Testing policy bypass",
                "body_md": "This should work despite contacts_only policy",
            },
        )

        assert result is not None
        assert result["count"] == 1

        # Verify message was delivered
        inbox = await client.call_tool(
            "fetch_inbox",
            {
                "project_key": "/test-project",
                "agent_name": "AgentB",
                "limit": 10,
            },
        )

        assert len(inbox) == 1
        assert inbox[0]["subject"] == "Testing policy bypass"


@pytest.mark.asyncio
async def test_messaging_with_block_all_policy_ignored(isolated_env, monkeypatch):
    """Test that block_all policy is ignored and messaging works anyway."""
    monkeypatch.setenv("CONTACT_ENFORCEMENT_ENABLED", "false")
    with contextlib.suppress(Exception):
        _config.clear_settings_cache()

    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test-project"})

        for name in ("AgentA", "AgentB"):
            await client.call_tool(
                "register_agent",
                {
                    "project_key": "/test-project",
                    "program": "pytest",
                    "model": "test-model",
                    "name": name,
                },
            )

        # Set AgentB's policy to block_all (should be ignored)
        await client.call_tool(
            "set_contact_policy",
            {
                "project_key": "/test-project",
                "agent_name": "AgentB",
                "policy": "block_all",
            },
        )

        # AgentA should still be able to message AgentB
        result = await client.call_tool(
            "send_message",
            {
                "project_key": "/test-project",
                "sender_name": "AgentA",
                "to": ["AgentB"],
                "subject": "Testing block_all bypass",
                "body_md": "This should work despite block_all policy",
            },
        )

        assert result is not None
        assert result["count"] == 1

        # Verify message was delivered
        inbox = await client.call_tool(
            "fetch_inbox",
            {
                "project_key": "/test-project",
                "agent_name": "AgentB",
                "limit": 10,
            },
        )

        assert len(inbox) == 1
        assert inbox[0]["subject"] == "Testing block_all bypass"


@pytest.mark.asyncio
async def test_cross_project_messaging_without_approval(isolated_env, monkeypatch):
    """Test that cross-project messaging works without contact approval."""
    monkeypatch.setenv("CONTACT_ENFORCEMENT_ENABLED", "false")
    with contextlib.suppress(Exception):
        _config.clear_settings_cache()

    server = build_mcp_server()
    async with Client(server) as client:
        # Create two projects
        await client.call_tool("ensure_project", {"human_key": "/project-a"})
        await client.call_tool("ensure_project", {"human_key": "/project-b"})

        # Register agents in different projects
        await client.call_tool(
            "register_agent",
            {
                "project_key": "/project-a",
                "program": "pytest",
                "model": "test-model",
                "name": "AgentA",
            },
        )

        await client.call_tool(
            "register_agent",
            {
                "project_key": "/project-b",
                "program": "pytest",
                "model": "test-model",
                "name": "AgentB",
            },
        )

        # AgentA should be able to message AgentB across projects without approval
        result = await client.call_tool(
            "send_message",
            {
                "project_key": "/project-a",
                "sender_name": "AgentA",
                "to": ["project:project-b#AgentB"],
                "subject": "Cross-project message",
                "body_md": "This should work without contact approval",
            },
        )

        assert result is not None
        # Should have external delivery
        assert "deliveries" in result

        # Verify AgentB received the message
        inbox = await client.call_tool(
            "fetch_inbox",
            {
                "project_key": "/project-b",
                "agent_name": "AgentB",
                "limit": 10,
            },
        )

        assert len(inbox) == 1
        assert inbox[0]["subject"] == "Cross-project message"
        assert inbox[0]["sender"] == "AgentA"


@pytest.mark.asyncio
async def test_contact_tools_still_work_but_not_required(isolated_env, monkeypatch):
    """Test that contact tools still work for backward compatibility but aren't required."""
    monkeypatch.setenv("CONTACT_ENFORCEMENT_ENABLED", "false")
    with contextlib.suppress(Exception):
        _config.clear_settings_cache()

    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test-project"})

        for name in ("AgentA", "AgentB"):
            await client.call_tool(
                "register_agent",
                {
                    "project_key": "/test-project",
                    "program": "pytest",
                    "model": "test-model",
                    "name": name,
                },
            )

        # Contact tools should still work
        request_result = await client.call_tool(
            "request_contact",
            {
                "project_key": "/test-project",
                "from_agent": "AgentA",
                "to_agent": "AgentB",
                "reason": "Testing backward compatibility",
            },
        )

        assert request_result is not None
        assert "to" in request_result

        # Can approve contact
        approve_result = await client.call_tool(
            "respond_contact",
            {
                "project_key": "/test-project",
                "to_agent": "AgentB",
                "from_agent": "AgentA",
                "accept": True,
            },
        )

        assert approve_result is not None
        assert approve_result["approved"] is True

        # But messaging should have worked even without the approval
        # Send a message without any contact approval to a new agent
        await client.call_tool(
            "register_agent",
            {
                "project_key": "/test-project",
                "program": "pytest",
                "model": "test-model",
                "name": "AgentC",
            },
        )

        result = await client.call_tool(
            "send_message",
            {
                "project_key": "/test-project",
                "sender_name": "AgentA",
                "to": ["AgentC"],
                "subject": "No approval needed",
                "body_md": "This works without any contact request",
            },
        )

        assert result is not None
        assert result["count"] == 1


@pytest.mark.asyncio
async def test_multiple_recipients_without_approval(isolated_env, monkeypatch):
    """Test sending to multiple recipients without any contact approval."""
    monkeypatch.setenv("CONTACT_ENFORCEMENT_ENABLED", "false")
    with contextlib.suppress(Exception):
        _config.clear_settings_cache()

    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test-project"})

        # Register multiple agents
        for name in ("Sender", "Recipient1", "Recipient2", "Recipient3"):
            await client.call_tool(
                "register_agent",
                {
                    "project_key": "/test-project",
                    "program": "pytest",
                    "model": "test-model",
                    "name": name,
                },
            )

        # Send to multiple recipients at once
        result = await client.call_tool(
            "send_message",
            {
                "project_key": "/test-project",
                "sender_name": "Sender",
                "to": ["Recipient1", "Recipient2"],
                "cc": ["Recipient3"],
                "subject": "Broadcast message",
                "body_md": "This should reach all recipients without approval",
            },
        )

        assert result is not None
        assert result["count"] == 3  # to + cc recipients

        # Verify all recipients received the message
        for recipient in ["Recipient1", "Recipient2", "Recipient3"]:
            inbox = await client.call_tool(
                "fetch_inbox",
                {
                    "project_key": "/test-project",
                    "agent_name": recipient,
                    "limit": 10,
                },
            )

            assert len(inbox) == 1
            assert inbox[0]["subject"] == "Broadcast message"
            assert inbox[0]["sender"] == "Sender"


@pytest.mark.asyncio
async def test_list_contacts_works_but_optional(isolated_env, monkeypatch):
    """Test that list_contacts still works for tracking purposes."""
    monkeypatch.setenv("CONTACT_ENFORCEMENT_ENABLED", "false")
    with contextlib.suppress(Exception):
        _config.clear_settings_cache()

    server = build_mcp_server()
    async with Client(server) as client:
        await client.call_tool("ensure_project", {"human_key": "/test-project"})

        for name in ("AgentA", "AgentB"):
            await client.call_tool(
                "register_agent",
                {
                    "project_key": "/test-project",
                    "program": "pytest",
                    "model": "test-model",
                    "name": name,
                },
            )

        # Create a contact link
        await client.call_tool(
            "request_contact",
            {
                "project_key": "/test-project",
                "from_agent": "AgentA",
                "to_agent": "AgentB",
                "reason": "Testing list",
            },
        )

        # List contacts should work
        contacts = await client.call_tool(
            "list_contacts",
            {
                "project_key": "/test-project",
                "agent_name": "AgentA",
            },
        )

        assert isinstance(contacts, list)
        assert len(contacts) >= 1
        assert any(c["to"] == "AgentB" for c in contacts)
