# PR Targeting Test

This file verifies that PRs created from this repository target the correct fork.

## Test Details

- **Date**: 2025-11-06
- **Branch**: test/pr-targeting-verification
- **Expected target**: jleechanorg/mcp_agent_mail
- **Purpose**: Verify gh pr create targets user fork, not upstream

## Verification

If this PR appears in `jleechanorg/mcp_agent_mail`, the test is successful.

If this PR appears in `Dicklesworthstone/mcp_agent_mail`, configuration is incorrect.

## Cleanup

After verification, this PR and file should be deleted.
