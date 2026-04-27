# kb-skills-bioinformatics

A literature-review and method-evaluation workflow for bioinformatics, shipped as Claude Code and Codex skills.

These skills help you turn raw method papers and biology literature into a structured, queryable knowledge base — and then map that knowledge onto a specific project to produce a code-ready analysis plan. Originally built for single-cell / CITE-seq work but the workflow is method-agnostic.

## What you can do

- **Build a method knowledge base** — read a paper PDF, extract concepts, theory, code, and figures into structured markdown
- **Mine biology literature** — extract directly actionable intelligence (gene lists, marker panels, frequencies) from research papers, filtered by your project context
- **Synthesize across papers** — find consensus, conflicts, and novel cross-paper hypotheses
- **Evaluate method fit** — score every method in your KB against your project's data and goals
- **Design analyses** — produce an ordered, code-ready analytical plan that maps each biological hypothesis to a specific bioinformatics method
- **Adapt methods to your data** — generate a preliminary run with real EDA and method-specific configuration
- **Run the whole pipeline end-to-end** — `/run-pipeline` in Claude or `$run-pipeline` in Codex chains the per-project skills end-to-end, with an optional ensemble + adjudicator mode that swaps interactive review gates for two independent runs of each integrative output plus a third independent reviewer

## Pipeline at a glance

Two layers. Layer 1 is a reusable method library; Layer 2 is the per-project analytical workflow. Build Layer 1 once per method, reuse across all your projects.

```
              Layer 1: METHOD KNOWLEDGE  (one-time per method, reusable)
   ──────────────────────────────────────────────────────────────────────

   method paper.pdf ──► /build-knowledge ──► knowledge_base/<method>/
                                              ├── concept.md
                                              ├── theory.md
                                              ├── code.md
                                              └── figures.md   (optional; omit with --skip-figures)

   docs site URL    ──► /index-docs       ──► knowledge_base/ecosystems/<pkg>/


              Layer 2: PROJECT PIPELINE  (per project, driven by context.md)
   ──────────────────────────────────────────────────────────────────────

   biology PDFs                                       context.md
   + context.md                                      (your data,
        │                                            constraints)
        ▼                                                 │
   /mine-paper ──► literature/*_intel.md                  │
                          │                               │
                          ▼                               ▼
                /synthesize-literature              /evaluate-fit ◄── knowledge_base/
                          │                               │
                          ▼                               ▼
            0_synthesis_literature.md          fitness_summary.md
                          │                               │
                          └──────────┬────────────────────┘
                                     ▼
                            /design-analysis
                                     │
                                     ▼
                              analysis_plan.md
                                     │
                                     ▼
                              /adapt-method   (real data, preliminary run)


   ┌──────────────────────────────────────────────────────────────────┐
   │  /run-pipeline  chains the four Layer-2 phases into one command, │
   │                 with optional end-to-end ensemble + adjudicator. │
   └──────────────────────────────────────────────────────────────────┘
```

See [docs/workflow.md](docs/workflow.md) for the full skill DAG and per-phase detail.

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

Once published to a public Git host:

```bash
/plugin marketplace add <your-org>/kb-skills-bioinformatics
/plugin install kb-skills-bioinformatics@<your-org>
```

Skills become available as `/kb-skills-bioinformatics:read-paper`, etc. The Claude plugin manifest remains `.claude-plugin/plugin.json`.

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

### Codex quickstart

```bash
# Build a knowledge base entry for one method
$build-knowledge totalVI.pdf

# Set up a project context (use templates/project-context.md as starting point)
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

### Claude quickstart

```bash
# Build a knowledge base entry for one method
/build-knowledge totalVI.pdf

# Set up a project context (use templates/project-context.md as starting point)
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
# (figures.md isn't read by /evaluate-fit or /design-analysis, so when you
#  only need the KB to feed downstream skills, --skip-figures saves the
#  per-method /extract-figures tokens)
/run-pipeline projects/my_study/context.md --project=my_study \
              --auto --build-kb=totalVI.pdf,dsb.pdf --skip-figures
```

`--skip-figures` is opt-in (default off); pair it with `--build-kb` when you don't need figure documentation for human reading. It propagates to every per-method build the orchestrator spawns; harmonization and the final review treat `figures.md` as absent for those methods.

#### How end-to-end quality control works

In `--auto` mode, each integrative output (`0_synthesis_literature.md`, `fitness_summary.md`, `analysis_plan.md`) is produced by an **ensemble + adjudicator** pattern instead of an interactive review gate:

```
   Step 1: two independent runs
   ─────────────────────────────────────────────────────────────
                            ┌──► Agent v1 ──► output_v1.md
                            │    (fresh context)
   phase input  ────────────┤
   (context.md +            │
    upstream files)         └──► Agent v2 ──► output_v2.md
                                 (fresh context)


   Step 2: independent adjudication
   ─────────────────────────────────────────────────────────────
   output_v1.md  ──┐
                   │
   output_v2.md  ──┼──►  Adjudicator    ──►  output.md
                   │     (fresh context)     (canonical)
   source files  ──┘     - settles DISAGREE
   (intel /               - drops ungrounded   output_adjudication.md
    assessments /           UNIQUE items       (counts → confidence:
    context.md)           - spot-checks         High / Medium / Low,
                            high-stakes         flagged_items)
                            AGREE claims
                            (catches false
                             consensus)
```

Three things happen that an interactive gate or a single-pass run can't:

1. **Real disagreements between v1 and v2** are surfaced. The adjudicator reads source files to settle them.
2. **False consensus is caught.** If v1 and v2 both hallucinate the same plausible-sounding claim, the adjudicator spot-checks the high-stakes "AGREE" claims against source files and demotes anything unsupported.
3. **A deterministic confidence rubric** (counts of AGREE / DISAGREE-resolved / DISAGREE-flagged / UNIQUE-kept / UNIQUE-dropped → `High` / `Medium` / `Low`) is written to the audit log — anyone can recount and verify.

After all phases finish, a **fourth, cross-phase consistency auditor** reads `0_synthesis_literature.md`, `fitness_summary.md`, and `analysis_plan.md` together and verifies they agree on the load-bearing claims (which markers won, which method won, hypothesis-to-method mapping, no use of methods rated Poor / Not Recommended without justification).

If anything is flagged, the pipeline summary tells you exactly which file to open and what to look for. The ensemble + audit cost is roughly 2.5× per ensembled output; per-paper mining and per-method assessments stay single-run.

Each skill's `SKILL.md` documents its prerequisites, arguments, and outputs. Read those for details on individual skills, and [skills/run-pipeline/SKILL.md](skills/run-pipeline/SKILL.md) for the orchestrator.

## Repo layout

```
kb-skills-bioinformatics/
├── .claude-plugin/plugin.json   # Claude plugin manifest
├── .codex-plugin/plugin.json    # Codex plugin manifest
├── .agents/plugins/
│   └── marketplace.json         # repo-local Codex marketplace entry
├── skills/                      # Claude-compatible source skills
├── codex/
│   ├── .codex-plugin/plugin.json # installable Codex package manifest
│   └── skills/                   # generated Codex adapter mirror
├── scripts/
│   ├── sync_codex_skills.py     # regenerate/check Codex adapters
│   └── validate_codex_plugin.py # validate Codex packaging
├── templates/
│   ├── project-context.md       # starting point for projects/<name>/context.md
│   ├── CLAUDE.md                # drop-in for downstream projects
│   ├── AGENTS.md                # Codex equivalent for downstream projects
│   └── directory-layout.md      # explains the convention
├── README.md
└── LICENSE
```

## Convention: project directory layout

These skills assume a working directory with this structure:

```
<your-project>/
├── *.pdf                                  # method papers (for /build-knowledge)
├── papers/                                # biology papers (for /mine-paper)
├── knowledge_base/
│   ├── <method>/                          # one folder per method
│   │   ├── concept.md                     # from /read-paper
│   │   ├── theory.md                      # from /understand-theory
│   │   ├── code.md                        # from /learn-code
│   │   └── figures.md                     # from /extract-figures
│   └── ecosystems/                        # from /index-docs
│       └── <package>/
└── projects/
    └── <project_name>/
        ├── context.md                     # YOUR project context (required input)
        ├── literature/                    # from /mine-paper, /synthesize-literature
        ├── bioinformatics/                # from /evaluate-fit
        ├── analysis_plan.md               # from /design-analysis
        ├── .repo_manifest.md              # from /run-pipeline pre-flight (if --build-kb used)
        └── <method>_adaptation/           # from /adapt-method
```

You don't need to create everything up-front. Skills create their own subdirectories.

## License

MIT — see [LICENSE](LICENSE).
