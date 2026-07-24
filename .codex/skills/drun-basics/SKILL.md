---
name: drun-basics
description: "Use when working in a repository that uses drun or xdrun for automation. Teaches the agent where specs live, how to run tasks, how to pass parameters, and how to verify tool requirements."
---

# drun-basics

Use this skill when the task mentions drun, xdrun, `.drun/spec.drun`, task automation, or repository workflows implemented in drun.

Read `.drun/ai/drun-basics.md` completely before making changes or proposing commands.

Apply the workflow in that guide exactly:
- inspect the existing drun file before editing
- keep task parameters in `key=value` form
- prefer `xdrun --list` and focused task runs for verification
- use `@platform(...)` for platform-specific tasks instead of burying OS differences inside one task
- when a task family mixes platform variants with one unannotated task, drun resolves exact platform match first and uses the unannotated task as the fallback
- use `requires tools:` for hard tool requirements
