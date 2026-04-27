---
name: evaluate-fit
description: "Assess whether a method is a good fit for your specific project, data, and analysis goals"
---

# Codex Adapter

This adapter is generated from `skills/evaluate-fit/SKILL.md`. Edit the source Claude skill, then run `python3 scripts/sync_codex_skills.py` to refresh the Codex mirror.

Preserve the shared workflow contract: `knowledge_base/`, `projects/<name>/literature/`, `fitness_summary.md`, `analysis_plan.md`, audit files, and progress files remain the expected outputs.

## Claude-to-Codex Term Map

- `/skill-name` examples mean `$skill-name` or explicit plugin/skill invocation in Codex.
- `Task` / `TaskOutput` mean delegated/fresh-agent execution when available; otherwise run phases sequentially and verify files.
- `AskUserQuestion` means ask the user directly when required.
- `WebFetch` / `WebSearch` mean Codex web/search tools when available.

## Source Skill Instructions

# Evaluate Fit Skill (Parallel Architecture)

This skill assesses whether bioinformatics methods in the knowledge base are appropriate for your specific project. It supports **parallel evaluation of multiple methods** using background agents.

## Usage Modes

### Mode 1: Single Method
```
/evaluate-fit <method-name> projects/{project}/context.md
```
**When to use**: Quick check of one specific method — e.g., a teammate suggests a tool you haven't evaluated yet, or you've added a new knowledge base entry and want to assess it against an existing project context without re-running the full suite. Runs in the current context, no background agents.

### Mode 2: All Methods with Knowledge Bases
```
/evaluate-fit --all projects/{project}/context.md --project={project}
```
**When to use**: Initial project setup, or after building several new knowledge base entries. Spawns parallel agents for each method.

### Mode 3: Specific Methods
```
/evaluate-fit --methods=method1,method2,method3 projects/{project}/context.md --project={project}
```
**When to use**: You know which methods are candidates and want a comparison without running all knowledge base entries. Useful when the KB is large but only a subset is relevant to the modality.

---

## Architecture Overview (Parallel Mode)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (lightweight)                       │
│  - Parses arguments (--all, --methods, --project)                   │
│  - Discovers methods with knowledge bases                           │
│  - Spawns evaluation agents in parallel                             │
│  - Tracks progress in .evaluation_progress.md                       │
│  - Generates summary comparison report                              │
└─────────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Agent 1    │ │  Agent 2    │ │  Agent 3    │ │  Agent N    │
│ (method 1)  │ │ (method 2)  │ │ (method 3)  │ │ (method N)  │
│             │ │             │ │             │ │             │
│ Own context │ │ Own context │ │ Own context │ │ Own context │
│ (~200k tok) │ │ (~200k tok) │ │ (~200k tok) │ │ (~200k tok) │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │               │
       ▼               ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ <method1>_  │ │ <method2>_  │ │ <method3>_  │ │ <methodN>_  │
│ fitness_    │ │ fitness_    │ │ fitness_    │ │ fitness_    │
│ assessment  │ │ assessment  │ │ assessment  │ │ assessment  │
│ .md         │ │ .md         │ │ .md         │ │ .md         │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

**Benefits:**
- Each method gets fresh context (~200k tokens)
- Can evaluate 10+ methods without context exhaustion
- Parallel execution reduces total time
- Failed evaluations don't block others

---

## Workflow: Parallel Mode (--all or --methods)

### Step 0: Parse Arguments

Extract from `$ARGUMENTS`:
- **--all**: Evaluate all methods with knowledge bases
- **--methods=a,b,c**: Comma-separated list of specific methods
- **context_file.md** (required): Project context file path
- **--project=folder** (optional): Project folder name under `projects/`

### Step 1: Discover Available Methods

```bash
# Find methods with complete knowledge bases (at minimum concept.md)
for method in $(ls knowledge_base/); do
  if [[ -f "knowledge_base/$method/concept.md" ]]; then
    echo "$method"
  fi
done
```

### Step 2: Validate Inputs

1. Check context file exists
2. If `--methods` specified, verify each method has knowledge base
3. If `--project` specified, verify or create folder
4. Skip methods that already have assessments (unless `--force`)

Ask user if ambiguous:

**"Found N methods with knowledge bases. Which would you like to evaluate?"**
- [ ] All N methods
- [ ] Only methods relevant to my modality: [list based on context]
- [ ] Let me specify: [text input]

### Step 3: Initialize Progress Tracker

Create `projects/{project}/.evaluation_progress.md`:

```markdown
---
project: {project}
context: {context_file}
started: {date}
architecture: parallel-agents
---

# Fitness Evaluation Progress

| Method | Status | Agent ID | Fit Score | Updated |
|--------|--------|----------|-----------|---------|
| {method1} | pending | - | - | - |
| {method2} | pending | - | - | - |
| ... | ... | ... | ... | ... |

## Agent Log

| Timestamp | Method | Agent ID | Status |
|-----------|--------|----------|--------|
```

### Step 4: Spawn Evaluation Agents in Parallel

For each method, spawn a background agent:

```
Task(
    subagent_type: "general-purpose",
    description: "Evaluate {method} fitness",
    prompt: |
        You are evaluating whether {method} is a good fit for a bioinformatics project.

        ## Your Task
        Generate a fitness assessment following the template below.

        ## Context File
        Read the project context from: {context_file_path}

        ## Knowledge Base Files to Read
        Read ALL of these files for {method}:
        - knowledge_base/{method}/concept.md (REQUIRED)
        - knowledge_base/{method}/theory.md (if exists)
        - knowledge_base/{method}/code.md (if exists)
        - knowledge_base/{method}/figures.md (if exists)

        ## Assessment Template
        Create a file at: projects/{project}/{method}_fitness_assessment.md

        Use this structure:
        ```markdown
        ---
        method: {method}
        project: {project}
        context_file: {context_file_name}
        assessed: {date}
        fit_score: [Excellent/Good/Moderate/Poor/Not Recommended]
        ---

        # Fitness Assessment: {method} for {project_title}

        ## Overall Verdict

        **Fit Score**: **[score]**

        **Summary**: [2-3 sentences]

        ---

        ## Compatibility Analysis

        ### Modality Match

        | Criterion | {method} | Your Data | Match |
        |-----------|----------|-----------|-------|
        | Data type | [method modality] | [user modality] | [check/x/warning] |
        | Data format | [supported formats] | [user format] | [check/x/warning] |
        | Organism | [supported] | [user organism] | [check/x/warning] |

        ### Task Alignment

        | Your Need | {method} Capability | Fit |
        |-----------|---------------------|-----|
        | [need 1] | [capability] | [check/x/warning] |
        | ... | ... | ... |

        ### Use Case Similarity

        | Your Context | {method} Original Use Cases | Similarity |
        |--------------|----------------------------|------------|
        | [context 1] | [original use] | [High/Moderate/Low/Novel] |
        | ... | ... | ... |

        ---

        ## Strengths (Why This Method Fits)

        1. **[Strength title]**: [explanation with reference to user context]
        2. ...

        ---

        ## Considerations (Potential Concerns)

        1. **[Concern title]**: [explanation]
           - **Mitigation**: [how to address]
        2. ...

        ---

        ## Specific Tasks {method} Can Accomplish

        ### Task 1: [Task Name]
        - **What**: [description]
        - **How**: [approach, reference to theory/code]
        - **Expected output**: [what user gets]
        - **Reference**: [link to knowledge_base section]

        ### Task 2: [Task Name]
        ...

        ---

        ## Configuration Recommendations

        For your specific use case:

        1. **[Setting]**: [recommendation] because [reason]
        2. ...

        ---

        ## Alternative Methods to Consider

        | Alternative | When to Consider |
        |-------------|------------------|
        | [method] | [scenario] |
        | ... | ... |

        ---

        ## Knowledge Base References

        - Detailed methodology: [theory.md](../knowledge_base/{method}/theory.md)
        - Implementation guide: [code.md](../knowledge_base/{method}/code.md)
        - Visual examples: [figures.md](../knowledge_base/{method}/figures.md)
        - Use cases and limitations: [concept.md](../knowledge_base/{method}/concept.md)

        ---

        *Generated by `/evaluate-fit` skill on {date}*
        ```

        ## Fit Score Criteria

        | Score | Criteria |
        |-------|----------|
        | **Excellent** | Modality match, all goals addressed, use case highly similar, no critical limitations |
        | **Good** | Modality match, most goals addressed, similar use case, minor limitations |
        | **Moderate** | Modality match, some goals addressed, requires extrapolation, notable limitations |
        | **Poor** | Partial modality match, limited goal coverage, significant limitations apply |
        | **Not Recommended** | Modality mismatch, goals not addressed, or critical limitations |

        ## Important Notes
        - Be honest about fit - don't oversell or undersell
        - Reference specific sections of knowledge base documents
        - Provide actionable configuration recommendations
        - Consider the user's specific experimental design and constraints
        - Use relative paths for links (../knowledge_base/{method}/)

        After writing the assessment, output a summary line:
        FIT_SCORE: [score]
        ASSESSMENT_FILE: projects/{project}/{method}_fitness_assessment.md
    ,
    run_in_background: true
)
```

### Step 5: Monitor Progress

While agents are running, periodically check status:

```
TaskOutput(
    task_id: {agent_id},
    block: false,
    timeout: 1000
)
```

Update progress tracker with status changes.

### Step 6: Wait for All Agents

Wait for all agents to complete (with timeout):

```
for each agent_id:
    TaskOutput(
        task_id: agent_id,
        block: true,
        timeout: 600000  # 10 minutes
    )
```

### Step 7: Verify Outputs

Background agents can complete successfully without writing the expected file (e.g., due to sandboxed Write denials). For each agent, apply the **Output Verification Protocol**:

```bash
ls -la projects/{project}/{method}_fitness_assessment.md
wc -l projects/{project}/{method}_fitness_assessment.md
```

Each assessment must pass all four checks:
1. **Existence**: file exists on disk
2. **Size**: ≥ 1 KB (an empty or stub file indicates a write failure)
3. **Frontmatter**: YAML parses and contains `method:`, `fit_score:` fields
4. **Sections**: at least these `##` headers are present: "Overall Verdict", "Compatibility Analysis", "Strengths", "Considerations"

For any agent whose output fails verification:
- Mark the method as `verification_failed` in `.evaluation_progress.md`
- Record the agent ID and output log path
- Continue with successful agents (do not block summary on partial failures)
- Surface failed methods in the final report so the user can re-run them

**Do not silently retry** — re-running the same prompt usually reproduces the failure. Surface the issue and let the user decide.

### Step 8: Generate Summary Comparison Report (Agent-Based)

The summary is the **integrative** output of `/evaluate-fit`: it ranks methods, picks a primary recommendation, and suggests pipeline combinations. The orchestrator does NOT write this inline — it spawns a dedicated background agent so the synthesis step gets fresh context, and so it can be **ensembled** when `--ensemble-summary` is set.

#### Single-run path (default)

Spawn one aggregation agent:

```
Task(
    subagent_type: "general-purpose",
    description: "Aggregate fitness summary for {project}",
    prompt: |
        You are aggregating per-method fitness assessments into a single
        comparison summary and pipeline recommendation.

        ## Inputs to read
        - projects/{project}/context.md
        - All files matching: projects/{project}/*_fitness_assessment.md
          (one per method that was successfully evaluated)

        ## Output
        Write to: projects/{project}/fitness_summary.md

        Use the template below.

        ## Template
        ```markdown
        ---
        project: {project}
        context_file: {context_file_name}
        methods_evaluated: [list]
        primary_recommendation: {method}
        generated: {date}
        ---

        # Fitness Assessment Summary: {project}

        **Evaluated**: {date}
        **Context**: {context_file}
        **Methods Evaluated**: {N}

        ## Quick Comparison

        | Method | Fit Score | Primary Strength | Main Concern |
        |--------|-----------|------------------|--------------|
        | {method} | {score} | {strength}      | {concern}    |
        | ...      | ...     | ...             | ...          |

        ## By Fit Score

        ### Excellent Fit
        - **{method}**: [brief reason]

        ### Good Fit
        - **{method}**: [brief reason]

        ### Moderate Fit
        - **{method}**: [brief reason]

        ### Poor Fit / Not Recommended
        - [none or list]

        ## Recommendations

        Based on the project context:

        1. **Primary recommendation**: [method] because [reason]
        2. **Alternative**: [method] for [specific use case]
        3. **Complementary**: [method1] + [method2] together

        ## Individual Assessments

        - [<method1>_fitness_assessment.md](<method1>_fitness_assessment.md)
        - ...

        ---

        *Generated by `/evaluate-fit` on {date}*
        ```

        ## Rules
        - Every claim must be grounded in one of the per-method assessment files.
          Cite the method by name in the assessment.
        - The "Primary recommendation" must respect the project's stated constraints
          in context.md (panel size, sample size, enrichment, etc.).
        - If two methods are nearly tied, say so — do not invent a tiebreaker.
        - If no method scores ≥ Good, surface this in the recommendation rather
          than promoting a Moderate fit to Primary.
    ,
    run_in_background: true
)
```

Wait via `TaskOutput(block: true)`, then verify `projects/{project}/fitness_summary.md` exists and has frontmatter + the "Quick Comparison", "Recommendations", "Individual Assessments" sections.

#### Ensemble path (`--ensemble-summary`)

When the flag is set, run the aggregation **twice as independent agents**, then a **third independent adjudicator** produces the canonical file.

**Run v1**: same prompt as above, but instruct the agent:

> "IMPORTANT (ensemble run 1 of 2): You are running INDEPENDENTLY. Do NOT look at any *_v1.md or *_v2.md files. Skip any interactive review prompts."

After the agent completes and writes `projects/{project}/fitness_summary.md`, rename:

```bash
mv projects/{project}/fitness_summary.md projects/{project}/fitness_summary_v1.md
```

**Run v2**: identical prompt, fresh agent, then `mv` to `_v2.md`.

**Adjudicator**:

```
Task(
    subagent_type: "general-purpose",
    description: "Adjudicate fitness summary for {project}",
    prompt: |
        You are the INDEPENDENT ADJUDICATOR for a fitness-assessment summary.
        Two prior agents produced these versions independently:
          - projects/{project}/fitness_summary_v1.md
          - projects/{project}/fitness_summary_v2.md

        Source-of-truth inputs (use BOTH to settle disagreements AND to
        verify high-stakes agreements):
          - projects/{project}/context.md
          - All projects/{project}/*_fitness_assessment.md (per-method assessments)

        Your job:

        1. Read v1 and v2.

        2. For each section, classify each substantive claim as:
           - AGREE: both versions assert it.
           - DISAGREE: versions conflict (e.g. different primary recommendations,
             different fit-score ratings).
           - UNIQUE_TO_V1 / UNIQUE_TO_V2: only one version has it.

        3. For DISAGREE items: read the relevant per-method assessment files,
           pick the better-supported version, OR keep both with a flagged
           uncertainty note if neither is clearly grounded.

        4. For UNIQUE items: include only if grounded in a per-method
           assessment; otherwise drop.

        5. AGREE verification (catches false consensus). Both v1 and v2 can
           assert the same plausible-sounding but unsupported thing. For each
           AGREE item, ask: "If this is wrong, does a downstream decision
           break?" — if yes, spot-check it. Target ~5-8 spot-checks weighted
           toward these high-stakes AGREE claims:

             a) The PRIMARY recommendation — verify the per-method assessment
                actually supports its claimed strengths and that no claimed
                concern is severe enough to disqualify it.
             b) Fit scores at category boundaries (e.g. a method rated
                "Excellent" in both v1 and v2) — verify the assessment
                supports the rating; demote on insufficient support.
             c) Claimed strengths and concerns in the "Quick Comparison"
                table — verify each phrase appears in or is supported by
                the corresponding assessment.
             d) Pipeline complementarity claims ("use Method A + Method B
                together") — verify both methods' assessments support the
                combination.

           For each spot-check: read the relevant per-method assessment
           file. If a spot-checked AGREE claim is NOT supported, demote it
           in the audit log to DISAGREE_FLAGGED, and either remove it from
           the canonical summary or rewrite it with the actual support.

        6. Pay extra attention to the "Primary recommendation":
           - v1 and v2 AGREE on the same method → still spot-check per (5a).
           - v1 and v2 DISAGREE → read the assessments for both candidate
             methods and pick the one whose assessment best supports it
             given the project's stated constraints. If genuinely tied,
             recommend both and flag the tie.

        7. Produce TWO files:

           a) projects/{project}/fitness_summary.md
              The final, adjudicated summary. Same template as the single-run
              version. Apply the per-claim classifications from steps 2-5.

           b) projects/{project}/fitness_summary_adjudication.md
              The audit log. For each section, list AGREE /
              DISAGREE-resolved / DISAGREE-flagged / UNIQUE-kept /
              UNIQUE-dropped decisions with reasoning. Include a
              "Spot-checks performed" subsection listing which AGREE claims
              were verified and what was found.

              End the audit log with the structured rubric block, computed
              DETERMINISTICALLY from your counts (do NOT self-rate):

              ```yaml
              counts:
                N_AGREE: <int>              # AGREE items kept after spot-checks
                N_DISAGREE_RESOLVED: <int>  # conflicts settled from assessments
                N_DISAGREE_FLAGGED: <int>   # conflicts left flagged + AGREE items demoted
                N_UNIQUE_KEPT: <int>        # UNIQUE items grounded, kept
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

        8. Do NOT silently merge or pick one version wholesale.

        Return a one-paragraph summary of (a) how much v1/v2 agreed, especially
        on the Primary recommendation, and (b) any AGREE claims that turned
        out NOT to be supported in spot-checks.
    ,
    run_in_background: true
)
```

Verify both adjudicator outputs exist and pass the section check. Parse the YAML rubric block from the audit log and surface `confidence`, `human_review_needed`, and `len(flagged_items)` in the user-facing summary at Step 9.

Token cost: ensemble adds ~2.5× the aggregation step (two runs + one adjudicator with ~5-8 source-file spot-checks). It does NOT re-run the per-method assessments — those remain single-run. The aggregation is the natural ensemble target because it is the integrative judgment call (which method wins, what pipeline to recommend) where divergence between independent runs is informative, AND the adjudicator's AGREE-verification catches the failure mode where v1 and v2 both confidently state an unsupported claim.

### Step 9: Report to User

Present summary:

```markdown
## Fitness Evaluation Complete

Evaluated **{N} methods** for your {project} project.

### Results by Fit Score:

| Score | Methods |
|-------|---------|
| Excellent | {list} |
| Good | {list} |
| Moderate | {list} |
| Poor | {list or "—"} |

### Files Generated:
- Summary: `projects/{project}/fitness_summary.md`
- Individual assessments: `projects/{project}/*_fitness_assessment.md`

### Recommended Next Steps:
1. Review the summary comparison
2. Read detailed assessments for top candidates
3. Run `/adapt-method` to apply the best-fit method to your data
```

---

## Workflow: Single Method Mode (Original)

When called without `--all` or `--methods`:

```
/evaluate-fit <method-name> projects/{project}/context.md
```

### Step 1: Identify Method and Context

Parse `$ARGUMENTS` to determine:
1. **Method name** (required) - The method to evaluate (must have knowledge base entries)
2. **Context file** (optional) - A markdown file describing your project/data

If no method is specified, list available methods:

```bash
ls knowledge_base/
```

Then ask the user which method to evaluate.

### Step 2: Load Method Knowledge Base

Read all available knowledge base files for the method:

1. `knowledge_base/<method>/concept.md` - **Required** (contains use cases, limitations)
2. `knowledge_base/<method>/theory.md` - If available
3. `knowledge_base/<method>/code.md` - If available
4. `knowledge_base/<method>/figures.md` - If available

Extract key information for evaluation:
- **Task tags**: What does the method do?
- **Modality tags**: What data types does it support?
- **Input requirements**: Data format, preprocessing needs
- **Limitations**: When NOT to use
- **Original use cases**: What scenarios was it designed for?
- **Benchmarks**: How does it compare to alternatives?

### Step 3: Gather User Context

#### Option A: Context File Provided

Read the provided markdown file and extract:
- Dataset characteristics (modality, size, structure)
- Experimental design (groups, conditions, batches)
- Technical details (sequencing depth, QC constraints)
- Analysis goals
- Known issues or special considerations

#### Option B: No Context File - Interactive Questionnaire

Present a series of multiple-choice questions to gather necessary context. Ask questions in logical groups, 2-3 at a time.

**Group 1: Data Modality & Format**

1. **What is your data modality?**
   - [ ] scRNA-seq only
   - [ ] CITE-seq (RNA + ADT protein)
   - [ ] ATAC-seq
   - [ ] Spatial transcriptomics
   - [ ] Multimodal (multiple assays)
   - [ ] Other (please specify)

2. **What data format do you have?**
   - [ ] Raw count matrix
   - [ ] Seurat object (R)
   - [ ] AnnData object (Python)
   - [ ] CellRanger output
   - [ ] Other (please specify)

**Group 2: Experimental Design**

3. **What is your experimental design?**
   - [ ] Single condition (exploration/atlas)
   - [ ] Case vs control comparison
   - [ ] Time series / longitudinal
   - [ ] Multiple conditions (>2 groups)
   - [ ] Complex factorial design
   - [ ] Other (please specify)

4. **Do you have batch effects to address?**
   - [ ] No batches (single batch)
   - [ ] Technical batches (same samples, different processing)
   - [ ] Biological batches (different donors/samples)
   - [ ] Multi-site study (different institutions)
   - [ ] Unsure

**Group 3: Analysis Goals**

5. **What is your primary analysis goal?** (Select all that apply)
   - [ ] Cell type annotation / clustering
   - [ ] Batch correction / integration
   - [ ] Differential expression / abundance
   - [ ] Trajectory / pseudotime analysis
   - [ ] Normalization / quality control
   - [ ] Feature selection
   - [ ] Other (please specify)

6. **What level of automation do you prefer?**
   - [ ] Fully automated with sensible defaults
   - [ ] Semi-automated with some manual tuning
   - [ ] Full control over all parameters
   - [ ] Interactive / GUI-based

**Group 4: Technical Constraints**

7. **What is your dataset size?**
   - [ ] Small (<10,000 cells)
   - [ ] Medium (10,000 - 100,000 cells)
   - [ ] Large (100,000 - 1M cells)
   - [ ] Very large (>1M cells)

8. **What computational environment will you use?**
   - [ ] Local workstation
   - [ ] HPC cluster
   - [ ] Cloud computing
   - [ ] Limited resources (need lightweight methods)

**Group 5: Special Considerations**

9. **Are there specific technical issues with your data?**
   - [ ] Low sequencing depth
   - [ ] High dropout / sparsity
   - [ ] Ambient contamination
   - [ ] Doublet concerns
   - [ ] Imbalanced cell populations
   - [ ] Missing cell types in some batches
   - [ ] None / not sure

10. **Do you have any of the following available?**
    - [ ] Prior knowledge about expected cell types
    - [ ] Reference dataset for annotation
    - [ ] Flow cytometry gates as ground truth
    - [ ] Known marker genes/proteins
    - [ ] None of the above

### Step 4: Perform Compatibility Assessment

Compare the method's characteristics against the user's context:

#### 4a: Modality Match
| Criterion | Method | User's Data | Match |
|-----------|--------|-------------|-------|
| Data type | [method modality tags] | [user modality] | ✓/✗/⚠️ |
| Data format support | [method input formats] | [user format] | ✓/✗/⚠️ |

#### 4b: Task Alignment
| User's Goal | Method Capability | Fit |
|-------------|-------------------|-----|
| [user goal 1] | [relevant method task] | ✓/✗/⚠️ |
| [user goal 2] | [relevant method task] | ✓/✗/⚠️ |

#### 4c: Use Case Similarity
Compare user's scenario to method's original use cases:
- Similar experimental design?
- Similar data characteristics?
- Similar analysis goals?
- Potential extrapolation needed?

#### 4d: Limitation Check
Review each method limitation against user's context:
- Does any limitation apply to user's situation?
- Are there workarounds?
- Is the limitation critical or minor?

#### 4e: Technical Fit
- Dataset size vs. method scalability
- Computational requirements vs. user resources
- Automation level vs. user preference

### Step 5: Generate Fitness Report

Create a structured assessment report (see template in parallel mode Step 4).

### Step 6: Verify and Refine

Review the fitness assessment:

#### Accuracy Check
- [ ] All claims about method capabilities are backed by knowledge base content
- [ ] User context has been accurately represented
- [ ] Compatibility assessments are justified with specific evidence

#### Completeness Check
- [ ] All user goals addressed
- [ ] All method limitations considered
- [ ] Specific, actionable tasks identified
- [ ] Configuration recommendations are practical

#### Tone Check
- [ ] Assessment is honest (doesn't oversell or undersell)
- [ ] Concerns are clearly stated with mitigations where possible
- [ ] Verdict is clear and defensible

Make corrections as needed.

### Step 7: Save Assessment

Save to: `projects/{project}/{method}_fitness_assessment.md`

If no project folder specified, ask user or derive from context file name.

### Step 8: Deliver Results

Present the fitness assessment to the user:

1. **Summary verdict** - Clear recommendation
2. **Key takeaways** - 3-5 bullet points
3. **File location** - Where the assessment was saved
4. **Next steps** - What to do based on the verdict

---

## Fit Score Criteria

| Score | Criteria |
|-------|----------|
| **Excellent** | Modality match, all goals addressed, use case highly similar, no critical limitations |
| **Good** | Modality match, most goals addressed, similar use case, minor limitations |
| **Moderate** | Modality match, some goals addressed, requires extrapolation, notable limitations |
| **Poor** | Partial modality match, limited goal coverage, significant limitations apply |
| **Not Recommended** | Modality mismatch, goals not addressed, or critical limitations |

---

## Example Usage

### Single Method
```
/evaluate-fit <method-name>
/evaluate-fit <method-name> projects/{project}/context.md
```

### All Methods (Parallel)
```
/evaluate-fit --all projects/{project}/context.md --project={project}
```

### Specific Methods (Parallel)
```
/evaluate-fit --methods=method1,method2,method3 projects/{project}/context.md --project={project}
```

---

## Skipping Already-Assessed Methods

By default, methods with existing assessments are skipped. To re-evaluate:

```
/evaluate-fit --all projects/{project}/context.md --project={project} --force
```

Or to re-evaluate specific methods:
```
/evaluate-fit --methods=<method-name> projects/{project}/context.md --project={project} --force
```

---

## Error Handling

### Agent Timeout
If an evaluation agent times out (>10 minutes):
- Log the failure in progress tracker
- Continue with other methods
- Report incomplete evaluations at the end

### Missing Knowledge Base
If a method lacks concept.md:
- Skip the method
- Note it as "incomplete knowledge base" in summary

### Context File Issues
If context file is missing or malformed:
- Stop and ask user for valid context
- Cannot proceed without context

---

## Project Folder Structure

```
<project-root>/
├── knowledge_base/
│   ├── <method-1>/
│   ├── <method-2>/
│   └── ...
├── projects/
│   └── <project-name>/
│       ├── context.md                          # Input context
│       ├── .evaluation_progress.md             # Progress tracker
│       ├── <method-1>_fitness_assessment.md    # Individual assessment
│       ├── <method-2>_fitness_assessment.md
│       ├── ...
│       └── fitness_summary.md                  # Comparison summary
└── .claude/skills/
```

---

## Tips

- Always provide a context file for best results
- Use `--all` to get a comprehensive view of available tools
- Review the summary first, then dive into individual assessments
- "Moderate" fit doesn't mean "don't use" - it means "proceed with awareness"
- Use `/adapt-method` after selecting your best-fit method

---

*This skill connects method knowledge to your specific use case, enabling informed method selection at scale.*
