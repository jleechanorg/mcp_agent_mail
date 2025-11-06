"""Tests for global agent name uniqueness with different enforcement modes.

This test suite verifies that agent names are globally unique across all projects,
with different enforcement modes:
- "coerce" mode (default): Auto-generates unique names when duplicates are detected
- "strict" mode: Raises errors when duplicates are detected
"""

from __future__ import annotations

import pytest
from fastmcp import Client

from mcp_agent_mail.app import build_mcp_server


@pytest.mark.asyncio
async def test_agent_names_coerce_mode_auto_generates_unique_names(isolated_env):
    """Test that in coerce mode (default), duplicate names are auto-renamed to ensure global uniqueness."""
    # Default mode is "coerce" - should auto-generate unique names
    mcp = build_mcp_server()
    async with Client(mcp) as client:
        # Create two different projects
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project1"})
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project2"})

        # Create an agent "Alice" in project1
        result1 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project1",
                "program": "test_program",
                "model": "test_model",
                "name": "Alice",
            },
        )
        assert result1.data["name"] == "Alice"

        # Try to create another agent "Alice" in project2
        # In coerce mode, this should succeed but with an auto-generated unique name
        result2 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project2",
                "program": "test_program",
                "model": "test_model",
                "name": "Alice",
            },
        )

        # Should get a different auto-generated name, not "Alice"
        assert result2.data["name"] != "Alice"
        # Should be a valid agent name (adjective+noun pattern)
        assert len(result2.data["name"]) > 0
        print(f"Auto-generated name in coerce mode: {result2.data['name']}")


@pytest.mark.asyncio
async def test_agent_names_strict_mode_raises_errors(isolated_env, monkeypatch):
    """Test that in strict mode, duplicate names raise errors for global uniqueness."""
    # Set strict mode via environment variable
    monkeypatch.setenv("AGENT_NAME_ENFORCEMENT_MODE", "strict")

    mcp = build_mcp_server()
    async with Client(mcp) as client:
        # Create two different projects
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project1"})
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project2"})

        # Create an agent "Alice" in project1
        result1 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project1",
                "program": "test_program",
                "model": "test_model",
                "name": "Alice",
            },
        )
        assert result1.data["name"] == "Alice"

        # Try to create another agent "Alice" in project2 - should fail in strict mode
        with pytest.raises(Exception) as exc_info:
            await client.call_tool(
                "register_agent",
                arguments={
                    "project_key": "/tmp/project2",
                    "program": "test_program",
                    "model": "test_model",
                    "name": "Alice",
                },
            )

        # Verify the error is about the name being taken globally
        error_msg = str(exc_info.value).lower()
        assert "already in use" in error_msg or "name_taken" in error_msg


@pytest.mark.asyncio
async def test_agent_names_are_case_insensitive_coerce_mode(isolated_env):
    """Test that agent names are case-insensitive in coerce mode (Alice == alice == ALICE)."""
    mcp = build_mcp_server()
    async with Client(mcp) as client:
        # Create project
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project1"})

        # Create agent "Alice"
        result1 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project1",
                "program": "test_program",
                "model": "test_model",
                "name": "Alice",
            },
        )
        assert result1.data["name"] == "Alice"

        # Try to create "alice" (lowercase) in same project
        # In coerce mode within same project, this should update the existing agent
        result2 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project1",
                "program": "test_program",
                "model": "test_model",
                "name": "alice",
                "task_description": "Updated task",
            },
        )

        # Should update the same agent (case-insensitive match)
        assert result2.data["name"] == "Alice"  # Preserves original casing
        assert result2.data["id"] == result1.data["id"]
        assert result2.data["task_description"] == "Updated task"


@pytest.mark.asyncio
async def test_same_agent_can_be_reregistered_in_same_project(isolated_env):
    """Test that registering the same agent name in the same project updates it."""
    mcp = build_mcp_server()
    async with Client(mcp) as client:
        # Create project
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project1"})

        # Create agent "Alice" with task description "Task 1"
        result1 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project1",
                "program": "test_program",
                "model": "test_model",
                "name": "Alice",
                "task_description": "Task 1",
            },
        )
        assert result1.data["name"] == "Alice"
        assert result1.data["task_description"] == "Task 1"
        agent_id = result1.data["id"]

        # Re-register same agent with different task description - should update
        result2 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project1",
                "program": "test_program",
                "model": "test_model",
                "name": "Alice",
                "task_description": "Task 2",
            },
        )
        assert result2.data["name"] == "Alice"
        assert result2.data["task_description"] == "Task 2"
        assert result2.data["id"] == agent_id  # Same agent ID


@pytest.mark.asyncio
async def test_different_names_can_coexist_across_projects(isolated_env):
    """Test that different agent names can exist across multiple projects."""
    mcp = build_mcp_server()
    async with Client(mcp) as client:
        # Create two projects
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project1"})
        await client.call_tool("ensure_project", arguments={"human_key": "/tmp/project2"})

        # Create Alice in project1
        result1 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project1",
                "program": "test_program",
                "model": "test_model",
                "name": "Alice",
            },
        )
        assert result1.data["name"] == "Alice"

        # Create Bob in project2 - should succeed (different name)
        result2 = await client.call_tool(
            "register_agent",
            arguments={
                "project_key": "/tmp/project2",
                "program": "test_program",
                "model": "test_model",
                "name": "Bob",
            },
        )
        assert result2.data["name"] == "Bob"
        assert result2.data["id"] != result1.data["id"]  # Different agents
