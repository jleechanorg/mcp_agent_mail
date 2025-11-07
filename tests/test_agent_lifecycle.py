"""Test agent lifecycle operations: rename and delete."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcp_agent_mail.config import get_settings
from mcp_agent_mail.db import ensure_schema, get_session
from mcp_agent_mail.models import Agent, AgentLink, FileReservation, Message, MessageRecipient, Project
from mcp_agent_mail.storage import ensure_archive


@pytest.fixture
async def project_and_agents(isolated_env):
    """Create a test project with two agents."""
    settings = get_settings()
    await ensure_schema()

    # Create project
    async with get_session() as session:
        project = Project(human_key="/tmp/test-project", slug="test-project")
        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Create agents
        agent1 = Agent(
            project_id=project.id,
            name="BlueLake",
            program="test-program",
            model="test-model",
            task_description="Test task 1",
        )
        agent2 = Agent(
            project_id=project.id,
            name="RedMountain",
            program="test-program",
            model="test-model",
            task_description="Test task 2",
        )
        session.add(agent1)
        session.add(agent2)
        await session.commit()
        await session.refresh(agent1)
        await session.refresh(agent2)

    # Initialize archive
    archive = await ensure_archive(settings, project.slug)

    # Create archive directories
    agent1_dir = archive.root / "agents" / "BlueLake"
    agent1_dir.mkdir(parents=True, exist_ok=True)
    (agent1_dir / "profile.json").write_text('{"name": "BlueLake"}')

    agent2_dir = archive.root / "agents" / "RedMountain"
    agent2_dir.mkdir(parents=True, exist_ok=True)
    (agent2_dir / "profile.json").write_text('{"name": "RedMountain"}')

    # Create inbox/outbox directories with test files
    inbox_dir = agent1_dir / "inbox" / "2025" / "01"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / "test_message.md").write_text("Test inbox message")

    outbox_dir = agent1_dir / "outbox" / "2025" / "01"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    (outbox_dir / "test_message.md").write_text("Test outbox message")

    # Commit to git
    repo = archive.repo
    repo.index.add(["agents/BlueLake", "agents/RedMountain"])
    repo.index.commit("Initial agents")

    return project, agent1, agent2, archive


class TestRenameAgent:
    """Tests for rename_agent functionality."""

    @pytest.mark.asyncio
    async def test_rename_agent_uses_canonical_name(self, project_and_agents):
        """Test that rename uses canonical agent.name for filesystem operations, not user input."""
        project, _agent1, _agent2, archive = project_and_agents
        settings = get_settings()

        from mcp_agent_mail.app import _rename_agent

        # Call with lowercase (user typo), should still work
        renamed_agent = await _rename_agent(project, "bluelake", "GreenCastle", settings)

        # Verify database updated
        assert renamed_agent.name == "GreenCastle"

        # Verify old directory moved correctly (using canonical BlueLake, not bluelake)
        old_dir = archive.root / "agents" / "BlueLake"
        new_dir = archive.root / "agents" / "GreenCastle"
        assert not old_dir.exists(), "Old directory should be moved"
        assert new_dir.exists(), "New directory should exist"
        assert (new_dir / "profile.json").exists(), "Profile should exist in new location"

    @pytest.mark.asyncio
    async def test_rename_agent_stages_entire_directory(self, project_and_agents):
        """Test that rename stages entire directory including inbox/outbox."""
        project, _agent1, _agent2, archive = project_and_agents
        settings = get_settings()

        from mcp_agent_mail.app import _rename_agent

        _renamed_agent = await _rename_agent(project, "BlueLake", "GreenCastle", settings)

        # Verify all files moved
        new_dir = archive.root / "agents" / "GreenCastle"
        assert (new_dir / "profile.json").exists()
        assert (new_dir / "inbox" / "2025" / "01" / "test_message.md").exists()
        assert (new_dir / "outbox" / "2025" / "01" / "test_message.md").exists()

        # Verify git tracked the move
        repo = archive.repo
        # Get the latest commit
        commit = next(repo.iter_commits())
        assert "rename" in commit.message.lower()

    @pytest.mark.asyncio
    async def test_rename_agent_fails_when_destination_exists(self, project_and_agents):
        """Test that rename fails when destination directory already exists."""
        project, _agent1, _agent2, _archive = project_and_agents
        settings = get_settings()

        from mcp_agent_mail.app import _rename_agent

        # Try to rename BlueLake to RedMountain (which already exists)
        with pytest.raises(ValueError, match="already in use"):
            await _rename_agent(project, "BlueLake", "RedMountain", settings)

    @pytest.mark.asyncio
    async def test_rename_agent_creates_directory_if_old_not_exists(self, project_and_agents):
        """Test that rename creates new directory if old one doesn't exist on filesystem."""
        project, _agent1, _agent2, archive = project_and_agents
        settings = get_settings()

        # Remove the filesystem directory but keep DB entry
        import shutil
        old_dir = archive.root / "agents" / "BlueLake"
        shutil.rmtree(old_dir)

        from mcp_agent_mail.app import _rename_agent

        _renamed_agent = await _rename_agent(project, "BlueLake", "GreenCastle", settings)

        # New directory should be created
        new_dir = archive.root / "agents" / "GreenCastle"
        assert new_dir.exists()
        assert (new_dir / "profile.json").exists()

    @pytest.mark.asyncio
    async def test_rename_agent_same_name_case_insensitive(self, project_and_agents):
        """Test that renaming to same name (case-insensitive) is rejected."""
        project, _agent1, _agent2, _archive = project_and_agents
        settings = get_settings()

        from mcp_agent_mail.app import _rename_agent

        with pytest.raises(ValueError, match="same as current name"):
            await _rename_agent(project, "BlueLake", "bluelake", settings)


class TestDeleteAgent:
    """Tests for delete_agent functionality."""

    @pytest.mark.asyncio
    async def test_delete_agent_blocks_when_has_sent_messages(self, project_and_agents):
        """Test that delete fails when agent has sent messages."""
        project, agent1, _agent2, _archive = project_and_agents
        settings = get_settings()

        # Create a message sent by agent1
        async with get_session() as session:
            message = Message(
                project_id=project.id,
                sender_id=agent1.id,
                subject="Test message",
                body_md="Test body",
                importance="normal",
                ack_required=False,
            )
            session.add(message)
            await session.commit()

        from mcp_agent_mail.app import _delete_agent

        # Should fail because agent has sent messages
        with pytest.raises(ValueError, match="referenced by messages"):
            await _delete_agent(project, "BlueLake", settings)

    @pytest.mark.asyncio
    async def test_delete_agent_blocks_when_has_received_messages(self, project_and_agents):
        """Test that delete fails when agent has received messages."""
        project, agent1, agent2, _archive = project_and_agents
        settings = get_settings()

        # Create a message received by agent1
        async with get_session() as session:
            message = Message(
                project_id=project.id,
                sender_id=agent2.id,
                subject="Test message",
                body_md="Test body",
                importance="normal",
                ack_required=False,
            )
            session.add(message)
            await session.flush()

            recipient = MessageRecipient(
                message_id=message.id,
                agent_id=agent1.id,
                kind="to",
            )
            session.add(recipient)
            await session.commit()

        from mcp_agent_mail.app import _delete_agent

        # Should fail because agent has received messages
        with pytest.raises(ValueError, match="referenced by messages"):
            await _delete_agent(project, "BlueLake", settings)

    @pytest.mark.asyncio
    async def test_delete_agent_blocks_when_has_agent_links(self, project_and_agents):
        """Test that delete fails when agent has agent links."""
        project, agent1, agent2, _archive = project_and_agents
        settings = get_settings()

        # Create an agent link
        async with get_session() as session:
            link = AgentLink(
                a_project_id=project.id,
                a_agent_id=agent1.id,
                b_project_id=project.id,
                b_agent_id=agent2.id,
                relation="contact",
                initiated_by="a",
            )
            session.add(link)
            await session.commit()

        from mcp_agent_mail.app import _delete_agent

        # Should fail because agent has links
        with pytest.raises(ValueError, match="links"):
            await _delete_agent(project, "BlueLake", settings)

    @pytest.mark.asyncio
    async def test_delete_agent_checks_unreleased_reservations_only(self, project_and_agents):
        """Test that delete only blocks on unreleased, unexpired reservations."""
        project, agent1, _agent2, _archive = project_and_agents
        settings = get_settings()

        now = datetime.now(timezone.utc)

        # Create released reservation (should not block)
        async with get_session() as session:
            released_res = FileReservation(
                project_id=project.id,
                agent_id=agent1.id,
                path_pattern="test/*.py",
                exclusive=True,
                reason="test",
                expires_ts=now + timedelta(hours=1),
                released_ts=now - timedelta(minutes=5),  # Already released
            )
            session.add(released_res)
            await session.commit()

        from mcp_agent_mail.app import _delete_agent

        # Should succeed because reservation is released
        delete_result = await _delete_agent(project, "BlueLake", settings)
        assert delete_result["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_agent_blocks_on_active_unreleased_reservation(self, project_and_agents):
        """Test that delete blocks on active unreleased reservations."""
        project, agent1, _agent2, _archive = project_and_agents
        settings = get_settings()

        now = datetime.now(timezone.utc)

        # Create active unreleased reservation
        async with get_session() as session:
            active_res = FileReservation(
                project_id=project.id,
                agent_id=agent1.id,
                path_pattern="test/*.py",
                exclusive=True,
                reason="test",
                expires_ts=now + timedelta(hours=1),
                released_ts=None,  # Not released
            )
            session.add(active_res)
            await session.commit()

        from mcp_agent_mail.app import _delete_agent

        # Should fail because reservation is active
        with pytest.raises(ValueError, match="active file reservation"):
            await _delete_agent(project, "BlueLake", settings)

    @pytest.mark.asyncio
    async def test_delete_agent_moves_to_trash(self, project_and_agents):
        """Test that delete moves agent directory to trash."""
        project, _agent1, _agent2, archive = project_and_agents
        settings = get_settings()

        from mcp_agent_mail.app import _delete_agent

        result = await _delete_agent(project, "BlueLake", settings)

        # Verify moved to trash
        old_dir = archive.root / "agents" / "BlueLake"
        trash_dir = archive.root / "agents" / ".trash" / "BlueLake"

        assert not old_dir.exists(), "Original directory should be removed"
        assert trash_dir.exists(), "Trash directory should exist"
        assert (trash_dir / "profile.json").exists(), "Profile should exist in trash"

        # Verify git tracked the move
        repo = archive.repo
        commit = next(repo.iter_commits())
        assert "delete" in commit.message.lower()

        assert result["deleted"] is True
        assert result["agent"]["name"] == "BlueLake"

    @pytest.mark.asyncio
    async def test_delete_agent_uses_canonical_name(self, project_and_agents):
        """Test that delete uses canonical agent.name for filesystem operations."""
        project, _agent1, _agent2, archive = project_and_agents
        settings = get_settings()

        from mcp_agent_mail.app import _delete_agent

        # Call with lowercase (user typo), should still work
        _result = await _delete_agent(project, "bluelake", settings)

        # Verify moved to trash using canonical name
        trash_dir = archive.root / "agents" / ".trash" / "BlueLake"
        assert trash_dir.exists(), "Should use canonical BlueLake, not bluelake"
