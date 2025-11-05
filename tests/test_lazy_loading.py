"""Tests for lazy loading meta-tools."""

import pytest
from mcp_agent_mail.app import build_mcp_server, CORE_TOOLS, EXTENDED_TOOLS, _EXTENDED_TOOL_REGISTRY


class TestListExtendedTools:
    """Tests for list_extended_tools meta-tool."""

    @pytest.mark.asyncio
    async def test_list_extended_tools_returns_correct_count(self):
        """Test that list_extended_tools returns correct count of tools."""
        mcp = build_mcp_server()

        # Check that _EXTENDED_TOOL_REGISTRY is populated
        assert len(_EXTENDED_TOOL_REGISTRY) == len(EXTENDED_TOOLS), (
            f"Registry has {len(_EXTENDED_TOOL_REGISTRY)} tools but EXTENDED_TOOLS has {len(EXTENDED_TOOLS)}"
        )
        assert len(_EXTENDED_TOOL_REGISTRY) == 19, "Expected 19 extended tools"

    @pytest.mark.asyncio
    async def test_list_extended_tools_has_all_categories(self):
        """Test that all tools have valid categories in metadata."""
        from mcp_agent_mail.app import EXTENDED_TOOL_METADATA

        expected_categories = {
            "messaging",
            "search",
            "identity",
            "contact",
            "file_reservations",
            "workflow_macros",
            "infrastructure",
        }

        actual_categories = {
            meta.get("category")
            for meta in EXTENDED_TOOL_METADATA.values()
        }

        assert actual_categories.issubset(expected_categories | {"uncategorized"}), (
            f"Unexpected categories: {actual_categories - expected_categories}"
        )


class TestExtendedToolRegistry:
    """Tests for _EXTENDED_TOOL_REGISTRY population."""

    @pytest.mark.asyncio
    async def test_extended_tool_registry_populated(self):
        """Test that all extended tools are in registry after server build."""
        # Build server to populate registry
        _ = build_mcp_server()

        # Verify all extended tools are registered
        assert len(_EXTENDED_TOOL_REGISTRY) == len(EXTENDED_TOOLS), (
            f"Registry has {len(_EXTENDED_TOOL_REGISTRY)} tools but EXTENDED_TOOLS defines {len(EXTENDED_TOOLS)}"
        )

        for tool_name in EXTENDED_TOOLS:
            assert tool_name in _EXTENDED_TOOL_REGISTRY, (
                f"Extended tool '{tool_name}' not found in registry"
            )
            assert callable(_EXTENDED_TOOL_REGISTRY[tool_name]), (
                f"Registry entry for '{tool_name}' is not callable"
            )


class TestCoreTools:
    """Tests for core tools categorization."""

    def test_core_tools_count(self):
        """Test that core tools has expected count."""
        assert len(CORE_TOOLS) == 8, f"Expected 8 core tools, got {len(CORE_TOOLS)}"

    def test_core_and_extended_are_disjoint(self):
        """Test that core and extended tool sets don't overlap."""
        overlap = CORE_TOOLS & EXTENDED_TOOLS
        assert not overlap, f"Core and extended tools should be disjoint, but have overlap: {overlap}"

    def test_essential_tools_in_core(self):
        """Test that essential tools are in core set."""
        essential_tools = {
            "health_check",
            "ensure_project",
            "register_agent",
            "send_message",
            "fetch_inbox",
        }
        assert essential_tools.issubset(CORE_TOOLS), (
            f"Missing essential tools from core: {essential_tools - CORE_TOOLS}"
        )


class TestToolMetadata:
    """Tests for EXTENDED_TOOL_METADATA structure."""

    def test_all_extended_tools_have_metadata(self):
        """Test that every extended tool has metadata entry."""
        from mcp_agent_mail.app import EXTENDED_TOOL_METADATA

        for tool_name in EXTENDED_TOOLS:
            assert tool_name in EXTENDED_TOOL_METADATA, (
                f"Extended tool '{tool_name}' missing from EXTENDED_TOOL_METADATA"
            )

    def test_metadata_has_required_fields(self):
        """Test that metadata entries have category and description."""
        from mcp_agent_mail.app import EXTENDED_TOOL_METADATA

        for tool_name, metadata in EXTENDED_TOOL_METADATA.items():
            assert "category" in metadata, f"Tool '{tool_name}' metadata missing 'category'"
            assert "description" in metadata, f"Tool '{tool_name}' metadata missing 'description'"
            assert isinstance(metadata["category"], str), (
                f"Tool '{tool_name}' category must be string"
            )
            assert isinstance(metadata["description"], str), (
                f"Tool '{tool_name}' description must be string"
            )
            assert len(metadata["description"]) > 0, (
                f"Tool '{tool_name}' description is empty"
            )


class TestToolsMode:
    """Tests for MCP_TOOLS_MODE environment variable support."""

    def test_tools_mode_default_is_extended(self):
        """Test that default tools mode is 'extended'."""
        from mcp_agent_mail.config import get_settings, clear_settings_cache

        # Clear cache to get fresh settings
        clear_settings_cache()
        settings = get_settings()

        assert settings.tools_mode == "extended", (
            f"Default tools_mode should be 'extended', got '{settings.tools_mode}'"
        )

    def test_tools_mode_normalizes_to_lowercase(self, monkeypatch):
        """Test that tools_mode is normalized to lowercase."""
        from mcp_agent_mail.config import get_settings, clear_settings_cache

        monkeypatch.setenv("MCP_TOOLS_MODE", "CORE")
        clear_settings_cache()
        settings = get_settings()

        assert settings.tools_mode == "core", (
            f"tools_mode should be normalized to 'core', got '{settings.tools_mode}'"
        )
