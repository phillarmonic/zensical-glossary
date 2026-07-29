# drun Basics for AI Agents

This repository uses drun for automation.
The CLI binary is `xdrun`.

## What to Know First

- Main drun spec location: `.drun/spec.drun`
- Default initialization command: `xdrun --init`
- List available tasks: `xdrun --list`
- Run a task: `xdrun <task>`
- Pass task parameters as `key=value`, for example `xdrun deploy environment=production`
- Keep CLI behavior flags separate, for example `xdrun deploy environment=production --dry-run`
- Official upstream repository for clarification and broader docs: https://github.com/phillarmonic/drun

## Recommended Workflow

1. Read the existing drun file before making changes.
2. If there is no spec yet, initialize one with `xdrun --init`.
3. Use `xdrun --list` to inspect task names instead of guessing.
4. For platform-specific workflows, prefer separate declarations with `@platform(...)` instead of mixing OS branches into one task when the behavior is substantially different.
5. Use canonical platform names in new specs: `linux`, `mac`, `windows`. Legacy `darwin` still parses, but prefer `mac` in new code and examples.
6. If a task family includes both platform-tagged variants and one unannotated task, drun resolves the exact platform variant first and uses the unannotated task as the fallback.
7. When adding hard dependencies, declare them with `requires tools:`.
8. Prefer small, readable tasks that explain intent with `means`, `info`, and `step`.
9. For AI-driven CI or noisy checks, prefer tasks declared with `mode "ci"` so successful shell stdout/stderr stays buffered and only failure output is emitted.
10. After editing a spec, run the narrowest relevant `xdrun` command to verify behavior.

## Interpolation and Variables

- drun interpolation inside strings commonly uses `{$name}` for task/project variables.
- Environment variables can be referenced with shell-style syntax such as `${USER}` or `${HOME:-/tmp}`.
- Conditional interpolation is available for inline flags and small config choices, for example `{$debug ? '--debug' : ''}` or `{if $environment is 'production' then 'prod.yml' else 'dev.yml'}`.
- Secrets can be read in interpolation with `secret(...)`, for example `{secret('api_key')}` or `{secret('webhook_url', 'https://default.example')}`.
- Undefined drun variables are strict by default. Prefer declaring them with `requires $name` or `given $name defaults to ...` instead of relying on missing values.
- Keep interpolation readable. If an expression becomes hard to scan inline, compute it with `set $name to "..."` first and reuse the variable.
- Multi-line `run "..."` strings support interpolation too, which is often cleaner than building one huge shell line.
- When mixing drun interpolation with shell syntax, keep the whole command explicit and quoted so both layers are obvious during review.

Useful examples at the https://github.com/phillarmonic/drun/tree/master/examples repository:
- `examples/03-interpolation.drun` for basic variable interpolation
- `examples/51-env-var-interpolation.drun` for environment variables
- `examples/52-conditional-interpolation.drun` for ternary and `if/then/else` expressions
- `examples/62-secrets-interpolation.drun` for `secret(...)` usage
- `examples/63-multiline-strings.drun` for multi-line commands with interpolation

## Tool Checks

Prefer declarative requirements when a task depends on a binary or minimum version:

```drun
project "my-app" version "1.0":
  requires tools:
    go >= "1.21"
    docker
```

Task-level checks are also valid:

```drun
task "test" means "Run the test suite":
  requires tools:
    go
  run "go test ./..."
```

## Writing Good drun Specs

- Keep the file readable at a glance.
- Prefer task names that match user intent.
- If two platforms need the same user-facing workflow name, use duplicate task names with disjoint `@platform(...)` annotations so `xdrun <task>` resolves the correct variant automatically.
- A task family may also include one unannotated task as a fallback when no platform-specific variant matches.
- Use `given $name defaults to ...` for optional parameters.
- Use `requires $name` for values that must be supplied at runtime instead of silently falling back inside shell.
- Prefer interpolation for task inputs and shell env expansion for true process environment values.
- For complex command assembly, compute intermediate values with `set` before the `run` step rather than hiding logic in one long string.
- Use `call task ...` instead of duplicating steps across tasks.
- Use `mode "ci"` for noisy validation tasks when you want to save output tokens during successful runs.
- Keep shell commands explicit inside `run "..."`.

## Lifecycle Basics

- Bootstrap a repository with `xdrun --init`.
- Evolve `.drun/spec.drun` as the source of truth for project automation.
- Use `xdrun --list` as the quickest way to discover available workflows.
- For CI-style tasks, `mode "ci"` buffers normal shell stdout/stderr and only prints that buffered output when a command fails, which reduces noisy output and saves tokens for AI runs.
- Use targeted runs such as `xdrun test` or `xdrun build --dry-run` to validate changes.
- If the local repository guidance is incomplete, check the official upstream repo for clarification: https://github.com/phillarmonic/drun

## Example Starter Spec

```drun
version: 2.0

project "my-app" version "1.0":
  requires tools:
    go

task "default" means "Show available automation":
  info "Run xdrun --list to inspect tasks"

task "test" means "Run tests":
  run "go test ./..."

@platform("linux", "mac")
task "shell" means "Open a Unix shell":
  run "bash" attached

@platform("windows")
task "shell" means "Open PowerShell":
  run "pwsh.exe" attached

task "ci" mode "ci" means "Run noisy checks with buffered output":
  run "go test ./..."
```

## Git Policy and Hooks

Projects can define git conventions in the project body using the `git policy:` block.
When a git policy is defined, use `xdrun cmd:hook install` to install drun-managed git hooks (like pre-commit, commit-msg, pre-push) that enforce these conventions.

```drun
project "my-app" version "1.0":
  git policy:
    branch:
      default branches: "master", "main"
      protected branches: "master", "main"
      naming: "{type}/{identifier}-{description}"
      types: "feat", "fix", "chore"
    commit:
      messages: "{identifier}: {message}"
      extract identifier from branch
      enforce signed commits
```