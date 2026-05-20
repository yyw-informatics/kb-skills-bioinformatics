# kb-skills-bioinformatics

A literature-review and method-evaluation workflow for bioinformatics, shipped as Claude Code and Codex skills.

These skills turn raw method papers and biology literature into a structured, queryable knowledge base (KB) — and then map that knowledge onto a specific project to produce a code-ready analysis plan. Originally built for single-cell / CITE-seq work; the workflow is method-agnostic.

## Why

### What is this, and who's it for?

Skills for a bench biologist + their computational collaborator (or LLM). You drop in method papers and biology PDFs, describe your project once in a `context.md`, and the skills build a reusable method knowledge base, mine the literature for findings relevant to your project, score each method against your data, and produce an ordered analysis plan.

### What problem does it solve?

Three gaps: too many papers to scan, too many methods to evaluate, and the chasm between "I've read it" and "I have a plan I can implement." Each gap gets its own skill family — literature mining + cross-paper synthesis, method KB + fit scoring, and integrated analysis design.

## How

### How does the pipeline fit together?

Two layers. Layer 1 is a reusable method library (build once per method). Layer 2 is the per-project pipeline driven by your `context.md`.

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

Per-phase narrative and the full skill DAG: [docs/workflow.md](docs/workflow.md).

### How do I install it?

Three options:

- **Codex local plugin** — `codex plugin marketplace add ./ && codex`, then install **KB Skills Bioinformatics** from `/plugins`. Skills as `$read-paper`, `$build-knowledge`, etc.
- **Claude plugin** — `/plugin marketplace add yyw-informatics/kb-skills-bioinformatics && /plugin install kb-skills-bioinformatics@yyw-informatics`. Skills as `/kb-skills-bioinformatics:read-paper`.
- **Claude symlink** — `ln -s ~/code/kb-skills-bioinformatics/skills ~/.claude/skills`. Skills as `/read-paper`.

Detail and update instructions: [docs/getting-started.md](docs/getting-started.md).

### What's the smallest useful run?

One method KB entry + one project + the whole project pipeline in a single command:

```bash
# Claude
/build-knowledge totalVI.pdf
/run-pipeline projects/my_study/context.md --project=my_study --auto

# Codex
$build-knowledge totalVI.pdf
$run-pipeline projects/my_study/context.md --project=my_study --auto
```

You need `projects/my_study/context.md` (copy from [templates/project-context.md](templates/project-context.md); see [docs/context-fields.md](docs/context-fields.md) for which fields drive which skill behaviors) and at least one biology paper in `papers/`. Per-skill walkthrough: [docs/getting-started.md](docs/getting-started.md).

### Should I run skills by hand or use `/run-pipeline`?

`/run-pipeline` chains the four project-pipeline phases (mine → synthesize → evaluate → design) into one invocation and is the right default once the workflow is familiar. Run by hand when iterating on a single phase, debugging a specific output, or learning what each skill does. The orchestrator never reads phase content into its own context — each phase runs as an isolated background agent. Full DAG and per-phase detail: [docs/workflow.md](docs/workflow.md).

### How do I get more reliable results?

Pass `--auto` to `/run-pipeline`. Each integrative output — `0_synthesis_literature.md`, `fitness_summary.md`, `analysis_plan.md` — is then produced by two independent agents with isolated context windows, and resolved by a third adjudicator that reads the source files to settle disagreements and spot-check consensus. A fourth cross-phase auditor checks the three outputs agree at the end.

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

What this catches that a single pass can't:

1. **Real disagreements** between v1 and v2, settled by the adjudicator against source files.
2. **False consensus** — if v1 and v2 both hallucinate the same plausible-sounding claim, the adjudicator spot-checks high-stakes AGREE claims against sources and demotes anything unsupported.
3. **Inter-phase inconsistency** — the cross-phase auditor catches, e.g., a method rated Poor still appearing in the plan, or a marker that won in synthesis but is missing from the plan.

Each adjudication writes an audit log, and the pipeline summary flags any output that warrants closer review and identifies the file to inspect. Rubric detail in [docs/workflow.md](docs/workflow.md).

Only the three integrative outputs are multi-pass. Per-paper mining (`*_intel.md`) and per-method evaluation (`*_fitness_assessment.md`) stay single-pass — those are extraction over many independent items and already get diversity from parallel agents. Cost in `--auto`: roughly 2.5× per ensembled output; everything else unchanged.

## What if

### What if I want to add a new method to the knowledge base?

`/build-knowledge <paper.pdf>` orchestrates `/read-paper` → `/understand-theory` → `/learn-code` → `/extract-figures` → `/harmonize` → `/review-knowledge` for a single method. Each phase runs in its own background context window so a long build doesn't exhaust the orchestrator. Pass `--supplement=<supp.pdf>` to fold in supplementary material, `--repo=<github-url>` to point `/learn-code` at the source, or `--skip-figures` when you only need the KB to feed downstream skills.

---

Each skill's `SKILL.md` documents its prerequisites, arguments, and outputs. Project working-directory layout: [templates/directory-layout.md](templates/directory-layout.md). License: MIT — see [LICENSE](LICENSE).
