# Contributing

Thanks for your interest in improving kb-skills-bioinformatics. This doc covers the layout, how to add or modify a skill, and the conventions to follow before opening a PR.

## Repository overview

```
.claude-plugin/plugin.json       # Claude plugin manifest
.codex-plugin/plugin.json        # Codex plugin manifest (root)
.agents/plugins/marketplace.json # local Codex marketplace entry
skills/                          # CANONICAL source for all skills (Claude-compatible)
codex/
  .codex-plugin/plugin.json      # installable Codex package manifest
  skills/                        # GENERATED Codex adapter mirror — do not hand-edit
scripts/
  sync_codex_skills.py           # regenerate or check the Codex adapter mirror
  validate_codex_plugin.py       # validate Codex packaging
templates/                       # drop-in files for downstream projects
docs/                            # workflow, getting-started, context-fields, examples
```

`skills/<name>/SKILL.md` is the source of truth for every skill. The `codex/skills/` mirror is generated from it.

## Adding or modifying a skill

1. **Create or edit `skills/<name>/SKILL.md`.** Frontmatter must include `name` and `description`. Any additional structure (prerequisites, arguments, outputs, examples) lives in the markdown body.

2. **Regenerate the Codex adapter mirror.** The Codex package can't be hand-edited — it's derived from `skills/`:
   ```bash
   python3 scripts/sync_codex_skills.py
   ```
   This rewrites `codex/skills/<name>/SKILL.md` for every skill, translating Claude-style `/skill-name` references to Codex-style `$skill-name` where appropriate. Commit the regenerated files alongside your source edits.

3. **Validate Codex packaging.** Confirms the manifests, marketplace entry, and adapter mirror are mutually consistent:
   ```bash
   python3 scripts/validate_codex_plugin.py
   ```

4. **Check for drift before pushing.** `--check` exits non-zero if the mirror is out of sync — useful as a pre-push or CI check:
   ```bash
   python3 scripts/sync_codex_skills.py --check
   ```

5. **Update the templates if the skill list changed.** When you add, remove, or rename a top-level skill, update both:
   - [templates/CLAUDE.md](templates/CLAUDE.md) — the skill-reference table
   - [templates/AGENTS.md](templates/AGENTS.md) — the Codex equivalent

   Sub-skills invoked only by `/build-knowledge` (e.g., `/read-paper`, `/understand-theory`) are listed compactly and don't need per-skill rows.

6. **Update docs if your change is user-visible.** If you've changed a phase of the project pipeline, update [docs/workflow.md](docs/workflow.md). If your skill reads new fields from `context.md`, update [docs/context-fields.md](docs/context-fields.md). If install or quickstart changes, update [docs/getting-started.md](docs/getting-started.md) and the README's terse counterparts.

## Documentation conventions

- **`SKILL.md` is canonical.** Per-skill prerequisites, arguments, outputs, and examples live there. Don't duplicate skill specs into the README, templates, or docs — link to `SKILL.md` instead.
- **Templates are short and structural.** `templates/CLAUDE.md` and `templates/AGENTS.md` give a downstream project enough to navigate (typical sequence + skill reference table + directory layout), not full skill specs.
- **README is question-driven.** Reader questions get short answers; depth lives in `docs/`.
- **Use markdown tables, not bullet lists, for skill references.** Tables are scannable; bullets buried in prose are not.

## Commit and PR guidance

- Keep commit messages general and focused on the change's purpose, not the literal diff (e.g., "polish skill docs and README" rather than "rename X to Y in three files").
- One logical change per commit when reasonable.
- Open a PR against `main`. Describe the user-visible effect, not the implementation.

## Project working-directory layout

The skills assume a downstream user's directory follows the layout in [templates/directory-layout.md](templates/directory-layout.md). If you change what a skill writes or where, update that doc — downstream users will check it.

## License

By contributing, you agree your contributions are licensed under the project's MIT [LICENSE](LICENSE).
