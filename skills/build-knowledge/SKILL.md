---
name: build-knowledge
description: Build a complete knowledge base entry for a method by orchestrating skills 1-6
argument-hint: [paper.pdf] [--method=name] [--supplement=file.pdf] [--repo=url] [--web-search-repos] [--skip-figures]
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Bash(mkdir *), Task, TaskOutput, WebSearch, WebFetch
---

# Build Knowledge Orchestrator (Background Agent Architecture)

This skill orchestrates the complete knowledge base building workflow using **background agents**. Each phase runs as a separate subprocess with its own context window (~200k tokens), preventing context exhaustion during long builds.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (lightweight)                       │
│  - Parses arguments                                                  │
│  - Tracks progress in .build_progress.md                            │
│  - Spawns phase agents                                              │
│  - Spawns review agents                                             │
│  - Makes PASS/NEEDS_REVISION/FAIL decisions                         │
│  - Asks user for input when needed                                  │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Phase Agent 1  │  │  Phase Agent 2  │  │  Phase Agent N  │
│  (/read-paper)  │  │(/understand...  │  │  (/harmonize)   │
│                 │  │                 │  │                 │
│  Own context    │  │  Own context    │  │  Own context    │
│  (~200k tokens) │  │  (~200k tokens) │  │  (~200k tokens) │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Review Agent 1 │  │  Review Agent 2 │  │  Review Agent N │
│  (concept.md)   │  │  (theory.md)    │  │  (all docs)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Key Benefits:**
- Each phase gets fresh context (no accumulation)
- Orchestrator stays lightweight (can run full 6-phase build)
- Failed phases can be retried without context loss
- Progress persists across sessions via `.build_progress.md`

---

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Input: Paper PDF + Optional (Supplement, Repo URL)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: spawn_agent(/read-paper) → concept.md             │
│  └── spawn_agent(/review-knowledge --phase=concept)         │
│      └── PASS/NEEDS_REVISION/FAIL decision loop             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                         [Phases 2-5]
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 6: spawn_agent(/harmonize)                           │
│  └── spawn_agent(/review-knowledge --phase=all)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Output: knowledge_base/{method}/ (complete)                │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 0: Parse Arguments and Setup

### 0.1: Parse Arguments

Extract from `$ARGUMENTS`:
- **Paper PDF path** (required): The main paper file
- **--method=name** (optional): Method name (inferred from paper if not provided)
- **--supplement=file.pdf** (optional): Supplementary materials
- **--repo=url** (optional): Code repository URL
- **--skip-figures** (optional): Skip Phase 4 (`/extract-figures`). Phase 4 is marked `skipped` in the progress tracker, no `figures.md` is written, and downstream phases (split-supplement, harmonize, final review) treat the file as absent. Use when figures aren't needed for downstream work and you want to save the extraction tokens.

### 0.2: Validate Inputs

```bash
# Check paper exists
ls -la {paper_path}

# Check supplement if provided
ls -la {supplement_path}
```

### 0.3: Check for Existing Build

```bash
ls knowledge_base/{method}/.build_progress.md 2>/dev/null
```

If progress file exists, read it and ask user:

**"Found existing build for {method} at phase {n}. What would you like to do?"**
- [ ] Resume from phase {n+1}
- [ ] Re-run phase {n}
- [ ] Start fresh (overwrite)

### 0.4: Initialize Progress Tracker

Create `knowledge_base/{method}/.build_progress.md`:

```markdown
---
method: {method}
started: {date}
paper: {paper_path}
supplement: {supplement_path}
repo: {repo_url}
architecture: background-agent
---

# Build Progress

| Phase | Skill | Status | Passes | Agent ID | Last Updated |
|-------|-------|--------|--------|----------|--------------|
| 1 | /read-paper | pending | 0 | - | - |
| 2 | /understand-theory | pending | 0 | - | - |
| 3 | /learn-code | pending | 0 | - | - |
| 4 | /extract-figures | pending | 0 | - | - |
| 5 | /split-supplement | pending | 0 | - | - |
| 6 | /harmonize | pending | 0 | - | - |

If `--skip-figures` was passed, write `skipped` (instead of `pending`) in the Phase 4 Status column at init time so resumption logic and the build summary treat that phase as intentionally absent.

## Agent Log

| Timestamp | Phase | Agent Type | Agent ID | Status |
|-----------|-------|------------|----------|--------|
```

---

## Agent Output Verification

Background agents have a critical failure mode: they may complete successfully but produce **no output file**, an **empty file**, or a **stub** with no real content. Causes include sandboxed write-tool denials, permission errors, or agents that summarize their work without actually calling Write. When this happens, the orchestrator must NOT silently proceed.

After every Task spawn, run all four checks:

| Check | Pass Criteria | Failure Action |
|-------|---------------|----------------|
| **Existence** | `ls` returns the file | Report "missing output", check agent log for Write errors |
| **Size** | File ≥ 1 KB (≥ 30 lines for content docs) | Report "stub output", read agent log to extract content if present |
| **Frontmatter** | YAML frontmatter parses, has `method:` (or skill-specific key) | Report "malformed", surface to user |
| **Sections** | At least 2 of the documented top-level `##` headers present | Report "incomplete", show user what's there |

**On any failure**: log it to the progress tracker, surface to the user with the agent ID and output log path, and stop. Do not retry blindly — retries with the same prompt usually fail the same way.

For batch/parallel skills, apply this per-agent: failed agents go in the failure list, successful ones continue. Report a per-agent verification table at the end.

---

## Phase Execution Pattern (Applies to All Phases)

Each phase follows this background-agent pattern:

### Step A: Spawn Phase Agent

Use the Task tool with `run_in_background=true`:

```
Task(
    subagent_type: "general-purpose",
    description: "Build {document}.md for {method}",
    prompt: "/{skill_name} {args}",
    run_in_background: true
)
```

This returns immediately with:
- `agent_id`: Use this to check status or resume
- `output_file`: Path to agent output log

### Step B: Wait for Phase Agent

Use TaskOutput to wait for completion:

```
TaskOutput(
    task_id: {agent_id},
    block: true,
    timeout: 600000  # 10 minutes max
)
```

### Step C: Verify Output Created

Background agents can silently fail to write files (e.g., when they're sandboxed or hit permission errors), then keep retrying and burning tokens. The orchestrator MUST verify each phase's output before proceeding.

```bash
ls -la knowledge_base/{method}/{document}.md
wc -l knowledge_base/{method}/{document}.md
```

Apply the **Output Verification Protocol** (see "Agent Output Verification" section below):
1. File exists
2. Size is non-trivial (>1 KB)
3. Required YAML frontmatter present
4. Has expected top-level section headers

If any check fails: do NOT spawn the next phase. Log the failure to `.build_progress.md`, surface to the user with the agent's output log path, and stop.

### Step D: Spawn Review Agent

```
Task(
    subagent_type: "general-purpose",
    description: "Review {document}.md",
    prompt: "/review-knowledge {method} --phase={phase}",
    run_in_background: true
)
```

### Step E: Wait for Review Agent

```
TaskOutput(
    task_id: {review_agent_id},
    block: true,
    timeout: 300000  # 5 minutes
)
```

### Step F: Parse Review Result

Read the review output and extract:
- Status: PASS / NEEDS_REVISION / FAIL
- Completeness score: n/10
- High-priority issues: list
- Recommended actions: list

### Step G: Decision Logic

```
if status == "PASS":
    → Update progress, proceed to next phase

elif status == "NEEDS_REVISION":
    if passes < 3:
        → Ask user: Refine / Accept / Manual edit
        if refine:
            passes += 1
            → Go back to Step A with refinement guidance
    else:
        → Force user decision: Accept / Manual edit / Abort

elif status == "FAIL":
    → Must fix before continuing
    → Ask user: Retry with guidance / Manual edit / Abort
```

### Step H: Update Progress Tracker

After each attempt, update `.build_progress.md`:

```markdown
| {phase} | /{skill} | {status} | {passes} | {agent_id} | {timestamp} |
```

And append to Agent Log:

```markdown
| {timestamp} | {phase} | phase | {agent_id} | {status} |
| {timestamp} | {phase} | review | {review_id} | {review_status} |
```

---

## Phase 1: Extract Concepts

### 1.1: Spawn /read-paper Agent

```
Task(
    subagent_type: "general-purpose",
    description: "Extract concepts for {method}",
    prompt: |
        /read-paper {paper_path} --method={method}

        After completing, verify that knowledge_base/{method}/concept.md exists
        and contains all required sections per the skill definition.
    run_in_background: true
)
```

### 1.2: Wait and Verify

Wait for agent completion, then verify:
```bash
ls -la knowledge_base/{method}/concept.md
```

### 1.3: Spawn Review Agent

```
Task(
    subagent_type: "general-purpose",
    description: "Review concept.md",
    prompt: |
        /review-knowledge {method} --phase=concept

        Return a structured result:
        STATUS: [PASS|NEEDS_REVISION|FAIL]
        COMPLETENESS: [n]/10
        HIGH_PRIORITY_ISSUES: [count]
        ISSUES:
        - [list of issues]
        RECOMMENDATIONS:
        - [list of recommendations]
    run_in_background: true
)
```

### 1.4: Process Review Result

Parse the review output. Display to user:

```markdown
## Phase 1 Review Result

**Status**: {PASS|NEEDS_REVISION|FAIL}
**Completeness**: {n}/10
**Pass**: {current}/3

### Issues Found:
{issues_list}

### Recommendations:
{recommendations_list}
```

### 1.5: Decision Handling

Follow the decision logic in Step G above.

---

## Phase 2: Extract Theory

### 2.1: Spawn /understand-theory Agent

```
Task(
    subagent_type: "general-purpose",
    description: "Extract theory for {method}",
    prompt: |
        /understand-theory {paper_path} --method={method}

        Note: concept.md already exists at knowledge_base/{method}/concept.md
        Reference it for context about the method.

        After completing, verify that knowledge_base/{method}/theory.md exists.
    run_in_background: true
)
```

### 2.2: Wait, Verify, Review

Follow same pattern as Phase 1.

---

## Phase 3: Document Code

### 3.1: Repository Resolution Order

Repository URL is resolved by `/learn-code` (Step 1 of that skill) using this chain — orchestrator does NOT need to determine it up front:

```
1. --repo=<url>         (passed through from build-knowledge invocation)
2. methods.yaml         (project-root override file)
3. concept.md github:   (extracted by /read-paper)
4. web search           (only if --web-search-repos is set)
5. MISSING              (writes no_repo stub, marks phase as resolved-with-skip)
```

In **interactive (gated) mode without `--repo=`**: if all chain steps fail and the user has not opted into web search, the orchestrator may ask the user for a URL after `/learn-code` reports MISSING. In **auto mode** (or when invoked from `/run-pipeline --auto`): never prompt — accept the MISSING stub and continue, surfacing it in the build summary.

### 3.2: Spawn /learn-code Agent

Pass through both `--repo=` (if provided) and `--web-search-repos` (if provided):

```
Task(
    subagent_type: "general-purpose",
    description: "Analyze code for {method}",
    prompt: |
        /learn-code {method}{repo_arg}{web_search_arg}

        Note: concept.md and theory.md already exist at knowledge_base/{method}/.
        Use the resolution chain in /learn-code Step 1 to locate the repo:
          - this invocation passed: {repo_arg or "(no --repo)"} {web_search_arg or "(no --web-search-repos)"}
          - methods.yaml at the project root will be consulted if present
          - concept.md github: will be used if those fail

        After completing, verify that knowledge_base/{method}/code.md exists,
        and report the chosen repo_source from its frontmatter (flag/yaml/paper/search/none).
    run_in_background: true
)
```

Where `{repo_arg}` is `" --repo=<url>"` if `--repo=` was passed to `/build-knowledge`, else empty. Similarly for `{web_search_arg}`.

### 3.3: Handle Resolution Outcomes

Read the `repo_source` field from the just-written `code.md` frontmatter:

| `repo_source` | Confidence | Action |
|---------------|------------|--------|
| `flag` | high | Continue to Phase 4 |
| `yaml` | high | Continue to Phase 4 |
| `paper` | high | Continue to Phase 4 |
| `search` | medium | Continue to Phase 4. Surface in build summary so user can audit the chosen repo. |
| `none` | n/a | The no_repo stub was written. In gated mode, ask user; in auto mode, accept and continue. Mark Phase 3 as `resolved-with-skip` in `.build_progress.md`. |

**Do NOT block the build on a search-resolved repo** — that defeats the point of opt-in auto-resolution. Instead, the surfacing in the build summary lets the user catch wrong picks and re-run with `--repo=` if needed.

---

## Phase 4: Extract Figures

### 4.0: Skip Check

If `--skip-figures` was passed:
- Do NOT spawn `/extract-figures`. Do NOT spawn the Phase 4 review agent.
- Confirm Phase 4 is marked `skipped` in `.build_progress.md` (it should already be from Step 0.4 init); append a row to the Agent Log noting the skip.
- Proceed directly to Phase 5.

### 4.1: Spawn /extract-figures Agent

```
Task(
    subagent_type: "general-purpose",
    description: "Extract figures for {method}",
    prompt: |
        /extract-figures {paper_path} --method={method}

        After completing, verify that knowledge_base/{method}/figures.md exists.
    run_in_background: true
)
```

---

## Phase 5: Process Supplement

### 5.1: Check if Supplement Provided

If no supplement, skip to Phase 6.

### 5.2: Spawn /split-supplement Agent (if needed)

For large supplements (>20 pages):

```
Task(
    subagent_type: "general-purpose",
    description: "Process supplement for {method}",
    prompt: |
        /split-supplement {supplement_path} --method={method}

        Merge extracted information into existing documents:
        - Additional theory → theory.md
        - Supplementary figures → figures.md   {# omit this line if --skip-figures was passed #}
        - Additional use cases → concept.md
    run_in_background: true
)
```

When `--skip-figures` is set, drop the "Supplementary figures → figures.md" line from the prompt so the agent does not create a stub `figures.md`. Supplementary figure information is dropped on the floor in this mode.

---

## Phase 6: Harmonize

### 6.1: Spawn /harmonize Agent

```
Task(
    subagent_type: "general-purpose",
    description: "Harmonize {method} knowledge base",
    prompt: |
        /harmonize {method}

        All documents exist at knowledge_base/{method}/:
        - concept.md
        - theory.md
        - code.md
        - figures.md   {# omit this line if --skip-figures was passed; /harmonize works with whatever files are present #}

        Ensure:
        1. Consistent terminology across all documents
        2. Cross-references between documents
        3. No redundancy
        4. Navigation index in each file
        5. harmonized: {date} metadata field added
    run_in_background: true
)
```

### 6.2: Final Comprehensive Review

```
Task(
    subagent_type: "general-purpose",
    description: "Final review for {method}",
    prompt: |
        /review-knowledge {method} --phase=all

        This is the FINAL review. Check:
        1. All individual document requirements
        2. Cross-document consistency
        3. Cross-references validity
        4. No contradictions
        5. Ready for downstream use

        Return structured result with overall assessment.
    run_in_background: true
)
```

If `--skip-figures` was passed, append `--skip-figures` to the `/review-knowledge` prompt so it does not flag the missing `figures.md` as a quality issue.

---

## Quality Gate Thresholds

| Status | Completeness | High-Priority Issues | Orchestrator Action |
|--------|--------------|----------------------|---------------------|
| PASS | ≥ 8/10 | 0 | Auto-continue to next phase |
| NEEDS_REVISION | 6-7/10 | 1-2 | Ask user: Refine / Accept / Edit |
| FAIL | < 6/10 | 3+ | Must fix before continuing |

---

## User Interaction Points

The orchestrator asks user input at these points:

### 1. After NEEDS_REVISION (passes < 3)

**"Review found issues in {document}.md (Pass {n}/3). How would you like to proceed?"**
- [ ] Refine and re-run (provide guidance below)
- [ ] Accept current state and continue
- [ ] Let me manually edit first

If refine selected, also ask:

**"What guidance should I provide to the agent for refinement?"**
- [ ] Focus on: {specific_issues}
- [ ] General instruction: {text_input}

### 2. After 3 Passes Still NEEDS_REVISION

**"Pass limit reached (3/3) for {document}.md. You must choose:"**
- [ ] Accept current state (issues will be logged)
- [ ] Let me manually edit the file
- [ ] Abort the build process

### 3. After FAIL

**"Critical issues found in {document}.md. How would you like to proceed?"**
- [ ] Retry with different approach
- [ ] Let me manually edit the file
- [ ] Skip this phase (create placeholder)
- [ ] Abort the build process

### 4. Supplement Processing (Optional)

**"Supplementary material processed. Review the updates?"**
- [ ] Yes, show what was added
- [ ] No, proceed to harmonization

---

## Error Handling

### Agent Timeout

If a phase agent times out (>10 minutes):

```markdown
⚠️ **Agent Timeout**: Phase {n} agent did not complete within 10 minutes.

**Options:**
- [ ] Retry the phase
- [ ] Check agent output log: {output_file}
- [ ] Abort build
```

### Agent Failure

If agent returns error:

```markdown
❌ **Agent Error**: Phase {n} agent failed.

**Error**: {error_message}

**Options:**
- [ ] Retry with different parameters
- [ ] Skip this phase
- [ ] Abort build
```

### Missing Output

If expected file not created:

```markdown
⚠️ **Missing Output**: {document}.md was not created.

**Possible causes:**
- Agent encountered an error
- Paper content insufficient for extraction

**Options:**
- [ ] Retry the phase
- [ ] Create placeholder and continue
- [ ] Abort build
```

---

## Resuming Interrupted Builds

When `/build-knowledge` is called and `.build_progress.md` exists:

1. Read the progress file
2. Find last completed phase
3. Check for any in-progress agents (by agent_id)

**"Found interrupted build for {method}."**

```markdown
## Build Status

| Phase | Status | Passes |
|-------|--------|--------|
| 1 | complete | 2 |
| 2 | complete | 1 |
| 3 | in_progress | 1 |
| 4-6 | pending | 0 |

Last agent: {agent_id} for Phase 3
```

**"How would you like to proceed?"**
- [ ] Resume Phase 3 (check if agent finished)
- [ ] Restart Phase 3
- [ ] Review Phase 2 output first
- [ ] Start fresh

---

## Final Output Structure

```
knowledge_base/{method}/
├── README.md              # Auto-generated summary
├── concept.md             # Phase 1 output
├── theory.md              # Phase 2 output
├── code.md                # Phase 3 output
├── figures.md             # Phase 4 output (absent when --skip-figures was passed)
├── .build_progress.md     # Build tracking (hidden)
└── .review_report.md      # Final review report (hidden)
```

---

## Implementation Notes for Orchestrator

### Spawning Agents

Use the Task tool with these parameters:

```
Task(
    subagent_type: "general-purpose",  # Always use this for skills
    description: "Short description",   # 3-5 words
    prompt: "Full prompt with context",
    run_in_background: true             # Critical for context isolation
)
```

### Checking Agent Status

```
TaskOutput(
    task_id: "{agent_id}",
    block: false,           # Non-blocking check
    timeout: 1000           # Quick check
)
```

Returns status: running / completed / failed

### Waiting for Agent

```
TaskOutput(
    task_id: "{agent_id}",
    block: true,            # Wait for completion
    timeout: 600000         # 10 minute max
)
```

### Reading Agent Output

If you need to check progress before completion:

```
Read(file_path: "{output_file}")
```

---

## Example Orchestrator Execution Flow

```
1. User: /build-knowledge paper.pdf --method=MethodX

2. Orchestrator:
   - Parse arguments
   - Create knowledge_base/MethodX/
   - Initialize .build_progress.md

3. Phase 1:
   - Spawn: Task(/read-paper paper.pdf --method=MethodX, background=true)
   - Wait: TaskOutput(agent_id, block=true)
   - Verify: ls knowledge_base/MethodX/concept.md
   - Spawn: Task(/review-knowledge MethodX --phase=concept, background=true)
   - Wait: TaskOutput(review_id, block=true)
   - Parse: status=PASS
   - Update: .build_progress.md

4. Phase 2:
   - Spawn: Task(/understand-theory paper.pdf --method=MethodX, background=true)
   - Wait: TaskOutput(agent_id, block=true)
   - Spawn: Task(/review-knowledge MethodX --phase=theory, background=true)
   - Wait: TaskOutput(review_id, block=true)
   - Parse: status=NEEDS_REVISION, passes=1
   - Ask user: Refine / Accept / Edit
   - User: Refine with "Focus on missing notation definitions"
   - Spawn: Task(/understand-theory ... --focus="notation", background=true)
   - ... (repeat until PASS or pass limit)

5. [Phases 3-5 similar pattern]

6. Phase 6:
   - Spawn: Task(/harmonize MethodX, background=true)
   - Wait: TaskOutput(agent_id, block=true)
   - Spawn: Task(/review-knowledge MethodX --phase=all, background=true)
   - Wait: TaskOutput(review_id, block=true)
   - Parse: status=PASS
   - Generate README.md
   - Mark build complete

7. Output:
   "Knowledge base for MethodX complete!"
   - concept.md: 9/10 (PASS)
   - theory.md: 8/10 (PASS after 2 passes)
   - code.md: 9/10 (PASS)
   - figures.md: 8/10 (PASS)
   - Final review: PASS
```

---

## Comparison with Sequential Execution

| Aspect | Sequential (old) | Background Agents (new) |
|--------|------------------|-------------------------|
| Context usage | Accumulates (~50k/phase) | Fresh each phase (~50k max) |
| Max phases | ~3 before context full | All 6 phases easily |
| Resumability | Manual via progress file | Built-in via agent IDs |
| Parallelism | None | Possible (not recommended) |
| Error isolation | Errors affect whole session | Errors isolated to agent |
| User interaction | Inline | Between agent spawns |

---

## Tips

- The orchestrator should be minimal - just tracking, spawning, and deciding
- Each agent prompt should include necessary context (file paths, prior phase outputs)
- Use non-blocking TaskOutput to show progress to user while waiting
- If a phase is taking many passes, consider whether source material is sufficient
- The agent log in .build_progress.md is useful for debugging

---

*This orchestrator uses background agents to enable complete builds without context exhaustion.*
