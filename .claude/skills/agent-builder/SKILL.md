---
name: agent-builder
description: Interactive wizard for creating Claude Code custom subagents at user or project scope.
disable-model-invocation: true
---

# Agent Builder

Create Claude Code custom subagents through an interactive wizard.

This skill replaces the old interactive `/agents` creation workflow.

The wizard creates standard Claude Code agent Markdown files in either:

- User scope: `~/.claude/agents/<agent-name>.md`
- Project scope: `${CLAUDE_PROJECT_DIR}/.claude/agents/<agent-name>.md`

The skill itself may be installed at either or both:

- User scope: `~/.claude/skills/agent-builder/SKILL.md`
- Project scope: `${CLAUDE_PROJECT_DIR}/.claude/skills/agent-builder/SKILL.md`

Run the wizard manually with:

```text
/agent-builder
```

---

# Core behavior

Run this workflow interactively in the main Claude Code conversation.

Do not run the wizard in a forked subagent because the wizard needs to communicate directly with the user while constructing the agent definition.

Use `AskUserQuestion` when it is available.

If `AskUserQuestion` is unavailable, ask the same questions conversationally.

Do not silently guess required configuration choices.

Show the complete generated agent definition before writing it to disk.

---

# Provider-safe model handling

The user may launch Claude Code through custom provider scripts.

These scripts may redirect Claude Code to another Anthropic-compatible provider and may map Claude model-family aliases to provider-specific models.

Examples may include mappings such as:

```text
opus   -> provider model A
sonnet -> provider model A
haiku  -> provider model B
```

The exact mappings belong to the user's provider configuration.

Therefore:

- Never inspect API keys unless explicitly requested for an unrelated troubleshooting task.
- Never copy API keys into an agent file.
- Never modify provider launcher scripts.
- Never modify `ANTHROPIC_BASE_URL`.
- Never modify authentication environment variables.
- Never rewrite the user's model environment variables.
- Never replace Claude Code model aliases with provider-specific model IDs.

When the user selects a model, write exactly one of:

```yaml
model: opus
```

```yaml
model: sonnet
```

```yaml
model: haiku
```

```yaml
model: inherit
```

The provider configuration remains responsible for resolving those aliases to the actual underlying model.

For example, if the user's launcher maps:

```text
ANTHROPIC_DEFAULT_OPUS_MODEL
ANTHROPIC_DEFAULT_SONNET_MODEL
ANTHROPIC_DEFAULT_HAIKU_MODEL
```

to another provider's models, do not interfere with those mappings.

The Agent Builder only records the logical Claude Code model choice.

---

# Never modify global provider configuration

This skill creates agent definitions only.

Do not modify:

```text
~/.claude/settings.json
~/.claude/settings.local.json
.claude/settings.json
.claude/settings.local.json
.env
Start-Claude.ps1
Start-ClaudeWithMiMo.ps1
Start-ClaudeWithCursor.ps1
```

or equivalent provider/configuration files merely to create an agent.

The only directories this wizard should normally create or modify are:

```text
~/.claude/agents/
```

or:

```text
${CLAUDE_PROJECT_DIR}/.claude/agents/
```

depending on the selected scope.

---

# Wizard overview

Collect the following information:

1. Agent scope
2. Agent name
3. Agent purpose
4. Agent system instructions
5. Tool access
6. Model
7. Display color
8. Persistent memory
9. Final preview
10. Confirmation
11. File creation
12. Validation

Do not write the file until the user has had an opportunity to review the generated configuration.

---

# Step 1 — Agent scope

Ask where the agent should be available.

Present:

```text
User
Project
```

## User

Use:

```text
~/.claude/agents/<agent-name>.md
```

A user-level agent can be used across projects on the current machine.

## Project

Use:

```text
${CLAUDE_PROJECT_DIR}/.claude/agents/<agent-name>.md
```

A project-level agent belongs to the current repository/project and can normally be committed to version control.

Store this choice as the agent's destination scope.

---

# Step 2 — Agent name

Ask for the agent name.

Prefer lowercase kebab-case.

Examples:

```text
code-reviewer
backend-developer
security-auditor
database-specialist
test-engineer
research-agent
```

Validate the name before continuing.

Rules:

- Must not begin with `-`.
- Must not contain `:`.
- Prefer lowercase letters, numbers, and hyphens.
- Keep the name concise.
- Use the same value for the filename unless the user explicitly requests otherwise.

Example:

```text
backend-developer
```

becomes:

```text
backend-developer.md
```

The `name` frontmatter field is the agent's actual identity.

---

# Step 3 — Purpose and description

Ask:

```text
What should this agent specialize in, and when should Claude delegate work to it?
```

Generate a concise `description`.

The description should help Claude Code decide when to delegate to this agent.

Keep it short.

Do not place detailed operating instructions in `description`.

Example:

```yaml
description: Implements, debugs, and reviews backend application features.
```

Detailed behavior belongs in the Markdown system prompt.

---

# Step 4 — Agent instructions

Ask what the agent should actually do.

Gather enough information to determine:

- Role
- Primary responsibilities
- Important constraints
- Expected behavior
- Expected output
- Things the agent must avoid
- Whether it should proactively inspect related files
- Whether it should update memory when memory is enabled

If the user provides only a short purpose, convert it into a concise system prompt without inventing project-specific requirements.

Prefer practical instructions.

Example:

```markdown
You are a backend development specialist.

When invoked:

- Inspect the relevant implementation and surrounding code before making changes.
- Follow existing project architecture and coding conventions.
- Make focused changes rather than broad unrelated refactors.
- Run relevant tests or validation when execution tools are available.
- Report the files changed and any important assumptions.
```

---

# Step 5 — Tool access

Ask which tool categories the agent should receive.

Present:

```text
All
Read-only
Edit
Execution
MCP
Others
```

`All` is exclusive.

If `All` is selected, do not combine it with the other categories.

For all other choices, allow selecting multiple categories.

Merge duplicate tools before generating the agent.

---

## Tool option — All

If the user selects:

```text
All
```

omit the `tools` field entirely.

Do not write:

```yaml
tools: all
```

Omitting `tools` tells Claude Code to inherit the tools available to subagents in the current session.

This is preferable to maintaining a hardcoded list of every Claude Code tool.

Example:

```yaml
---
name: implementation-agent
description: Handles general implementation work.
model: sonnet
color: green
---
```

There is intentionally no `tools:` field.

---

# Tool option — Read-only

Canonical read-only tool set:

```text
Read
Grep
Glob
LSP
WebFetch
WebSearch
```

Generate:

```yaml
tools: Read, Grep, Glob, LSP, WebFetch, WebSearch
```

Use this category for agents that should inspect and analyze information without modifying project files.

Examples:

```text
research-agent
code-reviewer
architecture-reviewer
dependency-researcher
```

---

# Tool option — Edit

Canonical editing tool set:

```text
Read
Grep
Glob
LSP
Edit
Write
NotebookEdit
```

Generate:

```yaml
tools: Read, Grep, Glob, LSP, Edit, Write, NotebookEdit
```

Use this category when the agent should inspect and modify project files.

---

# Tool option — Execution

Canonical execution tool set:

```text
Read
Grep
Glob
LSP
Bash
PowerShell
```

Generate:

```yaml
tools: Read, Grep, Glob, LSP, Bash, PowerShell
```

This category is appropriate for:

- Running tests
- Running build commands
- Running package managers
- Inspecting git state
- Running scripts
- Executing development commands

If a listed execution tool is not available in the current environment, do not invent a replacement tool.

---

# Combining Edit and Execution

If both are selected, merge the tools.

Example:

```yaml
tools: Read, Grep, Glob, LSP, Edit, Write, NotebookEdit, Bash, PowerShell
```

Remove duplicates.

---

# Tool option — MCP

If the user selects:

```text
MCP
```

ask which already-configured MCP server or servers the agent should use.

Examples of possible server names:

```text
github
playwright
postgres
filesystem
slack
```

Do not assume these servers exist.

Do not ask for MCP credentials.

Do not place secrets inside the agent definition.

For an already-configured MCP server named:

```text
github
```

add:

```yaml
mcpServers:
  - github
```

If the agent also has an explicit `tools` allowlist, add the MCP server-level tool pattern:

```text
mcp__github
```

Example:

```yaml
tools: Read, Grep, Glob, mcp__github
mcpServers:
  - github
```

For multiple servers:

```yaml
tools: Read, Grep, Glob, mcp__github, mcp__playwright
mcpServers:
  - github
  - playwright
```

The server-level MCP pattern means the agent can use tools belonging to that named server.

If MCP is selected as the only non-`All` tool category, require at least one server name.

---

# Tool option — Others

If the user selects:

```text
Others
```

ask which exact additional Claude Code tools should be available.

Possible examples include:

```text
Agent
Skill
TodoWrite
ToolSearch
Monitor
TaskStop
SendMessage
Artifact
EnterWorktree
ExitWorktree
```

Do not automatically add them.

The user must choose them or describe a requirement that clearly needs them.

---

# Agent tool

If the user selects:

```text
Agent
```

the generated subagent may itself be able to spawn additional subagents, subject to Claude Code's subagent depth and session restrictions.

Do not enable `Agent` merely because the generated file itself represents an agent.

Only enable it when the user wants this agent to delegate work further.

---

# Tool availability

Tool availability can depend on:

- Claude Code version
- Operating system
- Foreground/background execution
- MCP configuration
- Session configuration
- Permissions
- Provider environment

Do not fabricate unavailable tools.

If a user explicitly provides an exact valid tool name, preserve it unless there is a clear compatibility problem.

When possible, prefer the canonical categories defined above.

---

# Step 6 — Model

Ask:

```text
Which model should this agent use?
```

Present exactly:

```text
Sonnet
Opus
Haiku
Inherit from parent
```

Map them as follows:

```text
Sonnet              -> sonnet
Opus                -> opus
Haiku                -> haiku
Inherit from parent -> inherit
```

Generate exactly the alias.

Examples:

```yaml
model: sonnet
```

```yaml
model: opus
```

```yaml
model: haiku
```

```yaml
model: inherit
```

Do not resolve the alias yourself.

Do not replace it with a provider-specific model ID.

Do not inspect launcher scripts merely to determine which physical model the alias currently maps to.

---

# Inherit model behavior

When the user selects:

```text
Inherit from parent
```

write:

```yaml
model: inherit
```

This tells Claude Code to use the parent/main conversation's model according to Claude Code's model resolution behavior.

Do not omit `model` when the user explicitly chooses `inherit`.

---

# Step 7 — Display color

Ask:

```text
Which display color should identify this subagent while it is running?
```

Present:

```text
Red
Blue
Green
Yellow
Purple
Orange
Pink
Cyan
```

Map them to lowercase:

```text
Red    -> red
Blue   -> blue
Green  -> green
Yellow -> yellow
Purple -> purple
Orange -> orange
Pink   -> pink
Cyan   -> cyan
```

Always write the selected color into the agent frontmatter.

Example:

```yaml
color: purple
```

---

# Purpose of the color field

The `color` field controls the subagent's display color in Claude Code's:

- Task list
- Transcript

It acts as a visual identifier for the subagent while the agent is being displayed or running.

Do not claim that it recolors every terminal line or every character of the subagent's output.

Describe it as:

```text
Subagent display color / visual identifier
```

Encourage distinct colors when multiple specialized agents may run concurrently.

For example, a user may optionally adopt a convention such as:

```text
Blue   = research
Green  = implementation
Yellow = testing
Red    = debugging
Purple = architecture
Cyan   = review
Orange = operations
Pink   = documentation
```

This convention is optional.

Never force semantic meaning onto a color unless the user chooses such a convention.

---

# Step 8 — Persistent agent memory

Ask:

```text
Should this agent have persistent memory?
```

Present:

```text
Project
None
User
Local
```

Map them as follows:

```text
Project -> project
User    -> user
Local   -> local
None    -> omit memory field
```

---

# Memory — Project

Generate:

```yaml
memory: project
```

Claude Code stores project-scoped agent memory under:

```text
.claude/agent-memory/<agent-name>/
```

Use this when the knowledge should belong to the project and may be shared through version control.

This is generally the preferred memory scope for project-specific specialist agents.

---

# Memory — User

Generate:

```yaml
memory: user
```

Claude Code stores user-scoped agent memory under:

```text
~/.claude/agent-memory/<agent-name>/
```

Use this when the agent should retain relevant knowledge across multiple projects.

---

# Memory — Local

Generate:

```yaml
memory: local
```

Claude Code stores local project memory under:

```text
.claude/agent-memory-local/<agent-name>/
```

Use this when memory should remain project-specific but should not normally be committed to version control.

---

# Memory — None

If the user selects:

```text
None
```

omit the `memory` field completely.

Do not generate:

```yaml
memory: none
```

`none` is not a persistent memory scope.

The absence of the `memory` field represents no persistent agent memory.

---

# Memory-aware system prompt

When memory is enabled, add concise instructions telling the agent how to use it.

For example:

```markdown
Use your persistent agent memory to retain useful project knowledge across tasks.

Before starting work, consult relevant memory when it may help.

Update memory with durable information such as:

- Important code locations
- Architecture decisions
- Project conventions
- Repeated debugging findings
- Important workflow knowledge

Do not store temporary noise, secrets, API keys, credentials, or irrelevant task details.
```

Do not add these instructions when memory is `None`.

---

# Step 9 — Build the final configuration

Use YAML frontmatter followed by the system prompt in Markdown.

Preferred field order:

```yaml
---
name: <name>
description: <description>
tools: <comma-separated tool list>
model: <sonnet|opus|haiku|inherit>
color: <red|blue|green|yellow|purple|orange|pink|cyan>
memory: <project|user|local>
mcpServers:
  - <server>
---
```

Only include fields that apply.

Important exceptions:

- Omit `tools` when `All` is selected.
- Omit `memory` when `None` is selected.
- Omit `mcpServers` when no MCP server was selected.

---

# Example — Read-only reviewer

```markdown
---
name: code-reviewer
description: Reviews code changes for correctness, maintainability, security, and test gaps.
tools: Read, Grep, Glob, LSP
model: sonnet
color: cyan
memory: project
---

You are a focused code-review specialist.

When invoked:

- Inspect the relevant code and surrounding implementation.
- Identify correctness, security, maintainability, and testing concerns.
- Prioritize concrete issues over stylistic preferences.
- Reference relevant files and locations when possible.
- Do not modify project files.
- Return concise, actionable findings.

Use your persistent agent memory for durable project-specific review knowledge.

Consult relevant memory before reviewing when useful, and update it with recurring patterns, conventions, or important architectural findings.
```

---

# Example — Implementation agent

```markdown
---
name: backend-developer
description: Implements and debugs backend application features.
tools: Read, Grep, Glob, LSP, Edit, Write, Bash, PowerShell
model: opus
color: green
memory: project
---

You are a backend development specialist.

When invoked:

- Understand the existing implementation before changing it.
- Follow established project architecture and conventions.
- Make focused, maintainable changes.
- Avoid unrelated refactors.
- Run relevant tests or validation when possible.
- Report what changed and any remaining concerns.

Use persistent memory for durable project architecture, conventions, important code locations, and recurring implementation knowledge.
```

---

# Example — Provider-safe model selection

If the user chooses:

```text
Opus
```

generate:

```yaml
model: opus
```

Even if the current Claude Code launcher internally maps Opus to something such as:

```text
mimo-v2.6-pro[1m]
```

the agent file should still contain:

```yaml
model: opus
```

The agent definition describes the logical model family.

The provider launcher determines the underlying model.

---

# Example — All tools, no memory

```markdown
---
name: general-implementer
description: Handles broad implementation and debugging tasks.
model: inherit
color: blue
---

You are a general implementation specialist.

Investigate the requested task thoroughly, make appropriate changes, validate the result, and report what you changed.
```

Notice:

- No `tools` field because `All` was selected.
- No `memory` field because `None` was selected.

---

# Step 10 — Preview

Before writing the file, display a concise configuration summary.

Example:

```text
Agent configuration

Name        : backend-developer
Scope       : Project
Destination : <project>/.claude/agents/backend-developer.md
Model       : opus
Tools       : Read, Grep, Glob, LSP, Edit, Write, Bash, PowerShell
Color       : green — subagent display color
Memory      : project
MCP         : none
```

Then show the complete proposed agent Markdown file.

Clearly distinguish:

```text
Model alias
```

from:

```text
Underlying provider model
```

Do not try to determine the latter.

---

# Step 11 — Existing file protection

Before writing, check whether the destination already exists.

If it does not exist, proceed after the normal final confirmation.

If it exists:

- Tell the user the exact path.
- Do not overwrite it automatically.
- Require explicit overwrite confirmation.
- Allow the user to choose another agent name instead.

Never silently replace an existing agent.

---

# Step 12 — Write the file

Create the appropriate directory if necessary.

For user scope:

```text
~/.claude/agents/
```

For project scope:

```text
${CLAUDE_PROJECT_DIR}/.claude/agents/
```

Write the file as UTF-8 text.

The opening:

```text
---
```

must be the first line of the file.

Do not place a blank line, BOM-related text, heading, or comment before the opening YAML delimiter.

---

# Step 13 — Verify the generated file

Read the generated file back after writing it.

Verify:

- YAML frontmatter starts on line 1.
- `name` exists.
- `description` exists.
- Agent name does not begin with `-`.
- Agent name does not contain `:`.
- `model` contains the selected alias.
- Provider model IDs were not substituted.
- `color` contains the selected display color.
- `memory: none` was not written.
- `memory`, when present, is one of:
  - `project`
  - `user`
  - `local`
- `tools` is omitted when `All` was selected.
- Tool entries are not duplicated.
- `mcpServers` is included only when required.
- The Markdown system prompt exists after the YAML frontmatter.

---

# Optional Claude validation

If command execution is available, optionally validate the agents directory.

For project scope:

```text
claude plugin validate .claude/agents
```

For user scope, validate the corresponding user agents directory.

Treat validation failures as issues to report.

Do not automatically delete an agent because validation fails.

Instead:

1. Report the validation output.
2. Inspect the generated frontmatter.
3. Fix the definition when the problem is clear.
4. Re-run validation if appropriate.

---

# Newly created agents directory

Claude Code watches existing agent directories for changes.

If this wizard creates a previously nonexistent:

```text
.claude/agents/
```

or:

```text
~/.claude/agents/
```

directory during the current Claude Code session, tell the user that Claude Code may need to be restarted once for that newly created directory to be discovered.

If the directory already existed, normal agent-file changes are generally detected without requiring a restart.

---

# Completion message

After successful creation, report:

```text
Agent created successfully

Name        : <name>
Scope       : <user|project>
Path        : <full path>
Model       : <alias>
Color       : <color>
Memory      : <project|user|local|none>
Tools       : <tool policy>
MCP         : <servers or none>
```

For color, describe it as:

```text
Display color used in Claude Code's task list and transcript
```

Example:

```text
Color : purple — visual identifier in task list/transcript
```

---

# Important safety rules

Never place any of the following into generated agent files:

- API keys
- Authentication tokens
- Passwords
- Provider secrets
- `.env` contents
- Private credentials

Never copy provider credentials from launcher scripts into an agent.

Never modify the user's provider configuration merely because an agent selects Opus, Sonnet, Haiku, or inherit.

---

# Important compatibility rules

Always preserve these model aliases literally:

```text
opus
sonnet
haiku
inherit
```

Always preserve these supported display colors literally:

```text
red
blue
green
yellow
purple
orange
pink
cyan
```

Persistent memory accepts:

```text
project
user
local
```

No-memory behavior is represented by omitting `memory`.

All-tools behavior is represented by omitting `tools`.

---

# Final principle

Agent Builder manages the logical definition of a Claude Code custom subagent.

It should determine:

- What the agent does
- Where the agent is stored
- Which tools it receives
- Which logical model alias it requests
- Which display color identifies it
- Whether it has persistent memory
- Which MCP servers it may use

It should not determine:

- Which external AI provider the user launches Claude Code through
- Which API key is active
- Which physical provider model an alias resolves to
- How provider billing works
- How provider launcher scripts are configured

Keep those concerns separate.