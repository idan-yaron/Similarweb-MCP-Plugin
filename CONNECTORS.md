# Connectors

This plugin uses tool-agnostic connector placeholders so each user's exact Cowork plugin stack (pptx vs slides, slack vs teams, etc.) can be resolved at runtime. Cowork's built-in `cowork-plugin-management` plugin handles the `~~` substitution.

| Category | Placeholder | Default | Other supported |
|----------|-------------|---------|-----------------|
| Deck | `~~deck` | pptx (Anthropic-shipped) | (none) |
| Spreadsheet | `~~spreadsheet` | xlsx (Anthropic-shipped) | (none) |
| Document | `~~doc` | pdf | docx |
| Chat | `~~chat` | slack-by-salesforce | Teams, Discord |
| Data warehouse | `~~data warehouse` | data plugin's Snowflake | BigQuery, Redshift, PostgreSQL |
| CRM | `~~CRM` | Salesforce | HubSpot, Pipedrive |

## How recipes invoke connectors

Recipes' `## Export options` blocks (one per recipe) cite the connectors by placeholder. At runtime Cowork resolves the placeholder to the user's chosen plugin and the recipe delegates via the `Skill` tool. If the user has not configured a connector for that category, the recipe surfaces a graceful error: "To export this to a slide deck, install a deck-builder plugin (default: pptx) via Cowork settings."

## Plugin requirements

This plugin does not bundle the connector targets. Users must install the upstream plugins separately:

- pptx, xlsx, pdf, docx: Anthropic-shipped via the SkillsPlugin registry (auto-available in Cowork).
- slack-by-salesforce, salesforce-crm, data: install from Cowork's in-app plugin marketplace (Customize, then Plugins).
