# PyPI Package Cleanup

## Old Package: mcp-agent-mail

The package has been renamed from `mcp-agent-mail` to `ai-universe-mail`.

### To Remove the Old Package

PyPI doesn't provide a public API for deleting or yanking packages. You must use the web interface:

#### Option 1: Delete Project (Recommended)

1. Log in to <https://pypi.org>
2. Navigate to <https://pypi.org/project/mcp-agent-mail/>
3. Click "Manage" in the sidebar
4. Click "Settings"
5. Scroll to the bottom and click "Delete project"
6. Confirm by typing the project name: `mcp-agent-mail`

**Note**: Deletion is only available if the package has minimal downloads and no dependents.

#### Option 2: Yank Release (If deletion unavailable)

1. Log in to <https://pypi.org>
2. Navigate to <https://pypi.org/project/mcp-agent-mail/>
3. Click on version "0.1.0"
4. Click "Options" dropdown
5. Select "Yank version 0.1.0"
6. Add yank reason: "Package renamed to ai-universe-mail"

**Effect**: Prevents new installations but keeps the package visible with a warning.

## New Package: ai-universe-mail

**Install**: `pip install ai-universe-mail`

**PyPI URL**: <https://pypi.org/project/ai-universe-mail/>

The server has been verified to run successfully from the PyPI package.
