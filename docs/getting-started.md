# Getting started

Full install and quickstart detail. The README has the terse version.

## Install

### Codex local plugin

From the repo root:

```bash
codex plugin marketplace add ./
codex
```

Open `/plugins`, install **KB Skills Bioinformatics**, then invoke skills explicitly with `$read-paper`, `$build-knowledge`, `$run-pipeline`, etc.

The root Codex plugin manifest lives at `.codex-plugin/plugin.json`. The installable Codex package lives under `codex/` so current Codex CLIs can resolve a non-empty local marketplace path, and its adapter skills are generated into `codex/skills/` from the Claude-facing `skills/` tree.

### Claude plugin

```bash
/plugin marketplace add yyw-informatics/kb-skills-bioinformatics
/plugin install kb-skills-bioinformatics@yyw-informatics
```

Skills become available as `/kb-skills-bioinformatics:read-paper`, etc. The Claude plugin manifest is `.claude-plugin/plugin.json`.

### Claude symlink

```bash
git clone <repo-url> ~/code/kb-skills-bioinformatics

# User-wide (available in any project)
ln -s ~/code/kb-skills-bioinformatics/skills ~/.claude/skills

# Or per-project
ln -s ~/code/kb-skills-bioinformatics/skills .claude/skills
```

Skills become available as `/read-paper`, `/build-knowledge`, etc.

To update either local install: `git -C ~/code/kb-skills-bioinformatics pull`. Symlinks track the live tree, no relink needed. After changing source skills, run `python3 scripts/sync_codex_skills.py` to refresh Codex adapters.

## Quickstart

In a new project directory:

```bash
mkdir my-project && cd my-project
mkdir knowledge_base projects
```

Drop your method-paper PDFs in the root, then:

### Codex

```bash
# Build a knowledge base entry for one method
$build-knowledge totalVI.pdf

# Set up a project context
mkdir projects/my_study
cp <repo>/templates/project-context.md projects/my_study/context.md
# Edit projects/my_study/context.md to describe your data

# Mine biology papers for actionable findings
$mine-paper --all projects/my_study/context.md --project=my_study

# Cross-paper synthesis
$synthesize-literature projects/my_study/context.md --project=my_study

# Evaluate which methods fit your project
$evaluate-fit --all projects/my_study/context.md --project=my_study

# Produce an integrated analysis plan
$design-analysis projects/my_study/literature/0_synthesis_literature.md \
                 projects/my_study/context.md \
                 --project=my_study
```

Run the whole Codex project pipeline in one command:

```bash
# Gated: same as running each skill by hand, but chained
$run-pipeline projects/my_study/context.md --project=my_study

# End-to-end with default ensemble
$run-pipeline projects/my_study/context.md --project=my_study --auto

# End-to-end + build new KB entries, skipping figure extraction
$run-pipeline projects/my_study/context.md --project=my_study \
              --auto --build-kb=totalVI.pdf,dsb.pdf --skip-figures
```

### Claude

```bash
# Build a knowledge base entry for one method
/build-knowledge totalVI.pdf

# Set up a project context
mkdir projects/my_study
cp <repo>/templates/project-context.md projects/my_study/context.md
# Edit projects/my_study/context.md to describe your data

# Mine biology papers for actionable findings
/mine-paper --all projects/my_study/context.md --project=my_study

# Cross-paper synthesis
/synthesize-literature projects/my_study/context.md --project=my_study

# Evaluate which methods fit your project
/evaluate-fit --all projects/my_study/context.md --project=my_study

# Produce an integrated analysis plan
/design-analysis projects/my_study/literature/0_synthesis_literature.md \
                 projects/my_study/context.md \
                 --project=my_study
```

Run the whole Claude project pipeline in one command:

```bash
# Gated: same as running each skill by hand, but chained
/run-pipeline projects/my_study/context.md --project=my_study

# End-to-end with default ensemble
/run-pipeline projects/my_study/context.md --project=my_study --auto

# End-to-end + build new KB entries, skipping figure extraction
/run-pipeline projects/my_study/context.md --project=my_study \
              --auto --build-kb=totalVI.pdf,dsb.pdf --skip-figures
```

`--skip-figures` is opt-in (default off); pair it with `--build-kb` when you don't need figure documentation for human reading. `figures.md` isn't read by `/evaluate-fit` or `/design-analysis`, so when you only need the KB to feed downstream skills, the flag saves the per-method `/extract-figures` tokens. It propagates to every per-method build the orchestrator spawns; harmonization and the final review treat `figures.md` as absent for those methods.

Each skill's `SKILL.md` documents its prerequisites, arguments, and outputs. See [../skills/run-pipeline/SKILL.md](../skills/run-pipeline/SKILL.md) for the orchestrator and [workflow.md](workflow.md) for the per-phase deep dive.
