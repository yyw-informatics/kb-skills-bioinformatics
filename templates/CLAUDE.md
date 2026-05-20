# {Project Name}

> Drop this file at the root of a project directory after installing kb-skills-bioinformatics.
> It tells Claude Code about the workflow conventions used here.

## Workflow

This project uses the [kb-skills-bioinformatics](https://github.com/yyw-informatics/kb-skills-bioinformatics) skills for literature review, method evaluation, and analysis design.

### Typical sequence

Build the method knowledge base once per method (Layer 1), then run the project pipeline per project (Layer 2):

```
Layer 1 (one-time):  /build-knowledge <paper.pdf>
                     /index-docs <docs-url> <package>

Layer 2 (per project): /mine-paper → /synthesize-literature
                                  ↘                       ↘
                                   → /evaluate-fit → /design-analysis → /adapt-method
```

Or chain Layer 2 with `/run-pipeline projects/<name>/context.md --project=<name> --auto`.

### Skill reference

**Layer 1 — method knowledge base** (reusable across projects)

| Skill | Use when | Key output |
|-------|----------|-----------|
| `/build-knowledge <paper.pdf>` | adding a new method to the knowledge base (orchestrates the full build) | `knowledge_base/<method>/{concept,theory,code,figures}.md` |
| `/index-docs <url> <package>` | adding a package's docs as a navigation layer for downstream skills | `knowledge_base/ecosystems/<package>/` |

Sub-skills `/read-paper`, `/understand-theory`, `/learn-code`, `/extract-figures`, `/split-supplement`, `/harmonize`, and `/review-knowledge` are invoked by `/build-knowledge` but can also run standalone — see each skill's `SKILL.md`.

**Layer 2 — project pipeline** (driven by `projects/<name>/context.md`)

| Skill | Use when | Key output |
|-------|----------|-----------|
| `/mine-paper --all projects/<name>/context.md --project=<name>` | extracting actionable findings from biology papers in `papers/` | `projects/<name>/literature/<paper>_intel.md` |
| `/synthesize-literature projects/<name>/context.md --project=<name>` | producing cross-paper consensus, conflicts, and hypothesis ranking | `projects/<name>/literature/0_synthesis_literature.md` |
| `/evaluate-fit --all projects/<name>/context.md --project=<name>` | scoring every method in the knowledge base against the project | `projects/<name>/bioinformatics/<method>_fitness_assessment.md` + `fitness_summary.md` |
| `/design-analysis projects/<name>/literature/0_synthesis_literature.md projects/<name>/context.md --project=<name>` | integrating biology hypotheses + bioinformatics fitness into an ordered, code-ready plan | `projects/<name>/analysis_plan.md` |
| `/adapt-method <method>` | running a chosen method on real data with project-specific EDA | `projects/<name>/<method>_adaptation/` |
| `/run-pipeline projects/<name>/context.md --project=<name>` | chaining mine → synthesize → evaluate → design end-to-end (add `--auto` for ensemble + adjudicator) | all of the above |

Each skill's `SKILL.md` documents prerequisites, arguments, and outputs in detail.

## Directory layout

```
.
├── *.pdf                            # method papers
├── papers/                          # biology papers
├── knowledge_base/                  # built by /read-paper, /build-knowledge, /index-docs
│   ├── <method>/{concept,theory,code,figures}.md
│   └── ecosystems/<package>/
└── projects/<project_name>/
    ├── context.md                   # required input — describes data, panel, comparisons
    ├── literature/                  # built by /mine-paper, /synthesize-literature
    ├── bioinformatics/              # built by /evaluate-fit
    ├── analysis_plan.md             # built by /design-analysis
    └── <method>_adaptation/         # built by /adapt-method
```

`context.md` is the single most important file — every Layer 2 skill reads it. See [docs/context-fields.md](https://github.com/yyw-informatics/kb-skills-bioinformatics/blob/main/docs/context-fields.md) for which fields drive which skill behaviors.

## Project-specific notes

{Replace this section with anything Claude should know about this specific project — e.g., conventions, environment names, things to avoid.}
