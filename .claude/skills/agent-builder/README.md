# Claude Code Agent Builder

Interactive custom-subagent builder for Claude Code.

This skill provides a replacement for the old interactive `/agents` creation wizard.

Current Claude Code versions still support custom subagents, but the older `/agents` terminal creation wizard is no longer the normal creation workflow.

Agent Builder restores that experience as a reusable Claude Code skill:

```text
/agent-builder
```

It interactively asks how the agent should be configured and then creates a normal Claude Code agent Markdown file.

---

# Features

The wizard asks for:

- Agent scope
- Agent name
- Agent purpose
- Agent instructions
- Tool access
- Model
- Display color
- Persistent memory
- MCP access
- Final confirmation before writing

The resulting agent is a standard Claude Code custom subagent.

---

# Agent scopes

Agent Builder can create agents at either level.

## User agent

Stored at:

```text
~/.claude/agents/<agent-name>.md
```

On Windows this normally corresponds to:

```text
C:\Users\<username>\.claude\agents\<agent-name>.md
```

User agents are available across projects on that machine.

---

## Project agent

Stored at:

```text
<project>\.claude\agents\<agent-name>.md
```

Project agents belong to the repository and can normally be committed with the project.

---

# Skill installation scopes

The Agent Builder skill itself can also be installed at user level, project level, or both.

## User-level skill

```text
~/.claude/skills/agent-builder/SKILL.md
```

Windows example:

```text
C:\Users\Administrator\.claude\skills\agent-builder\SKILL.md
```

This makes `/agent-builder` available across projects.

---

## Project-level skill

```text
<project>\.claude\skills\agent-builder\SKILL.md
```

Example:

```text
expense-tracker
└── .claude
    └── skills
        └── agent-builder
            └── SKILL.md
```

The project copy can be committed so the project carries its own Agent Builder definition.

---

# Important distinction: skill vs agent

The Agent Builder **skill** lives under:

```text
.claude/skills/
```

or:

```text
~/.claude/skills/
```

The custom agents it creates live under:

```text
.claude/agents/
```

or:

```text
~/.claude/agents/
```

These are separate concepts.

Example:

```text
~/.claude/
├── skills/
│   └── agent-builder/
│       └── SKILL.md
│
└── agents/
    ├── code-reviewer.md
    ├── backend-developer.md
    └── debugger.md
```

---

# No settings.json modification required

The skill does not need to modify your Claude Code provider configuration.

It should not rewrite:

```text
~/.claude/settings.json
.claude/settings.json
settings.local.json
.env
```

simply to create an agent.

Agent definitions are stored as Markdown files under the agent directories.

---

# Using the wizard

Start Claude Code and run:

```text
/agent-builder
```

The wizard walks through the agent configuration interactively.

A typical session conceptually looks like:

```text
Agent Builder

Where should this agent be stored?

> Project
  User
```

Then:

```text
Agent name:
backend-developer
```

Then:

```text
What should this agent specialize in?
Backend implementation, API development, debugging, and tests.
```

Then tool selection:

```text
Select tool categories:

[x] Edit
[x] Execution
[ ] Read-only
[ ] MCP
[ ] Others
```

Then model:

```text
Select model:

[ ] Sonnet
[x] Opus
[ ] Haiku
[ ] Inherit from parent
```

Then display color:

```text
Select display color:

[ ] Red
[ ] Blue
[x] Green
[ ] Yellow
[ ] Purple
[ ] Orange
[ ] Pink
[ ] Cyan
```

Then memory:

```text
Select persistent memory:

[x] Project
[ ] None
[ ] User
[ ] Local
```

Finally the wizard shows the complete definition before creating the file.

---

# Tool categories

Agent Builder provides convenient tool groups.

## All

Selecting:

```text
All
```

means the generated agent does not contain a `tools` field.

Example:

```yaml
---
name: general-agent
description: Handles general implementation work.
model: inherit
color: blue
---
```

Claude Code then gives the agent the tool pool available to subagents in the current session.

This avoids hardcoding every possible current and future tool.

---

# Read-only

Typical tool set:

```text
Read
Grep
Glob
LSP
WebFetch
WebSearch
```

Example:

```yaml
tools: Read, Grep, Glob, LSP, WebFetch, WebSearch
```

Useful for:

- Research agents
- Code reviewers
- Architecture reviewers
- Dependency researchers
- Investigation agents

---

# Edit

Typical tool set:

```text
Read
Grep
Glob
LSP
Edit
Write
NotebookEdit
```

Example:

```yaml
tools: Read, Grep, Glob, LSP, Edit, Write, NotebookEdit
```

Useful for agents that need to modify files.

---

# Execution

Typical tool set:

```text
Read
Grep
Glob
LSP
Bash
PowerShell
```

Example:

```yaml
tools: Read, Grep, Glob, LSP, Bash, PowerShell
```

Useful for:

- Tests
- Builds
- Git inspection
- Package managers
- Development scripts
- Validation commands

---

# Combined tools

Categories can be combined.

For example:

```text
Edit + Execution
```

can produce:

```yaml
tools: Read, Grep, Glob, LSP, Edit, Write, NotebookEdit, Bash, PowerShell
```

Duplicate tools are removed.

---

# MCP tools

Agent Builder can also give an agent access to configured MCP servers.

For example, if a configured server is named:

```text
github
```

the generated agent may contain:

```yaml
tools: Read, Grep, Glob, mcp__github
mcpServers:
  - github
```

Multiple servers are supported:

```yaml
tools: Read, Grep, Glob, mcp__github, mcp__playwright
mcpServers:
  - github
  - playwright
```

Agent Builder does not ask for or store MCP credentials.

It works with already-configured MCP servers.

---

# Other tools

The wizard can also add specific tools outside the predefined groups.

Examples include:

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

These are not automatically enabled.

Choose them only when the agent needs them.

---

# Nested subagents

Adding:

```text
Agent
```

to the agent's tool list allows the agent to delegate work to other subagents where Claude Code's current subagent rules permit it.

Example:

```yaml
tools: Read, Grep, Glob, Agent
```

A normal specialist does not necessarily need this.

Enable it only when you want an agent that can coordinate other agents.

---

# Model selection

The wizard intentionally offers:

```text
Sonnet
Opus
Haiku
Inherit from parent
```

These generate:

```yaml
model: sonnet
```

```yaml
model: opus
```

```yaml
model: haiku
```

or:

```yaml
model: inherit
```

---

# Why Agent Builder stores aliases

Agent Builder deliberately stores logical Claude Code aliases instead of physical model IDs.

This is particularly important when Claude Code is started through custom provider scripts.

For example, your environment might conceptually map:

```text
Opus   -> mimo-v2.6-pro[1m]
Sonnet -> mimo-v2.6-pro[1m]
Haiku  -> mimo-v2.6-flash
```

The generated agent should still contain:

```yaml
model: opus
```

rather than:

```yaml
model: mimo-v2.6-pro[1m]
```

This keeps the agent definition independent from the provider.

---

# Provider switching

A provider launcher may change things such as:

```text
ANTHROPIC_BASE_URL
ANTHROPIC_AUTH_TOKEN
ANTHROPIC_MODEL
ANTHROPIC_DEFAULT_OPUS_MODEL
ANTHROPIC_DEFAULT_SONNET_MODEL
ANTHROPIC_DEFAULT_HAIKU_MODEL
CLAUDE_CODE_SUBAGENT_MODEL
```

Agent Builder does not modify these values.

This separation allows the same agent library to work with different Claude Code launch environments.

For example, the same:

```yaml
model: opus
```

agent can be used when Claude Code is launched through:

```text
Anthropic
```

or through another compatible provider whose launcher maps the Opus alias to another model.

---

# Inherit from parent

Choosing:

```text
Inherit from parent
```

generates:

```yaml
model: inherit
```

This tells Claude Code to use the parent/main conversation's model according to Claude Code's current model-resolution behavior.

This can be useful when you want the agent automatically to follow whichever model the current provider/session is using.

---

# Display colors

Every generated agent can have a display color.

Supported choices in the wizard are:

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

Example:

```yaml
color: purple
```

---

# What the color does

The `color` field controls the subagent's display color in Claude Code's:

- Task list
- Transcript

This makes different subagents easier to visually distinguish while Claude Code is showing their activity.

For example:

```yaml
---
name: backend-developer
description: Implements backend application features.
model: opus
color: green
---
```

The agent uses green as its Claude Code display identifier.

The color should be thought of as:

```text
Agent visual identifier
```

It does **not** mean that every line of terminal output is necessarily recolored.

---

# Optional color convention

You can choose any supported color for any agent.

If you want a consistent visual system, one possible convention is:

| Color | Possible meaning |
|---|---|
| Blue | Research |
| Green | Implementation |
| Yellow | Testing |
| Red | Debugging |
| Purple | Architecture |
| Cyan | Review |
| Orange | Operations |
| Pink | Documentation |

This is only a suggested convention.

Claude Code itself does not require these meanings.

For example:

```yaml
name: researcher
color: blue
```

```yaml
name: backend-developer
color: green
```

```yaml
name: test-engineer
color: yellow
```

```yaml
name: debugger
color: red
```

```yaml
name: architect
color: purple
```

This can be particularly useful when several agents are active during one workflow.

---

# Persistent agent memory

Agent Builder supports:

```text
Project
User
Local
None
```

---

# Project memory

Selecting:

```text
Project
```

generates:

```yaml
memory: project
```

Storage:

```text
.claude/agent-memory/<agent-name>/
```

Use this for knowledge specific to the current project.

Examples:

- Project architecture
- Important code locations
- Coding conventions
- Database structure
- Recurring debugging findings
- Project-specific workflows

Project memory can be shared through version control if desired.

---

# User memory

Selecting:

```text
User
```

generates:

```yaml
memory: user
```

Storage:

```text
~/.claude/agent-memory/<agent-name>/
```

Use this when the agent should retain useful knowledge across multiple projects.

---

# Local memory

Selecting:

```text
Local
```

generates:

```yaml
memory: local
```

Storage:

```text
.claude/agent-memory-local/<agent-name>/
```

Use this when memory should remain specific to the current project but should not normally be committed.

---

# No memory

Selecting:

```text
None
```

does **not** generate:

```yaml
memory: none
```

Instead the `memory` field is omitted completely.

Example:

```yaml
---
name: temporary-researcher
description: Performs isolated research tasks.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: haiku
color: blue
---
```

---

# Memory-enabled agents

When persistent memory is enabled, Agent Builder can add instructions such as:

```text
Consult relevant persistent memory before starting work when useful.

Update memory with durable knowledge such as architecture decisions,
project conventions, important code locations, and recurring findings.

Do not store API keys, credentials, secrets, or temporary task noise.
```

This helps the agent use its persistent memory deliberately instead of accumulating unnecessary information.

---

# Example generated agent

A project backend-development agent might look like:

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
- Follow established project architecture and coding conventions.
- Make focused and maintainable changes.
- Avoid unrelated refactoring.
- Run relevant tests or validation when possible.
- Report what changed and any remaining concerns.

Use your persistent agent memory for durable project-specific knowledge.

Consult memory when useful and update it with important architecture,
conventions, recurring implementation patterns, and significant findings.

Never store API keys, credentials, or secrets in memory.
```

---

# Example read-only agent

```markdown
---
name: code-reviewer
description: Reviews changes for correctness, maintainability, security, and test coverage.
tools: Read, Grep, Glob, LSP
model: sonnet
color: cyan
memory: project
---

You are a focused code-review specialist.

Inspect the relevant implementation and provide concise, prioritized,
actionable findings.

Do not modify project files.

Use persistent memory to retain useful project-specific review patterns
and architectural knowledge.
```

---

# Example no-memory agent

```markdown
---
name: quick-researcher
description: Performs focused codebase and documentation research.
tools: Read, Grep, Glob, WebFetch, WebSearch
model: haiku
color: blue
---

Research the requested topic efficiently.

Return the relevant findings, important source locations, and any
remaining uncertainty.
```

---

# Example inherited-model agent

```markdown
---
name: general-specialist
description: Handles specialized implementation tasks using the current session model.
model: inherit
color: purple
memory: project
---

Handle the delegated task using the current project conventions.

Investigate before making changes and report the result clearly.
```

---

# Generated file format

Agent Builder generates standard Markdown agent files with YAML frontmatter.

General structure:

```markdown
---
name: agent-name
description: When Claude should delegate to this agent
tools: Read, Grep, Glob
model: sonnet
color: cyan
memory: project
---

Agent system instructions go here.
```

Only:

```text
name
description
```

are fundamental required identification fields for the standard file format.

Agent Builder adds the selected configuration fields as needed.

---

# Important omission rules

## All tools

When the user chooses:

```text
All
```

the `tools` field is omitted.

Do not write:

```yaml
tools: all
```

---

## No memory

When the user chooses:

```text
None
```

the `memory` field is omitted.

Do not write:

```yaml
memory: none
```

---

## No MCP

When no MCP server is selected, omit:

```yaml
mcpServers:
```

---

# Existing files

Agent Builder never silently overwrites an existing agent.

If this already exists:

```text
.claude/agents/backend-developer.md
```

the wizard should tell you and ask whether you want to:

- Replace it
- Change the name
- Cancel

Explicit confirmation is required before replacing an agent.

---

# Preview before creation

Before writing anything, the wizard displays a summary similar to:

```text
Agent configuration

Name        : backend-developer
Scope       : Project
Destination : .claude/agents/backend-developer.md
Model       : opus
Tools       : Edit + Execution
Color       : green
Memory      : project
MCP         : none
```

The color represents the agent's visual identifier in Claude Code's task list and transcript.

Then the complete Markdown definition is shown for review.

---

# Validation

After creating the file, Agent Builder reads it back and verifies:

- YAML begins on line 1.
- `name` exists.
- `description` exists.
- Agent name is valid.
- Model alias was preserved.
- Display color was preserved.
- Tool list contains no duplicates.
- `memory: none` was not generated.
- `tools: all` was not generated.
- MCP configuration matches the selected servers.
- The system prompt exists.

When appropriate, Claude Code's agent-directory validation can also be used.

---

# Restart behavior

Claude Code watches existing agent directories and can normally detect newly added or modified agent files.

A restart may be necessary when:

```text
~/.claude/agents/
```

or:

```text
.claude/agents/
```

did not exist when the current Claude Code session started and Agent Builder creates that directory for the first time.

After the directory exists, later agent-file edits are normally detected automatically.

---

# Windows example

For a project such as:

```text
C:\Lalit-VM-1-Win11Pro-Spectra-Technologies-Pvt-Ltd\
Claude-Code-CLI\
campus-x-Claude-CLI\
expense-tracker
```

a project skill would be:

```text
expense-tracker\
.claude\
skills\
agent-builder\
SKILL.md
```

and a generated project agent might be:

```text
expense-tracker\
.claude\
agents\
backend-developer.md
```

A user-level copy of Agent Builder would normally be:

```text
C:\Users\Administrator\
.claude\
skills\
agent-builder\
SKILL.md
```

and a user agent would normally be:

```text
C:\Users\Administrator\
.claude\
agents\
backend-developer.md
```

---

# Recommended setup

For your workflow, installing Agent Builder at both scopes is reasonable:

```text
User:
~/.claude/skills/agent-builder/SKILL.md
```

and:

```text
Project:
<project>/.claude/skills/agent-builder/SKILL.md
```

Keep the two `SKILL.md` files identical unless a particular project needs customized behavior.

User-level agents can then contain reusable specialists, while project-level agents can contain roles specific to a repository.

Example:

```text
~/.claude/agents/
├── general-code-reviewer.md
├── debugger.md
└── researcher.md
```

while:

```text
expense-tracker/.claude/agents/
├── expense-api-specialist.md
├── database-specialist.md
└── frontend-specialist.md
```

---

# Provider-safe architecture

The intended architecture is:

```text
                    ┌──────────────────────────────┐
                    │ Provider launcher script     │
                    │                              │
                    │ API key                      │
                    │ Base URL                     │
                    │ Alias -> physical model map  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Claude Code                  │
                    │                              │
                    │ opus / sonnet / haiku        │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Custom agent                 │
                    │                              │
                    │ model: opus                  │
                    │ color: green                 │
                    │ memory: project              │
                    └──────────────────────────────┘
```

The custom agent does not need to know whether `opus` currently maps to an Anthropic model, MiMo model, or another compatible provider model.

That mapping belongs to the launcher/provider layer.

---

# Security

Agent Builder should never write secrets into an agent definition.

Do not store:

```text
API keys
Authentication tokens
Passwords
Provider secrets
.env contents
Private credentials
```

inside:

```text
.claude/agents/
```

or:

```text
~/.claude/agents/
```

Agents should reference tools and behavior, not credentials.

---

# Summary

Agent Builder gives you an interactive replacement for the removed `/agents` creation wizard.

It supports:

```text
Scope
  ├── User
  └── Project

Tools
  ├── All
  ├── Read-only
  ├── Edit
  ├── Execution
  ├── MCP
  └── Others

Models
  ├── Sonnet
  ├── Opus
  ├── Haiku
  └── Inherit from parent

Colors
  ├── Red
  ├── Blue
  ├── Green
  ├── Yellow
  ├── Purple
  ├── Orange
  ├── Pink
  └── Cyan

Memory
  ├── Project
  ├── None
  ├── User
  └── Local
```

The generated agents remain independent of the underlying API provider because their model selection uses Claude Code aliases rather than provider-specific model IDs.

The selected `color` gives each agent a visual identity in Claude Code's task list and transcript.

Run:

```text
/agent-builder
```

to create an agent.