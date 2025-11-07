"""Tests for delete_agent functionality."""

from datetime import datetime, timezone, timedelta

import pytest
from sqlmodel import select
from mcp_agent_mail.app import _delete_agent, _get_agent
from mcp_agent_mail.models import (
    Agent,
    Message,
    MessageRecipient,
    FileReservation,
    AgentLink,
    Project,
)
from mcp_agent_mail.db import get_session, ensure_schema


@pytest.fixture
async def setup_test_data():
    """Set up test data for delete_agent tests."""
    await ensure_schema()

    async with get_session() as session:
        async with session.begin():
            # Create a test project
            project = Project(
                human_key="test_project",
                slug="test_project",
                api_key_hash="test_hash",
            )
            session.add(project)
            await session.flush()

            # Create agents
            agent_a = Agent(
                project_id=project.id, name="agent_a", description="Agent A"
            )
            agent_b = Agent(
                project_id=project.id, name="agent_b", description="Agent B"
            )
            agent_c = Agent(
                project_id=project.id, name="agent_c", description="Agent C"
            )
            session.add_all([agent_a, agent_b, agent_c])
            await session.flush()

            # Create messages:
            # - agent_a -> agent_b
            # - agent_a -> agent_c
            # - agent_a -> agent_a (self message)
            # - agent_b -> agent_a
            msg1 = Message(
                project_id=project.id,
                sender_id=agent_a.id,
                subject="Message 1",
                body="From A to B",
            )
            msg2 = Message(
                project_id=project.id,
                sender_id=agent_a.id,
                subject="Message 2",
                body="From A to C",
            )
            msg3 = Message(
                project_id=project.id,
                sender_id=agent_a.id,
                subject="Message 3",
                body="From A to A",
            )
            msg4 = Message(
                project_id=project.id,
                sender_id=agent_b.id,
                subject="Message 4",
                body="From B to A",
            )
            session.add_all([msg1, msg2, msg3, msg4])
            await session.flush()

            # Create message recipients
            mr1 = MessageRecipient(message_id=msg1.id, agent_id=agent_b.id, kind="to")
            mr2 = MessageRecipient(message_id=msg2.id, agent_id=agent_c.id, kind="to")
            mr3 = MessageRecipient(message_id=msg3.id, agent_id=agent_a.id, kind="to")
            mr4 = MessageRecipient(message_id=msg4.id, agent_id=agent_a.id, kind="to")
            session.add_all([mr1, mr2, mr3, mr4])

            # Create agent links
            link1 = AgentLink(a_agent_id=agent_a.id, b_agent_id=agent_b.id, kind="contact")
            link2 = AgentLink(a_agent_id=agent_a.id, b_agent_id=agent_c.id, kind="contact")
            session.add_all([link1, link2])

            # Create file reservation
            file_res = FileReservation(
                agent_id=agent_a.id,
                project_id=project.id,
                path_pattern="test/file.txt",
                expires_ts=datetime.now(timezone.utc) + timedelta(days=1),
            )
            session.add(file_res)

            await session.commit()

    return {
        "project": project,
        "agent_a_id": agent_a.id,
        "agent_b_id": agent_b.id,
        "agent_c_id": agent_c.id,
    }


@pytest.mark.asyncio
async def test_delete_agent_cascades_correctly(setup_test_data):
    """Test that deleting an agent properly cascades to all related records."""
    data = await setup_test_data
    project = data["project"]
    agent_a_id = data["agent_a_id"]
    agent_b_id = data["agent_b_id"]

    # Verify initial state
    async with get_session() as session:
        # Should have 3 messages from agent_a
        result = await session.execute(
            select(Message).where(Message.sender_id == agent_a_id)
        )
        assert len(result.scalars().all()) == 3

        # Should have 4 message recipients total
        result = await session.execute(select(MessageRecipient))
        assert len(result.scalars().all()) == 4

        # Should have 3 agents
        result = await session.execute(select(Agent))
        assert len(result.scalars().all()) == 3

    # Delete agent_a
    stats = await _delete_agent(project, "agent_a")

    # Verify deletion stats
    assert stats["agent_id"] == agent_a_id
    assert stats["agent_name"] == "agent_a"
    assert stats["messages_deleted"] == 3  # All messages from agent_a
    assert stats["message_recipients_deleted"] == 4  # All recipients related to agent_a
    assert stats["agent_links_deleted"] == 2  # Links with agent_b and agent_c
    assert stats["file_reservations_deleted"] == 1

    # Verify post-deletion state
    async with get_session() as session:
        # Agent_a should be deleted
        result = await session.execute(select(Agent).where(Agent.id == agent_a_id))
        assert result.scalars().first() is None

        # Messages from agent_a should be deleted
        result = await session.execute(
            select(Message).where(Message.sender_id == agent_a_id)
        )
        assert len(result.scalars().all()) == 0

        # All MessageRecipient records involving agent_a should be deleted
        result = await session.execute(
            select(MessageRecipient).where(MessageRecipient.agent_id == agent_a_id)
        )
        assert len(result.scalars().all()) == 0

        # Message from agent_b to agent_a should still exist (message itself)
        result = await session.execute(
            select(Message).where(Message.sender_id == agent_b_id)
        )
        messages = result.scalars().all()
        assert len(messages) == 1

        # But the MessageRecipient pointing to agent_a should be deleted
        msg_b_to_a = messages[0]
        result = await session.execute(
            select(MessageRecipient).where(MessageRecipient.message_id == msg_b_to_a.id)
        )
        assert len(result.scalars().all()) == 0

        # Agent links involving agent_a should be deleted
        result = await session.execute(
            select(AgentLink).where(
                (AgentLink.a_agent_id == agent_a_id) | (AgentLink.b_agent_id == agent_a_id)
            )
        )
        assert len(result.scalars().all()) == 0

        # File reservations for agent_a should be deleted
        result = await session.execute(
            select(FileReservation).where(FileReservation.agent_id == agent_a_id)
        )
        assert len(result.scalars().all()) == 0

        # Other agents should still exist
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        assert len(agents) == 2  # agent_b and agent_c remain


@pytest.mark.asyncio
async def test_delete_agent_no_orphaned_recipients():
    """Test that no MessageRecipient records are orphaned after deletion."""
    await ensure_schema()

    async with get_session() as session:
        async with session.begin():
            # Create project and agents
            project = Project(
                human_key="test_orphan", slug="test_orphan", api_key_hash="hash"
            )
            session.add(project)
            await session.flush()

            agent_x = Agent(project_id=project.id, name="agent_x", description="X")
            agent_y = Agent(project_id=project.id, name="agent_y", description="Y")
            session.add_all([agent_x, agent_y])
            await session.flush()

            # agent_x sends message to agent_y
            msg = Message(
                project_id=project.id,
                sender_id=agent_x.id,
                subject="Test",
                body="Test message",
            )
            session.add(msg)
            await session.flush()

            # agent_y is recipient
            mr = MessageRecipient(message_id=msg.id, agent_id=agent_y.id, kind="to")
            session.add(mr)
            await session.commit()

            agent_x_id = agent_x.id
            msg_id = msg.id

    # Delete agent_x (the sender)
    await _delete_agent(project, "agent_x")

    # Verify the message is deleted
    async with get_session() as session:
        result = await session.execute(select(Message).where(Message.id == msg_id))
        assert result.scalars().first() is None

        # Verify no orphaned MessageRecipient records exist
        result = await session.execute(
            select(MessageRecipient).where(MessageRecipient.message_id == msg_id)
        )
        assert len(result.scalars().all()) == 0
