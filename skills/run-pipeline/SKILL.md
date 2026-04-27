---
name: run-pipeline
description: Orchestrate the full per-project pipeline (mine → synthesize → evaluate → design) end-to-end, with an unattended mode that replaces interactive quality gates with a dual-run + independent adjudicator pattern
argument-hint: "[context.md] --project=folder [--unattended] [--ensemble=synthesize,evaluate-summary,design] [--phases=mine,synthesize,evaluate,design] [--build-kb=a.pdf,b.pdf] [--methods=m1,m2] [--papers-dir=papers/] [--check-consistency | --no-consistency-check] [--web-search-repos] [--no-preflight] [--skip-figures]"
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Bash(mkdir *, mv *, cp *, ls *, wc *), Task, TaskOutput, WebSearch, WebFetch
---

# Run Pipeline Orchestrator

This skill chains the per-project skills end-to-end so a single invocation takes you from "papers in `papers/`" to a finished `analysis_plan.md`. It is a **thin orchestrator**: it never reads the contents of phase outputs into its own context — it only spawns background agents, waits, and verifies that files exist and pass sanity checks.

Two modes:

- **Default (gated)** — chains the existing skills with their built-in interactive quality gates (PASS / NEEDS_REVISION / FAIL). You answer prompts between phases, just as you would running them by hand.
- **Unattended (`--unattended`)** — disables interactive gates. Each *integrative* output runs **twice as independent background agents**; a **third independent adjudicator agent** compares the two, spot-checks the highest-stakes "agreed" claims against source files (catching false consensus), and produces the canonical artifact plus an audit log with a deterministic confidence rubric. After all phases finish, a **fourth, cross-phase consistency auditor** verifies the three integrative outputs cohere with each other. No human in the loop until the pipeline finishes.

Three integrative outputs are eligible for ensemble:
- `synthesize` — `0_synthesis_literature.md`
- `evaluate-summary` — `fitness_summary.md` (the cross-method aggregation, NOT the per-method assessments)
- `design` — `analysis_plan.md`

The token cost story:

- The orchestrator stays small (no phase content ever enters its window).
- Default mode adds ~zero tokens beyond what the user would spend invoking each skill manually.
- Unattended mode roughly **2.5×** the cost of each ensembled output (two independent runs + one adjudicator). Per-paper (`/mine-paper`) and per-method (`/evaluate-fit` per-method assessments) extraction work stays single-run — those phases are already parallelized internally over many independent items, and dual-running each item inflates cost without proportional gain. Only the integrative *aggregation* steps benefit from independent re-runs.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                  RUN-PIPELINE (lightweight)                       │
│  - Parse args                                                     │
│  - Track progress in projects/<name>/.pipeline_progress.md        │
│  - Spawn phase agents (background)                                │
│  - Verify outputs (existence, size, frontmatter, sections)        │
│  - In unattended+ensemble: spawn v1, v2, then adjudicator         │
│  - NEVER reads phase outputs into its own context                 │
└──────────────────────────────────────────────────────────────────┘
           │
           ├─ (optional) Phase 0: build-knowledge for each --build-kb PDF
           │   ├─ 0.1 pre-flight repo manifest (1 agent: methods.yaml +
           │   │       PDF extraction + optional web search w/ verification)
           │   ├─ 0.2 surface manifest (gated: AskUserQuestion; unattended: log)
           │   ├─ 0.3 spawn /build-knowledge per PDF with resolved --repo=
           │   └─ 0.4 verify outputs
           │
           ▼
   Phase 1: /mine-paper --all       ──► literature/<paper>_intel.md
           │
           ▼
   Phase 2: /synthesize-literature  ──► literature/0_synthesis_literature.md
           │   (ensemble target)            ├── _v1.md
           │                                ├── _v2.md
           │                                └── _adjudication.md
           ▼
   Phase 3: /evaluate-fit --all     ──► bioinformatics/<method>_fitness_assessment.md  (per-method, single-run)
           │   (summary is ensemble        + bioinformatics/fitness_summary.md          (ensemble target)
           │    target, not per-method)        ├── _v1.md
           │                                   ├── _v2.md
           │                                   └── _adjudication.md
           ▼
   Phase 4: /design-analysis        ──► analysis_plan.md
           │   (ensemble target)         ├── analysis_plan_v1.md
           │                             ├── analysis_plan_v2.md
           │                             └── analysis_plan_adjudication.md
           ▼
   Phase 5: cross-phase consistency ──► .consistency_report.md
               (one auditor agent)        (PASS / WARNING / FAIL)
```

`/adapt-method` is **not** included — it requires real data and is run on a chosen method after the plan is reviewed.

---

## Step 0: Parse Arguments and Validate

### 0.1 Required arguments

- `context.md` — path to the project context file (positional)
- `--project=<name>` — project folder under `projects/`

### 0.2 Optional flags

| Flag | Default | Effect |
|------|---------|--------|
| `--unattended` | off | Skip all interactive review gates; use ensemble + adjudicator on the outputs listed in `--ensemble`. |
| `--ensemble=<list>` | `synthesize,evaluate-summary,design` | Integrative outputs that run twice + adjudicator in unattended mode. Valid: `synthesize`, `evaluate-summary`, `design`. |
| `--phases=<list>` | `mine,synthesize,evaluate,design` | Which phases to actually run. Use to resume or skip. |
| `--build-kb=<pdfs>` | (none) | If set, run `/build-knowledge` on each PDF before Phase 1. Comma-separated. |
| `--methods=<list>` | (all KB methods) | Restrict `/evaluate-fit` to these methods. |
| `--papers-dir=<path>` | `papers/` | Passed through to `/mine-paper --all`. |
| `--check-consistency` | on in `--unattended`, off in gated | Run the cross-phase consistency auditor (Phase 5) after the integrative outputs are produced. |
| `--no-consistency-check` | — | Skip Phase 5 even in unattended mode. |
| `--web-search-repos` | off | Allow `/learn-code` (inside Phase 0) to use web search as a fallback when `--repo=`, `methods.yaml`, and `concept.md` extraction all fail. Requires verification (2 of 3 README checks); falls back to MISSING on failed verification. |
| `--no-preflight` | — | Skip the pre-flight repo manifest (Phase 0.5). Phase 0 still runs but each `/build-knowledge` resolves its own repo independently. |
| `--skip-figures` | off | Pass `--skip-figures` through to every `/build-knowledge` agent spawned in Phase 0. Skips `/extract-figures` per method; no `figures.md` is written; downstream Phase 0 verification does not require it. Has no effect if `--build-kb` is not set. |

### 0.3 Validate

```bash
ls {context_path}
ls -d projects/{project}
ls knowledge_base/   # warn if empty and --build-kb not set
```

If `--unattended` is set without any `--ensemble` value, default to `synthesize,evaluate-summary,design`.

If `--build-kb` is **not** set and `knowledge_base/` is empty, abort with: *"No knowledge base entries found. Run `/build-knowledge <paper.pdf>` first, or pass `--build-kb=...` to this command."*

---

## Step 1: Initialize Progress Tracker

Create `projects/{project}/.pipeline_progress.md`:

```markdown
---
project: {project}
started: {timestamp}
mode: {gated|unattended}
ensemble: {comma-list or none}
phases_requested: {comma-list}
---

# Pipeline Progress

| Phase | Skill | Mode | Status | Agent IDs | Last Updated |
|-------|-------|------|--------|-----------|--------------|
| 0 | /build-knowledge × N | gated | pending | - | - |
| 1 | /mine-paper --all | single | pending | - | - |
| 2 | /synthesize-literature | {single|ensemble} | pending | - | - |
| 3 | /evaluate-fit --all | single | pending | - | - |
| 4 | /design-analysis | {single|ensemble} | pending | - | - |

## Agent Log

| Timestamp | Phase | Role | Agent ID | Status | Output Path |
|-----------|-------|------|----------|--------|-------------|
```

If a progress file already exists, read it and ask the user:
- Resume from the first non-complete phase
- Re-run a specific phase
- Start fresh (overwrite)

In `--unattended` mode, default to **resume from first non-complete phase** without prompting.

---

## Output Verification Protocol

Apply after **every** background agent completes. Background agents have a critical failure mode: they may finish "successfully" but produce no file, an empty file, or a stub with no real content (sandbox denials, permission errors, agents that summarize without calling Write). The orchestrator must NEVER silently proceed.

Run all four checks per expected output file:

| Check | Pass criteria | Failure action |
|-------|---------------|----------------|
| **Existence** | `ls` returns the file | Log "missing output", record agent ID + output log path, halt phase |
| **Size** | ≥ 1 KB (≥ 30 lines for content docs) | Log "stub output", surface to user, halt phase |
| **Frontmatter** | YAML frontmatter parses; key field present (e.g. `method:`, `project:`) | Log "malformed", halt phase |
| **Sections** | At least 2 of the documented top-level `##` headers present | Log "incomplete", halt phase |

For per-paper / per-method batch skills (`/mine-paper --all`, `/evaluate-fit --all`), apply per output file. Failed items go in a per-agent failure list; succeeded items continue. Report a verification table at end of the phase.

In **gated mode**, on any failure: surface to user with options (retry / accept / skip / abort).
In **unattended mode**, on any failure: write the failure to `.pipeline_progress.md`, mark the phase as `failed`, do **not** retry blindly, and continue with downstream phases that don't depend on the failed output. Halt the pipeline if a downstream phase has a hard dependency.

---

## Adjudicator Pattern (shared)

Every ensemble phase uses the same independent-adjudicator pattern. This section is the canonical definition; phase sections specify only the **inputs** (which v1/v2 files, which source-of-truth files), the **outputs** (canonical file path, audit log path), and any **phase-specific quality criteria**.

### Why this pattern

The two prior agents (v1, v2) ran independently with identical prompts. Three failure modes the adjudicator must catch:

1. **Real disagreement** — v1 and v2 picked different answers on the same point.
2. **Asymmetric coverage** — one version included an item the other missed.
3. **False consensus** — v1 and v2 both hallucinated the same plausible-sounding thing. The naive adjudicator rubber-stamps this as AGREE. The fix is **explicit AGREE-verification against source files** for the highest-stakes claims.

### Adjudicator prompt template

When spawning an adjudicator, the orchestrator constructs the prompt by substituting `{V1_PATH}`, `{V2_PATH}`, `{SOURCE_FILES}`, `{PHASE_CRITERIA}`, `{CANONICAL_PATH}`, `{AUDIT_PATH}`, and `{CITATION_FORMAT}` into this template:

```
You are the INDEPENDENT ADJUDICATOR. Two prior agents produced these versions
independently:
  - {V1_PATH}
  - {V2_PATH}

Source-of-truth inputs (use to settle disagreements AND to verify high-stakes
agreements):
{SOURCE_FILES}

Phase-specific quality criteria:
{PHASE_CRITERIA}

Your job:

1. Read v1 and v2.

2. For each top-level section, classify each substantive claim/item as one of:
   - AGREE: both versions assert it (with the same provenance).
   - DISAGREE: versions conflict.
   - UNIQUE_TO_V1 / UNIQUE_TO_V2: only one version has it.

3. For DISAGREE items: read the relevant source-of-truth files. Pick the
   better-supported version, OR keep both with a flagged uncertainty note
   if neither is clearly grounded.

4. For UNIQUE items: include only if grounded in the source-of-truth files;
   otherwise drop.

5. AGREE verification (catches false consensus). Both v1 and v2 can hallucinate
   the same plausible thing. For every AGREE item, ask: "If this is wrong,
   does a downstream decision break?" — if yes, spot-check it against
   sources. Target ~5-10 spot-checks, weighted toward the most consequential
   AGREE claims for this phase (see PHASE_CRITERIA above for what counts as
   high-stakes).
   For each spot-check: grep / read the cited source file and verify the
   claim is actually supported. If a spot-checked AGREE claim is NOT
   supported, demote it in the audit log to DISAGREE_FLAGGED, and either
   remove it from the canonical output or rewrite it with the actual
   support.

6. Produce TWO files:

   a) {CANONICAL_PATH}
      The final, adjudicated artifact. Apply the per-claim classifications
      from steps 2-5. Use the better structural template of v1 vs v2 (or
      merge if both are partial). Every claim must cite supporting source
      files in this format: {CITATION_FORMAT}.

   b) {AUDIT_PATH}
      Audit log. For each section, list AGREE / DISAGREE-resolved /
      DISAGREE-flagged / UNIQUE-kept / UNIQUE-dropped decisions and the
      reasoning. Include a "Spot-checks performed" subsection listing
      which AGREE claims were verified and what was found.

      End the audit log with the structured rubric block, computed
      DETERMINISTICALLY from your counts (do NOT self-rate):

      ```yaml
      counts:
        N_AGREE: <int>              # AGREE items kept after spot-checks
        N_DISAGREE_RESOLVED: <int>  # conflicts adjudicator settled from sources
        N_DISAGREE_FLAGGED: <int>   # conflicts left flagged + AGREE items demoted by spot-check
        N_UNIQUE_KEPT: <int>        # UNIQUE items grounded in sources, kept
        N_UNIQUE_DROPPED: <int>     # UNIQUE items not grounded, dropped
      ratio: <N_AGREE / (N_AGREE + N_DISAGREE_RESOLVED + N_UNIQUE_KEPT)>
      confidence: High | Medium | Low
      human_review_needed: true | false
      flagged_items:
        - <short description per flagged item>
      ```

      Apply this rubric exactly:
        confidence = High    if N_DISAGREE_FLAGGED == 0 AND ratio >= 0.7
                   = Medium  if N_DISAGREE_FLAGGED == 0 AND 0.4 <= ratio < 0.7
                   = Low     if N_DISAGREE_FLAGGED  > 0 OR  ratio < 0.4

        human_review_needed = (confidence == "Low") OR (N_DISAGREE_FLAGGED > 0)

7. Do NOT silently merge by concatenation. Do NOT pick one version wholesale.

Return a one-paragraph summary of (a) how much v1/v2 agreed, and (b) any
AGREE claims that turned out NOT to be supported in spot-checks.
```

### Verification of adjudicator output

After the adjudicator finishes:

1. Run the Output Verification Protocol on `{CANONICAL_PATH}` and `{AUDIT_PATH}`.
2. Parse the YAML rubric block from the audit log. Record `confidence`, `human_review_needed`, and `len(flagged_items)` in `.pipeline_progress.md`.
3. These three fields drive the Final Summary warnings.

### What this pattern does and does not do

- ✅ Catches real disagreements between independent runs.
- ✅ Catches false-consensus hallucinations on the highest-stakes claims, via spot-checks against sources.
- ✅ Produces a deterministic, auditable confidence signal (anyone can recount the AGREE / DISAGREE / UNIQUE entries and verify the rubric).
- ❌ Does NOT iterate — runs once, surfaces flags, moves on. (A future iterative refinement pass on `confidence: Low` outputs would be additive.)
- ❌ Does NOT catch errors that BOTH versions agreed on AND the adjudicator did NOT spot-check. The spot-check budget is finite; pick the high-stakes claims wisely.

---

## Phase 0: (Optional) Build Knowledge Base

Only runs if `--build-kb=<pdfs>` is set.

### 0.1 Pre-flight Repo Manifest

`/build-knowledge` Phase 3 needs a GitHub URL per method. Resolution can fail silently (paper doesn't list one, extraction picks an old fork, etc.) — in unattended mode, those failures get noticed only after each `/build-knowledge` agent has already burned tokens on phases 1 and 2. The pre-flight pass resolves all repos up front, in one cheap agent, so gaps are surfaced before the heavy work.

Skip this step with `--no-preflight`.

**Spawn one pre-flight agent**:

```
Task(
    subagent_type: "general-purpose",
    description: "Pre-flight repo manifest for {project}",
    prompt: |
        You are building a manifest of repository URLs for these method PDFs:
          {comma-separated list of --build-kb PDFs}

        For each PDF, resolve a GitHub URL using this chain (stop at the first
        success; record which step succeeded):

        1. methods.yaml at the project root.
           - Read methods.yaml (or methods.yml) if present.
           - The lookup key is the PDF filename stem (e.g. "totalVI.pdf" → "totalVI").
           - If found, source: "yaml", confidence: "high".

        2. PDF metadata extraction.
           - Open the PDF and grep the first ~10 pages for "github.com/<owner>/<repo>"
             URLs. Filter out personal homepages, university pages, etc.
           - If exactly one matches, source: "paper", confidence: "high".
           - If multiple match, prefer the one in a "Code availability" /
             "Software" / "Data and code availability" section. If still
             ambiguous, list all and mark source: "paper", confidence: "low",
             notes: "multiple github URLs in paper — please verify".

        3. Web search (only if --web-search-repos is set in this invocation:
           {true|false}).
           - WebSearch: "<filename-stem> github" and "<filename-stem> bioinformatics github".
           - For top 2-3 candidate github.com/<owner>/<repo> URLs, WebFetch the README.
           - Apply verification gate (2 of 3 must pass):
             a) README contains the method name (case-insensitive whole-token match)
             b) README links to the paper (DOI / arXiv / paper title) OR repo
                description references it
             c) Repo has analysis code (.py / .R / .ipynb / pyproject.toml /
                DESCRIPTION / setup.py)
           - If a candidate passes 2/3, source: "search", confidence: "medium",
             notes: list which checks passed.
           - If no candidate passes, source: "none", notes: list all candidates
             considered and which checks failed.

        4. If everything fails: source: "none", confidence: "n/a".

        Write the manifest to: projects/{project}/.repo_manifest.md

        Format:
        ```markdown
        ---
        project: {project}
        generated: {date}
        web_search_enabled: {true|false}
        ---

        # Pre-flight Repo Manifest

        | PDF | Method | URL | Source | Confidence | Notes |
        |-----|--------|-----|--------|------------|-------|
        | totalVI.pdf | totalVI | https://... | paper | high | extracted from "Code availability" |
        | dsb.pdf | dsb | https://... | yaml | high | methods.yaml override |
        | foo.pdf | foo | (MISSING) | none | n/a | paper has no URL; web search disabled |
        ```

        Then return a one-paragraph summary listing:
        - N resolved with high confidence
        - N resolved with medium confidence (search-based, audit recommended)
        - N missing (will produce no_repo stub if /build-knowledge runs)
    run_in_background: true
)
```

### 0.2 Surface the manifest

After the pre-flight agent finishes:

- Verify `projects/{project}/.repo_manifest.md` exists and parses.
- **In gated mode**: read the manifest, show the user the table with one `AskUserQuestion` covering all MISSING and `confidence: low | medium` entries. The user can supply URLs, accept the defaults, or skip individual methods. Update the manifest before proceeding.
- **In unattended mode**: do NOT prompt. Accept the manifest as-is. If any entries are MISSING or medium-confidence, log them in `.pipeline_progress.md` and surface in the Final Summary so the user can audit after the pipeline finishes.

The orchestrator does **not** read the manifest contents into its own context window — only the agent's one-paragraph summary. The manifest stays on disk; downstream `/build-knowledge` agents read it themselves.

### 0.3 Spawn /build-knowledge per PDF

For each PDF, spawn `/build-knowledge` as a background agent. Pass through:
- `--repo=<url>` if the manifest resolved a URL with `confidence: high` or `medium` (this short-circuits `/learn-code`'s resolution chain)
- `--web-search-repos` if the orchestrator was invoked with that flag (gives `/learn-code` permission to search again as a last resort, e.g. if the manifest was outdated or the user asks for a re-resolve)
- `--skip-figures` if the orchestrator was invoked with that flag (skips Phase 4 `/extract-figures` inside each per-method build)

**In unattended mode**, also include this prompt override:

> "Run in non-interactive mode: on NEEDS_REVISION, auto-refine once with the review's recommendations and then accept; on FAIL, halt that knowledge-base entry but do not block other entries. If `/learn-code` reports MISSING, accept the no_repo stub and continue."

`/build-knowledge` is itself an orchestrator with internal review. It is **not** ensemble-targeted — wrapping it in dual-run would multiply cost across 6 sub-phases per PDF. Trust its internal review with the unattended override above.

### 0.4 Verify

After all `/build-knowledge` agents finish, verify each `knowledge_base/<method>/` has `concept.md`, `theory.md`, `code.md`, and (unless `--skip-figures` was set) `figures.md`. For methods where `code.md` has `repo_source: none` or `search`, surface them in the Phase 0 status block of the Final Summary.

---

## Phase 1: Mine Papers

Spawn one background agent:

```
Task(
    subagent_type: "general-purpose",
    description: "Mine all papers for {project}",
    prompt: "/mine-paper --all {context_path} --project={project} --dir={papers_dir}",
    run_in_background: true
)
```

Wait via `TaskOutput(block: true, timeout: 1_800_000)`.

Verify: list `projects/{project}/literature/*_intel.md`, run the verification protocol per file. Record list of accepted intel files.

**No ensemble** — each paper is mined independently and `/mine-paper --all` already parallelizes internally.

---

## Phase 2: Synthesize Literature

### Single-run path (gated mode, OR unattended without `synthesize` in --ensemble)

Spawn `/synthesize-literature {context} --project={project}` and verify `projects/{project}/literature/0_synthesis_literature.md`.

In gated mode: the skill's own review prompts surface naturally.

### Ensemble path (unattended + `synthesize` in --ensemble)

Sequential dual-run, then independent adjudicator:

**Run v1:**

```
Task(
    subagent_type: "general-purpose",
    description: "Synthesis v1 for {project}",
    prompt: |
        /synthesize-literature {context_path} --project={project} --refresh

        IMPORTANT (ensemble run 1 of 2):
        - You are running INDEPENDENTLY. Do NOT look at any *_v1.md or *_v2.md files.
        - Produce the canonical output as the skill normally does.
        - Skip any interactive review prompts; treat the skill as fully automatic.
    run_in_background: true
)
```

Wait, verify the output at `projects/{project}/literature/0_synthesis_literature.md`, then **rename**:

```bash
mv projects/{project}/literature/0_synthesis_literature.md \
   projects/{project}/literature/0_synthesis_literature_v1.md
```

**Run v2:** Same prompt, fresh agent, independent context. Same verification, then `mv` to `_v2.md`.

**Adjudicator:** spawn the [Adjudicator Pattern](#adjudicator-pattern-shared) with these substitutions:

| Placeholder | Value |
|-------------|-------|
| `V1_PATH` | `projects/{project}/literature/0_synthesis_literature_v1.md` |
| `V2_PATH` | `projects/{project}/literature/0_synthesis_literature_v2.md` |
| `SOURCE_FILES` | `projects/{project}/context.md` and all `projects/{project}/literature/*_intel.md` |
| `PHASE_CRITERIA` | (a) Mouse-derived data must stay labeled separately from human consensus — never silently promote mouse findings to "consensus". (b) Every consensus claim requires a `[Author Year]` citation list. (c) **High-stakes AGREE claims for spot-check**: consensus markers cited as backed by 3+ papers, top-ranked hypotheses in the master ranking, gene signatures with claimed cross-paper provenance. |
| `CANONICAL_PATH` | `projects/{project}/literature/0_synthesis_literature.md` |
| `AUDIT_PATH` | `projects/{project}/literature/0_synthesis_literature_adjudication.md` |
| `CITATION_FORMAT` | `[Author Year]` referencing the intel files |

After adjudicator completes, run the Output Verification Protocol on both files and parse the rubric block per the shared pattern. If `human_review_needed: true`, queue a warning for the Final Summary (do not block downstream phases).

---

## Phase 3: Evaluate Fit

Spawn one background agent. If `evaluate-summary` is in the active `--ensemble` list, append the `--ensemble-summary` flag — `/evaluate-fit` runs the per-method assessments single-run as usual, then dual-runs the **summary aggregation step** with an independent adjudicator.

```
Task(
    subagent_type: "general-purpose",
    description: "Evaluate fit for all KB methods",
    prompt: "/evaluate-fit --all {context_path} --project={project}{methods_arg}{ensemble_summary_flag}",
    run_in_background: true
)
```

Where `{ensemble_summary_flag}` is `" --ensemble-summary"` if `evaluate-summary` is in the active ensemble list, else empty.

Verify per-method `*_fitness_assessment.md` files and `fitness_summary.md`. In ensemble-summary mode, also expect `fitness_summary_v1.md`, `fitness_summary_v2.md`, and `fitness_summary_adjudication.md`.

**Per-method assessments are NOT ensembled** — extraction-style work over many independent items already gets diversity from parallelism. The aggregation step (the integrative judgment about which method wins and what pipeline to recommend) is the ensemble target.

---

## Phase 4: Design Analysis

### Single-run path

Spawn `/design-analysis {synthesis_path} {context_path} --project={project}` and verify `projects/{project}/analysis_plan.md`.

### Ensemble path (unattended + `design` in --ensemble)

Sequential v1 → v2 (each renamed to `analysis_plan_v1.md` / `analysis_plan_v2.md`), then spawn the [Adjudicator Pattern](#adjudicator-pattern-shared) with these substitutions:

| Placeholder | Value |
|-------------|-------|
| `V1_PATH` | `projects/{project}/analysis_plan_v1.md` |
| `V2_PATH` | `projects/{project}/analysis_plan_v2.md` |
| `SOURCE_FILES` | `projects/{project}/literature/0_synthesis_literature.md`, `projects/{project}/bioinformatics/fitness_summary.md`, `projects/{project}/context.md`, and all `knowledge_base/<method>/concept.md` files referenced in either v1 or v2 |
| `PHASE_CRITERIA` | (a) Favor configurations that respect the project's stated constraints (broken markers, small n, enrichment biases). (b) Every method choice must trace to a hypothesis from synthesis AND a fit score from `fitness_summary.md`. (c) **High-stakes AGREE claims for spot-check**: the primary recommended pipeline order, hypothesis-to-method mappings, parameter values that depend on biology (e.g., gene signatures used in scoring), and any "do not use method X because" exclusions. |
| `CANONICAL_PATH` | `projects/{project}/analysis_plan.md` |
| `AUDIT_PATH` | `projects/{project}/analysis_plan_adjudication.md` |
| `CITATION_FORMAT` | references to specific sections of the synthesis, fitness summary, and concept files (e.g., `0_synthesis_literature.md § Consensus markers`, `<method>_fitness_assessment.md § Configuration recommendations`) |

After adjudicator completes, run the Output Verification Protocol and parse the rubric. If `human_review_needed: true`, queue a warning for the Final Summary.

---

## Phase 5: Cross-Phase Consistency Audit

The per-phase adjudicators only see their own phase. They cannot catch a class of failure that emerges only across phases — for example: the synthesis adjudicator endorses hypothesis X, but the design adjudicator builds a plan around a method that cannot test X; or `fitness_summary.md` ranks Method A as Primary while `analysis_plan.md` quietly uses Method B with no justification.

Phase 5 spawns one final auditor that reads all three integrative outputs and verifies they cohere.

### When it runs

| Mode | Default | How to override |
|------|---------|-----------------|
| `--unattended` | ON | `--no-consistency-check` |
| Gated | OFF | `--check-consistency` |

It runs only if all three integrative outputs exist on disk (`0_synthesis_literature.md`, `fitness_summary.md`, `analysis_plan.md`). If any are missing — e.g. `--phases` excluded one — Phase 5 logs "skipped: incomplete inputs" and exits cleanly.

### Spawn

```
Task(
    subagent_type: "general-purpose",
    description: "Cross-phase consistency audit for {project}",
    prompt: |
        You are the INDEPENDENT CROSS-PHASE CONSISTENCY AUDITOR. Three
        prior agents (one per phase) produced these files separately;
        each is internally consistent but they CAN disagree with each
        other. Read them in order:

          1. projects/{project}/context.md
          2. projects/{project}/literature/0_synthesis_literature.md
          3. projects/{project}/bioinformatics/fitness_summary.md
          4. projects/{project}/analysis_plan.md

        Run these five checks. For each, report PASS / FAIL / WARNING
        with specific cited evidence (file path + section name). Do NOT
        speculate — if a check requires information not present in the
        files, mark it WARNING and explain.

        Check A — Hypotheses → analysis_plan
          Every top-ranked hypothesis in 0_synthesis_literature.md
          (specifically: those listed in the master hypothesis ranking
          or marked as consensus) must be addressed by at least one
          step in analysis_plan.md, using a method that can actually
          test it.
          FAIL if a top-ranked hypothesis has no corresponding step.

        Check B — Primary method consistency
          The PRIMARY recommended method in fitness_summary.md must
          either (i) be the method used for the corresponding step in
          analysis_plan.md, or (ii) have an explicit justification in
          analysis_plan.md for the deviation.
          FAIL if a different method is silently substituted.

        Check C — No Poor / Not Recommended methods used
          No step in analysis_plan.md may use a method rated "Poor" or
          "Not Recommended" in fitness_summary.md without explicit
          justification in analysis_plan.md.
          FAIL on silent use of a rejected method.

        Check D — Markers and gene signatures used
          Markers / gene signatures promoted in 0_synthesis_literature.md
          (consensus markers, named signatures) should appear by name
          in analysis_plan.md code templates wherever biologically
          relevant (scoring, annotation, gating).
          WARNING if a consensus marker is absent from any obviously
          relevant step.

        Check E — Context constraints respected
          Constraints from context.md (broken antibodies / markers,
          small sample size, enrichment strategy, panel limitations)
          must be respected in BOTH fitness_summary.md (no Excellent
          rating in the face of a hard constraint) AND analysis_plan.md
          (no method config that violates a constraint).
          FAIL on a violation; WARNING on a constraint mentioned but
          not explicitly addressed.

        Write your report to:
          projects/{project}/.consistency_report.md

        Use this format:

        ```markdown
        ---
        project: {project}
        generated: {date}
        ---

        # Cross-Phase Consistency Report

        | Check | Status | Notes |
        |-------|--------|-------|
        | A: Hypotheses → analysis_plan | PASS/FAIL/WARNING | <one-liner> |
        | B: Primary method consistency | ... | ... |
        | C: No Poor/Not-Recommended methods used | ... | ... |
        | D: Markers / signatures used | ... | ... |
        | E: Context constraints respected | ... | ... |

        ## Findings

        ### Check A
        <evidence with file paths and section names>

        ### Check B
        ...

        (etc.)

        ## Summary

        ```yaml
        any_failures: true|false
        any_warnings: true|false
        actionable_recommendations:
          - <specific edit suggested>
        ```
        ```

        End your response with exactly one of:
          CONSISTENCY: PASS
          CONSISTENCY: WARNING
          CONSISTENCY: FAIL
    run_in_background: true
)
```

### After it returns

Run Output Verification on `.consistency_report.md`. Parse the trailing `CONSISTENCY:` line. Record the result in `.pipeline_progress.md`. If `WARNING` or `FAIL`, queue findings for the Final Summary.

### Cost

One extra agent. The auditor reads four files (context, synthesis, fitness summary, analysis plan) — none of which is huge. Typical cost: ~0.2× of an ensembled phase. Catches a real class of failure that the per-phase adjudicators structurally cannot see.

---

## Final Summary

After all phases complete, write `projects/{project}/.pipeline_summary.md` (and surface a short version to the user):

```markdown
# Pipeline Run Summary

- Mode: {gated|unattended}
- Ensemble phases: {list or none}
- Consistency check: {ran|skipped}
- Started: {ts}
- Finished: {ts}

## Phase Results

| Phase | Status | Output | Confidence | Flagged Items |
|-------|--------|--------|------------|---------------|
| 0: build-kb | ✓ / ✗ / skipped | N method KBs | per-method `repo_source` (flag/yaml/paper/search/none) | methods with `none` or `search` |
| 1: mine | ✓ / ✗ | N intel files | n/a | n/a |
| 2: synthesize | ✓ / ✗ | 0_synthesis_literature.md | High/Med/Low | <count> |
| 3: evaluate | ✓ / ✗ | fitness_summary.md | High/Med/Low | <count> |
| 4: design | ✓ / ✗ | analysis_plan.md | High/Med/Low | <count> |
| 5: consistency | ✓ / ✗ | .consistency_report.md | PASS/WARN/FAIL | n/a |

## Repo Resolution

(populate from `projects/{project}/.repo_manifest.md` if Phase 0 ran)

- **High-confidence resolutions**: N (sources: flag / yaml / paper)
- **Medium-confidence resolutions**: N (source: search — recommend audit)
- **Missing repos**: N (no_repo stub written; no `code.md` documentation)
- See `.repo_manifest.md` for the per-PDF table.

## Adjudication Flags

(populate from each adjudicator's audit log if `human_review_needed: true`)

- **{phase}** [{confidence}]: {N} flagged items — see `{adjudication_file}`
  - {first 2-3 flagged_items, truncated}

## Cross-Phase Consistency

(populate from `.consistency_report.md` if it ran)

- Status: PASS | WARNING | FAIL
- Failures (if any): list each Check that returned FAIL with the one-line note
- Warnings (if any): list each Check that returned WARNING with the one-line note
- See `.consistency_report.md` for full evidence and recommendations.
```

End the user-facing summary with one of:

**Clean run** (all confidence ≥ Medium AND consistency = PASS):

```
✅ Pipeline complete. No items flagged for human review.

Next step: review analysis_plan.md, then run `/adapt-method <method>` to apply
the recommended primary method to your real data.
```

**Items to review** (any `human_review_needed: true` OR consistency = WARNING):

```
⚠️  Pipeline complete with items needing human review:
    - {N} adjudicator flags across {phases}
    - {M} consistency warnings (Checks: {A,B,...})

Review these before running /adapt-method:
    - {adjudication_file_paths}
    - projects/{project}/.consistency_report.md
```

**Critical issues** (consistency = FAIL OR any phase `confidence: Low`):

```
🛑 Pipeline complete but with critical issues:
    - {phases with confidence: Low}
    - {consistency Checks that returned FAIL}

Do NOT run /adapt-method until these are resolved. Either:
    - Manually edit the canonical files to address the flagged items, OR
    - Re-run the affected phases (e.g., /run-pipeline --phases=design --unattended)
```

---

## Resumability

State lives entirely on disk:
- `.pipeline_progress.md` — phase status table
- Skill output files — per-phase canonical artifacts
- `_v1.md` / `_v2.md` / `_adjudication.md` — ensemble artifacts

If interrupted, re-running `/run-pipeline` with the same `--project` reads `.pipeline_progress.md` and resumes from the first non-complete phase. In unattended mode, resumption is silent. In gated mode, the user is asked to confirm.

---

## Token-Cost Notes

- The orchestrator never reads phase outputs into its own context — only `ls`, `wc`, frontmatter parse, and section header check. Its window stays under ~30k tokens for a full project.
- Each background agent gets a fresh ~200k window; their context never leaks back to the orchestrator.
- Unattended ensemble adds 2 extra full runs + 1 adjudicator per ensembled phase. The adjudicator reads only v1, v2, and source-of-truth files — not the entire KB.
- Default ensemble = `synthesize,evaluate-summary,design` (the three integrative outputs). Per-paper (`mine`) and per-method (assessments inside `evaluate`) extraction work is NOT ensembled — parallel agents over many small items already provide natural diversity.
- For a typical project (~20 papers, ~5 KB methods) in unattended mode, expect roughly: pre-flight repo manifest ≈ 0.1×, mine ≈ 1× × 20 papers, synthesize ≈ 2.5×, per-method assessments ≈ 1× × 5 methods, fitness_summary aggregation ≈ 2.5×, design ≈ 2.5×, cross-phase consistency ≈ 0.2×.
- Pre-flight repo resolution costs ~one cheap agent (PDF metadata grep + optional web searches/fetches). Even with `--web-search-repos` enabled across 5 missing methods, expect ≤ 0.2× of one ensembled phase. The savings vs. resolving inside each `/build-knowledge` are time-of-discovery (gaps surface up front, not after hours of agent work) more than tokens.
- AGREE-verification spot-checks inside each adjudicator add ~0.1–0.2× to the adjudicator step (the adjudicator reads ~5–10 source-file passages); cost is folded into the 2.5× ensemble multiplier above.

---

## When NOT to use this skill

- You want fine-grained control over each phase's review decisions → run skills individually.
- You only need one phase (e.g. just `/mine-paper` on new papers) → run that skill directly.
- You haven't built any KB entries yet AND you don't want to pass `--build-kb` → build at least one KB entry first so `/evaluate-fit` and `/design-analysis` have something to work with.

---

## Example Invocations

```bash
# Default: gated chain, identical to running each skill by hand
/run-pipeline projects/my_study/context.md --project=my_study

# Unattended end-to-end with default ensemble (synthesize + design)
/run-pipeline projects/my_study/context.md --project=my_study --unattended

# Build KB for two new method papers, then run unattended pipeline
/run-pipeline projects/my_study/context.md --project=my_study \
              --unattended --build-kb=totalVI.pdf,dsb.pdf

# Skip evaluate-fit (e.g. you already have fitness_summary.md from a prior run)
/run-pipeline projects/my_study/context.md --project=my_study \
              --unattended --phases=mine,synthesize,design

# Ensemble only the design phase (synthesis is fast/uncontroversial for this project)
/run-pipeline projects/my_study/context.md --project=my_study \
              --unattended --ensemble=design

# Unattended, ensemble synthesis + design but NOT the fitness summary
# (e.g. you trust the method-vs-method comparison but want extra rigor on the
# literature synthesis and the final analysis plan)
/run-pipeline projects/my_study/context.md --project=my_study \
              --unattended --ensemble=synthesize,design

# Gated mode but still run the cross-phase consistency audit at the end
/run-pipeline projects/my_study/context.md --project=my_study \
              --check-consistency

# Unattended but skip the consistency audit (e.g. you'll review by hand)
/run-pipeline projects/my_study/context.md --project=my_study \
              --unattended --no-consistency-check

# Build KB for several papers, allow web search to fill in missing repo URLs
# (paper-extracted URLs win where present; web search runs only as a last resort
#  with a 2/3-checks verification gate on each candidate's README)
/run-pipeline projects/my_study/context.md --project=my_study \
              --unattended --build-kb=totalVI.pdf,dsb.pdf,newmethod.pdf \
              --web-search-repos

# Skip the pre-flight manifest — let each /build-knowledge resolve its own repo
# (less batched-friendly; useful only when you're re-running a single method)
/run-pipeline projects/my_study/context.md --project=my_study \
              --unattended --build-kb=totalVI.pdf --no-preflight
```
