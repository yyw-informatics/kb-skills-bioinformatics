# Workflow: from papers to analysis plan

The skills are designed to compose into an end-to-end pipeline. You can use individual skills standalone, but the value compounds when you run them in sequence.

For auto end-to-end runs, `/run-pipeline` wraps the per-project phases (Phases 3–6 below) into one command — see [Phase 8: Auto end-to-end](#phase-8-auto-end-to-end) at the bottom of this doc.

## The big picture

```
                ┌─────────────────────────────────────────────────────┐
                │  Layer 1: METHOD KNOWLEDGE                          │
                │  (one-time per method, shared across projects)     │
                └─────────────────────────────────────────────────────┘
   method paper PDF
        │
        ▼
   /build-knowledge ─┬─→ /read-paper       → concept.md
                    ├─→ /understand-theory → theory.md
                    ├─→ /learn-code        → code.md
                    ├─→ /extract-figures   → figures.md
                    ├─→ /split-supplement  → enhances above (if supp)
                    └─→ /harmonize         → cross-references all of above
                              │
                              ▼
                    /review-knowledge      → quality gate report

   docs site URL
        │
        ▼
   /index-docs                              → ecosystems/<package>/{capabilities,
                                              function_index, workflows, navigation}

                ┌─────────────────────────────────────────────────────┐
                │  Layer 2: PROJECT-SPECIFIC ANALYSIS                 │
                │  (per project, filtered through context.md)         │
                └─────────────────────────────────────────────────────┘
   biology paper PDFs + projects/<name>/context.md
        │
        ▼
   /mine-paper --all                        → projects/<name>/literature/<paper>_intel.md
        │
        ▼
   /synthesize-literature                   → projects/<name>/literature/0_synthesis_literature.md
        │
        ▼
   /evaluate-fit --all                      → projects/<name>/bioinformatics/{method}_fitness_assessment.md
                                              + fitness_summary.md
        │
        ▼ (combines literature synthesis + fitness summary + KB + ecosystems)
   /design-analysis                         → projects/<name>/analysis_plan.md
        │
        ▼
   /adapt-method <method>                   → projects/<name>/<method>_adaptation/
                                              (preliminary run on actual data)
```

## Recommended sequence

### Phase 1: Build your method library (do once, reuse forever)

For each bioinformatics method you care about:

```bash
/build-knowledge totalVI.pdf
/build-knowledge dsb.pdf --supplement=dsb_supp.pdf
/build-knowledge ADTnorm.pdf --repo=https://github.com/yezhengSTAT/ADTnorm
```

`/build-knowledge` orchestrates `/read-paper` → `/understand-theory` → `/learn-code` → `/extract-figures` → optionally `/split-supplement` → `/harmonize`, with `/review-knowledge` as a quality gate after each phase. Each phase runs as a background agent with its own context window, so a long build doesn't exhaust the orchestrator's context.

Pass `--skip-figures` to skip `/extract-figures` for builds where figure documentation isn't useful for downstream work (e.g. you only need the entry to feed `/evaluate-fit` and `/design-analysis`). `figures.md` is omitted, and `/harmonize` + the final review treat it as absent. `/run-pipeline --skip-figures` propagates the flag to every per-method build it spawns.

Optionally index documentation sites for ecosystems you'll use:

```bash
/index-docs https://scanpy.readthedocs.io/en/stable/ scanpy
/index-docs https://docs.scvi-tools.org/en/stable/ scvi-tools
```

### Phase 2: Set up a new project

```bash
mkdir -p projects/my_study
cp templates/project-context.md projects/my_study/context.md
$EDITOR projects/my_study/context.md   # describe your data, panel, comparisons
```

The context file is the single most important input — every project-specific skill reads it. Time spent here pays off across all downstream skills.

### Phase 3: Mine biology literature

Drop biology papers in `papers/` (or root), then:

```bash
/mine-paper --all projects/my_study/context.md --project=my_study --dir=papers/
```

Each paper is screened for relevance against your context. Irrelevant papers get a one-paragraph "NOT USEFUL" verdict and stop. Relevant papers produce structured intel files with directly-actionable items (gene lists, marker panels, gating strategies translated to your panel) and hypothesis-generating items (predictions to test in your data).

### Phase 4: Synthesize across papers

```bash
/synthesize-literature projects/my_study/context.md --project=my_study
```

Produces `0_synthesis_literature.md` — consensus markers (cited by 3+ papers), consolidated gene signatures with provenance, agreement/conflict tables, and a master hypothesis ranking scored by `testability × impact × evidence`.

When you add new papers later: `--update` does an incremental merge (much faster than `--refresh`).

### Phase 5: Score methods against the project

```bash
/evaluate-fit --all projects/my_study/context.md --project=my_study
```

Each KB method gets a fitness assessment (Excellent / Good / Moderate / Poor / Not Recommended) with strengths, concerns, and configuration recommendations specific to your data. Produces `fitness_summary.md` with a primary pipeline recommendation.

### Phase 6: Integrate biology + bioinformatics into a plan

```bash
/design-analysis projects/my_study/literature/0_synthesis_literature.md \
                 projects/my_study/context.md \
                 --project=my_study
```

Produces `analysis_plan.md` — an ordered, code-ready analytical workflow that maps each biology hypothesis to a specific method + function + parameters, accounting for your project's constraints (broken markers, small sample size, enrichment biases).

### Phase 7: Apply a method to real data

```bash
/adapt-method totalVI
```

Generates project-specific data discovery → method-specific EDA → preliminary run on a subset, with real results. Produces ready-to-modify scripts for the full run.

## When to use each skill standalone

You don't have to run the full pipeline. Common standalone uses:

- `/read-paper`: just want a one-page summary of a method paper
- `/extract-figures`: documenting figures for a paper club presentation
- `/index-docs`: keeping a navigation layer for a Python package's docs
- `/evaluate-fit <method> <context>`: spot-check whether one new method fits an existing project

## Skill DAG (which skill needs what)

| Skill | Reads | Writes |
|-------|-------|--------|
| `/read-paper` | paper PDF | `concept.md` |
| `/understand-theory` | paper PDF + `concept.md` | `theory.md` |
| `/learn-code` | `concept.md` (for `github:` URL) | `code.md` |
| `/extract-figures` | paper PDF + `concept.md` | `figures.md` |
| `/split-supplement` | supplement PDF | enhances `concept.md`, `theory.md`, `figures.md` |
| `/harmonize` | all `<method>/*.md` | edits all `<method>/*.md` |
| `/review-knowledge` | `<method>/*.md` | review report |
| `/build-knowledge` | paper PDF | orchestrates all of the above |
| `/index-docs` | docs URL | `ecosystems/<pkg>/*.yaml` + `navigation.md` |
| `/mine-paper` | biology paper + `context.md` | `<paper>_intel.md` |
| `/synthesize-literature` | `<paper>_intel.md` files + `context.md` | `0_synthesis_literature.md` |
| `/evaluate-fit` | `concept.md` files + `context.md` | `<method>_fitness_assessment.md` + `fitness_summary.md` |
| `/design-analysis` | synthesis + fitness summary + concept.md files + ecosystem indexes | `analysis_plan.md` |
| `/adapt-method` | KB entry + actual data | `<method>_adaptation/` |
| `/run-pipeline` | `context.md` + KB + papers/ | orchestrates `/mine-paper` → `/synthesize-literature` → `/evaluate-fit` → `/design-analysis` |

## Phase 8: Auto end-to-end

`/run-pipeline` chains Phases 3–6 (mine → synthesize → evaluate → design) into one invocation. It is a thin orchestrator that spawns each phase as a background agent and verifies outputs on disk; it never reads phase content into its own context window.

```bash
# Gated: each phase keeps its native interactive review prompts (status quo, just chained)
/run-pipeline projects/my_study/context.md --project=my_study

# Auto: skip review prompts, ensemble the integrative outputs
/run-pipeline projects/my_study/context.md --project=my_study --auto

# Also build new KB entries before running the pipeline
/run-pipeline projects/my_study/context.md --project=my_study \
              --auto --build-kb=totalVI.pdf,dsb.pdf

# Resume / re-run only certain phases
/run-pipeline projects/my_study/context.md --project=my_study \
              --auto --phases=evaluate,design
```

### Ensemble + adjudicator (auto mode)

In `--auto`, the interactive PASS / NEEDS_REVISION / FAIL gates are replaced with an **ensemble + adjudicator** pattern on each integrative output:

1. The phase runs **twice as fully independent background agents** with identical prompts and isolated context windows. They cannot see each other's work.
2. Their outputs are written to `<artifact>_v1.md` and `<artifact>_v2.md`.
3. A **third independent adjudicator agent** reads both versions plus the source-of-truth inputs (intel files, per-method assessments, context.md, etc.) and produces:
   - The canonical artifact (`<artifact>.md`) with each claim classified as AGREE / DISAGREE-resolved / UNIQUE-kept-or-dropped.
   - An audit log (`<artifact>_adjudication.md`) with reasoning, a `confidence_score`, and a `human_review_needed` flag.

Three integrative outputs are eligible. By default all three are ensembled in `--auto` mode:

| Output | Phase | Why ensemble it |
|--------|-------|-----------------|
| `0_synthesis_literature.md` | synthesize | Integrative cross-paper synthesis with consensus / conflict judgments |
| `fitness_summary.md` | evaluate (aggregation) | Picks the primary recommended method and pipeline ordering |
| `analysis_plan.md` | design | Maps every biology hypothesis to a specific method + parameters |

**What is NOT ensembled**: per-paper mining (`*_intel.md`) and per-method assessments (`*_fitness_assessment.md`). These are extraction-style work over many independent items; parallel agents already provide natural diversity, and dual-running each item would multiply token cost without proportional benefit. Token cost in auto mode is roughly `2.5×` on each ensembled integrative output, with everything else unchanged.

To pick which outputs get the ensemble treatment:

```bash
# Only ensemble the analysis plan
/run-pipeline projects/my_study/context.md --project=my_study \
              --auto --ensemble=design

# Ensemble synthesis and design but not the fitness summary
/run-pipeline projects/my_study/context.md --project=my_study \
              --auto --ensemble=synthesize,design
```

After the pipeline finishes, check each `*_adjudication.md` audit log. If `human_review_needed: true` on any of them, the pipeline summary will surface a one-line warning naming which artifacts need a closer read.

---

## Worked example

See [examples/cite-seq-aging.md](examples/cite-seq-aging.md) for a complete worked example on a CITE-seq study showing the full skill composition.
