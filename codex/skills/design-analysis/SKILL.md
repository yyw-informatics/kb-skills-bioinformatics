---
name: design-analysis
description: "Integrates biology hypotheses from literature synthesis with bioinformatics methods to produce an ordered analytical plan with code-ready templates"
---

# Codex Adapter

This adapter is generated from `skills/design-analysis/SKILL.md`. Edit the source Claude skill, then run `python3 scripts/sync_codex_skills.py` to refresh the Codex mirror.

Preserve the shared workflow contract: `knowledge_base/`, `projects/<name>/literature/`, `fitness_summary.md`, `analysis_plan.md`, audit files, and progress files remain the expected outputs.

## Claude-to-Codex Term Map

- `/skill-name` examples mean `$skill-name` or explicit plugin/skill invocation in Codex.
- `Task` / `TaskOutput` mean delegated/fresh-agent execution when available; otherwise run phases sequentially and verify files.
- `AskUserQuestion` means ask the user directly when required.
- `WebFetch` / `WebSearch` mean Codex web/search tools when available.

## Source Skill Instructions

# Design Analysis Skill

You are designing an **integrated analysis plan** that bridges biology (hypotheses, markers, gene signatures from literature synthesis) with bioinformatics (methods, ecosystems, functions from the knowledge base). This is NOT a summary of either input — it is a **cross-referenced, ordered analytical workflow** that maps each testable hypothesis to the specific bioinformatics tool, function, parameters, and code template needed to test it.

## Critical Principles

1. **Every hypothesis gets a method**: Each biology hypothesis from the literature synthesis must be mapped to at least one bioinformatics method with specific functions and parameters. No hypothesis should be left as "can be tested" without specifying HOW.
2. **Order matters**: The output is an ordered pipeline (QC → normalization → embedding → classification → hypothesis testing), not a flat lookup table. Dependencies between phases must be explicit.
3. **Code-ready output**: Every analytical step must include copy-pasteable Python (or R) code templates that use real function names, real parameter values, and real gene lists from the literature synthesis.
4. **Constraint-aware**: Every recommendation must account for the project's specific constraints (e.g., broken antibodies, small panel, small n, enrichment strategy). Do not recommend methods in configurations that violate known constraints.
5. **Rationale-driven**: Every method choice must cite why it was selected — linking to both the biology need (from literature synthesis) and the bioinformatics capability (from fitness assessment/concept docs).
6. **fitness_summary.md is the backbone**: The pipeline recommendation in the fitness summary is the starting scaffold. Biology hypotheses are woven into this scaffold, not the other way around.

---

## Usage Modes

### Standard
```
/design-analysis projects/{project}/literature/0_synthesis_literature.md projects/{project}/context.md --project={project}
```

### Refresh (re-generate after updates)
```
/design-analysis projects/{project}/literature/0_synthesis_literature.md projects/{project}/context.md --project={project} --refresh
```
Re-runs full synthesis. If `analysis_plan.md` already exists, it will be overwritten.

---

## Architecture: 3 Extraction Agents → 1 Integration Agent

```
┌──────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (you, lightweight)             │
│  1. Parse arguments                                           │
│  2. Verify prerequisites exist                                │
│  3. Read project context (small, ~5KB)                        │
│  4. Spawn 3 extraction agents in parallel (background)        │
│  5. Wait for all agents                                       │
│  6. Spawn 1 integration agent                                 │
│  7. Verify output, clean up, report                           │
│  DO NOT read 0_synthesis_literature.md yourself — save context   │
└──────────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ Extract-Bio │  │Extract-Methods│  │Extract-Ecosys│
│             │  │              │  │              │
│ Reads:      │  │ Reads:       │  │ Reads:       │
│ literature_ │  │ fitness_     │  │ 3 ecosystem  │
│ synthesis.md│  │ summary.md + │  │ indexes      │
│             │  │ 11 concept.md│  │ (scanpy,     │
│ Produces:   │  │ files        │  │  scvi-tools, │
│ Hypotheses, │  │              │  │  seurat)     │
│ signatures, │  │ Produces:    │  │              │
│ gating,     │  │ Method caps, │  │ Produces:    │
│ constraints │  │ task matrix, │  │ Function map,│
│             │  │ APIs         │  │ workflows    │
└──────┬──────┘  └──────┬───────┘  └──────┬───────┘
       ▼                ▼                  ▼
  .design_extract   .design_extract    .design_extract
  _bio.md           _methods.md        _ecosystems.md
       │                │                  │
       └────────────────┼──────────────────┘
                        ▼
          ┌──────────────────────────┐
          │    INTEGRATION AGENT     │
          │                          │
          │ Reads:                   │
          │ - Project context (~5KB) │
          │ - fitness_summary.md     │
          │   (~5KB, pre-synthesized)│
          │ - 3 extraction files     │
          │   (~45KB total)          │
          │                          │
          │ Cross-references:        │
          │ hypothesis → method →    │
          │ function → code template │
          │                          │
          │ Produces:                │
          │ analysis_plan.md         │
          └──────────────────────────┘
```

---

## Step 0: Parse Arguments

Extract from the command arguments:
- **literature_synthesis** (required): Path to the literature synthesis markdown file
- **context_file** (required): Path to the project context markdown file
- **--project=folder** (required): Project folder name under `projects/`
- **--refresh** (optional): Force re-generation even if output exists

If any required argument is missing, ask the user:

**"I need a literature synthesis file, a project context file, and a --project flag. Example: `/design-analysis projects/{project}/literature/0_synthesis_literature.md projects/{project}/context.md --project={project}`"**

---

## Step 1: Verify Prerequisites

Check that all required input files exist:

```
Glob: {literature_synthesis}
Glob: projects/{project}/bioinformatics/fitness_summary.md
```

Also check for concept.md files in the bioinformatics KB:
```
Glob: knowledge_base/*/concept.md
```

And ecosystem indexes:
```
Glob: knowledge_base/ecosystems/*/capabilities.yaml
```

**If literature synthesis missing**: "No literature synthesis found. Run `/synthesize-literature` first to generate it."
**If fitness summary missing**: "No fitness summary found. Run `/evaluate-fit --all` first to assess bioinformatics methods."
**If no concept.md files**: "No method documentation found in the bioinformatics knowledge base."
**If no ecosystem indexes**: "No ecosystem indexes found. Run `/index-docs` for scanpy/scvi-tools/seurat first."

If `projects/{project}/analysis_plan.md` already exists and `--refresh` was NOT specified: ask the user if they want to overwrite.

Count and report:

```
Prerequisites verified:
- Literature synthesis: {literature_synthesis} ✓
- Fitness summary: projects/{project}/bioinformatics/fitness_summary.md ✓
- Method docs: {n} concept.md files found
- Ecosystem indexes: {n} ecosystems indexed
```

---

## Step 2: Read Project Context

Read the context file. Extract a compact project parameters summary:

| Parameter | Value |
|-----------|-------|
| Species | {from context} |
| Tissue | {from context} |
| Cell types of interest | {from context} |
| Technology | {from context — e.g., scRNA-seq, CITE-seq, spatial, etc.} |
| Measurement panel | {if applicable — list markers, flag any non-functional} |
| Experimental design | {groups, timepoints, comparisons} |
| Sample selection | {enrichment / sorting strategy and its implications} |
| Sample size | {n per group} |

You will pass file paths to sub-agents (they read files themselves).

---

## Step 3: Spawn Extraction Agents

Spawn all 3 extraction agents simultaneously in background.

### Agent 1: Extract-Bio

```
Task(
    subagent_type: "general-purpose",
    description: "Extract biology requirements",
    run_in_background: true,
    prompt: |
        You are extracting compact structured biology requirements from a
        literature synthesis for integration with bioinformatics methods.

        ## Your Input
        - **Literature synthesis file**: {literature_synthesis_path}
        - **Output file**: projects/{project}/.design_extract_bio.md

        ## Your Task

        ### 1. Read the literature synthesis
        Read the ENTIRE file. It contains consensus knowledge, gene signatures,
        gating strategies, and testable hypotheses from 13 research papers.

        ### 2. Extract the following sections in compact format

        Write to the output file with this EXACT structure:

        ```
        ---
        source: 0_synthesis_literature.md
        extracted_date: {today}
        ---

        ## Translation Constraints
        (Copy ALL universal translation constraints from Section 1.1 verbatim.
         These are critical for method selection.)

        ## ADT Panel
        | Marker | Protein | Status | Best Use |
        |--------|---------|--------|----------|
        (From Section 1.3 — include ALL markers with functional status)

        ## Hypotheses
        For EACH hypothesis in the Master Hypothesis Ranking (Section 2.5),
        extract and ADD an analytical_need field:

        | Rank | Hypothesis | Type | Papers | Testability | Impact | Score | analytical_need |
        |------|-----------|------|--------|-------------|--------|-------|-----------------|

        Analytical need categories:
        - compositional: Cell type proportion changes between conditions
        - differential_expression: Gene expression changes between conditions
        - module_scoring: Gene signature scoring across conditions
        - classification: Cell type identity / boundary questions
        - multimodal: cross-modality concordance/discordance analysis
        - trajectory: Differentiation, plasticity, or pseudotime analysis
        - interaction: Multi-factor interaction effects (e.g., condition × timepoint)

        A hypothesis may have multiple analytical needs (comma-separated).

        ## Gene Signatures
        Copy the COMPLETE Python signatures dictionary from Section 3.1.
        Include ALL genes in ALL tiers. This must be syntactically valid Python.

        ## Gating Strategy
        Copy the consensus gating strategy from Section 1.4:
        - The ASCII flowchart
        - The Python classification function

        ## Expected Frequencies
        Copy the full frequency table from Section 1.6.

        ## Top 5 Detailed Test Plans
        Copy the detailed test plans from Section 2.1 (the ones with
        specific genes, expected outcomes, statistical approach, caveats).

        ## Conflicting Findings
        Copy the conflicts table from Section 2.2.

        ## Gap-Filling Opportunities
        Copy the gap-filling table from Section 2.3.

        ## Novel Cross-Paper Hypotheses
        Copy the novel hypotheses from Section 2.4.
        ```

        ### 3. Write the output file
        Write to: projects/{project}/.design_extract_bio.md

        ### 4. Report completion
        EXTRACTION: bio
        HYPOTHESES_EXTRACTED: {count}
        SIGNATURES_EXTRACTED: {count}
        OUTPUT: projects/{project}/.design_extract_bio.md
)
```

### Agent 2: Extract-Methods

```
Task(
    subagent_type: "general-purpose",
    description: "Extract method capabilities",
    run_in_background: true,
    prompt: |
        You are extracting compact structured bioinformatics method capabilities
        for integration with biology hypotheses into an analysis plan.

        ## Your Inputs
        - **Fitness summary**: projects/{project}/bioinformatics/fitness_summary.md
        - **Method concept files**: discover by globbing `knowledge_base/*/concept.md`
          and read ALL files found. Skip the `ecosystems/` subdirectory.
        - **Output file**: projects/{project}/.design_extract_methods.md

        ## Your Task

        ### 1. Read the fitness summary
        This contains the synthesized overview of all methods evaluated against
        the project: fit scores, pipeline recommendation, complementary combinations,
        and cross-cutting concerns. This is your primary reference for method selection.

        ### 2. Read each concept.md file
        For each method, extract its analytical capabilities and API details.

        ### 3. Produce the extraction

        Write to the output file with this EXACT structure:

        ```
        ---
        source: fitness_summary.md + {count} concept.md files
        extracted_date: {today}
        methods_extracted: {count}
        ---

        ## Pipeline Backbone
        (Copy the "Primary Pipeline Recommendation" from fitness_summary.md
         — this is the 5-step ordered pipeline that becomes the analysis plan skeleton)

        ## Complementary Combinations
        (Copy the complementary combinations table from fitness_summary.md)

        ## Cross-Cutting Concerns
        (Copy the 5 critical cross-cutting concerns from fitness_summary.md)

        ## Method Capability Registry

        For EACH method, produce this compact entry:

        ### {Method Name}
        - **Fit**: {Good/Moderate}
        - **Language**: {Python/R}
        - **Task categories**: {list from: adt_normalization, joint_embedding,
          cell_classification, compositional_analysis, differential_expression,
          differential_abundance, module_scoring, reference_mapping,
          variance_decomposition, trajectory_inference}
        - **Key API**: {primary function/class name, e.g., scvi.model.TOTALVI}
        - **Input**: {required data format, e.g., AnnData with .obsm['protein_expression']}
        - **Output**: {what it produces, e.g., latent representation, denoised proteins, DE results}
        - **Key parameters for this project**:
          - {param1}: {recommended_value} — {why}
          - {param2}: {recommended_value} — {why}
        - **Limitations for this project**: {1-3 bullet points}
        - **Depends on**: {what preprocessing must happen first}

        ## Method-Task Matrix

        Build a table mapping each analytical task identified from the fitness
        summary to its recommended primary and secondary methods. Use ONLY methods
        present in the concept.md files; do not invent methods. Pull project-specific
        notes (panel size, broken markers, enrichment caveats) from the project
        context. Schema:

        | Analytical Task | Primary Method(s) | Secondary Method(s) | Notes |
        |----------------|-------------------|---------------------|-------|
        | {task from fitness summary} | {primary method} | {secondary method} | {project-specific caveat} |

        ## Method Execution Order

        Derive an ordered execution list from the pipeline backbone + method
        dependencies in the fitness summary. Each entry should follow:

        N. {Phase name} ({method}) → {what it requires from earlier phases}
        ```

        ### 4. Write the output file
        Write to: projects/{project}/.design_extract_methods.md

        ### 5. Report completion
        EXTRACTION: methods
        METHODS_EXTRACTED: {count}
        OUTPUT: projects/{project}/.design_extract_methods.md
)
```

### Agent 3: Extract-Ecosystems

```
Task(
    subagent_type: "general-purpose",
    description: "Extract ecosystem functions",
    run_in_background: true,
    prompt: |
        You are extracting relevant ecosystem functions and workflow templates
        for integration into a single-cell analysis plan.

        ## Your Inputs
        - **Ecosystem indexes**: discover available ecosystems by globbing
          `knowledge_base/ecosystems/*/`. For each ecosystem found, read all of:
          `capabilities.yaml`, `function_index.yaml`, `workflows.yaml`, `navigation.md`
          (skip any that are missing).
        - **Output file**: projects/{project}/.design_extract_ecosystems.md

        ## Your Task

        ### 1. Read all ecosystem files

        ### 2. Extract functions organized by analytical task

        Write to the output file with this structure. Use the actual ecosystem
        names you discovered, not the placeholder names. Group functions by
        analytical task — the task categories should reflect what's relevant to
        the project (which you'll see by reading the methods extraction file
        and project context).

        ```
        ---
        source: {comma-separated ecosystem names actually indexed}
        extracted_date: {today}
        ecosystems_indexed: {n}
        ---

        ## {Ecosystem Name} Functions by Task

        ### {Task Category — e.g., QC & Preprocessing, Embedding, Clustering,
        ### Differential Expression, Gene Scoring, Visualization, etc.}

        | Function | Full Name | Purpose | Key Parameters |
        |----------|-----------|---------|----------------|
        | {short_name} | {full.qualified.name} | {one-line purpose} | {key params} |
        (Include ALL relevant functions for this category, drawn from the
         ecosystem's function_index.yaml)

        {Repeat task-category subsections for each task type relevant to the project.}

        {Repeat the ecosystem block for each ecosystem indexed.}

        ## Cross-Ecosystem Equivalents (if multiple ecosystems indexed)

        For projects that mix Python and R (or compare across ecosystems),
        list per-task equivalents pulled from each ecosystem:

        | Task | {Ecosystem A} | {Ecosystem B} |
        |------|---------------|---------------|
        | {task} | {function from A} | {function from B} |

        ## Workflow Templates

        For each major workflow pattern relevant to the project (drawn from
        each ecosystem's workflows.yaml), reproduce a complete code skeleton.
        Common patterns to extract if present in the indexes:
        - Standard preprocessing pipeline
        - Embedding / batch integration
        - Clustering + annotation
        - Differential expression (whatever flavor — pseudobulk, mixed-effects, etc.)
        - Method-specific workflows for any joint-modality or specialized methods
          recommended in the fitness summary
        ```

        ### 3. Write the output file
        Write to: projects/{project}/.design_extract_ecosystems.md

        ### 4. Report completion
        EXTRACTION: ecosystems
        ECOSYSTEMS_EXTRACTED: {count}
        FUNCTIONS_MAPPED: {count}
        OUTPUT: projects/{project}/.design_extract_ecosystems.md
)
```

Spawn all 3 agents simultaneously (parallel) using Task with `run_in_background: true`.

---

## Step 4: Wait for Extraction Agents

Wait for all extraction agents to complete:

```
for each agent_id:
    TaskOutput(task_id: {agent_id}, block: true, timeout: 600000)
```

Verify all extract files were created. Apply the **Output Verification Protocol** to each:

```
Glob: projects/{project}/.design_extract_*.md
Bash: wc -l projects/{project}/.design_extract_*.md
```

Each extract file must:
1. Exist on disk
2. Be ≥ 2 KB (each extraction should produce substantial structured content)
3. Have YAML frontmatter
4. Contain expected top-level sections per agent type (e.g., `## Hypotheses` for bio extraction)

Background agents can complete without writing — they may have summarized in their output instead of calling Write. If any extract is missing or fails verification, surface the failure with the agent ID and output log path, and stop. Do not proceed to integration with partial extractions.

---

## Step 5: Spawn Integration Agent

Spawn a single integration agent that reads the compact extracts plus the fitness summary and project context, then produces the final analytical plan.

```
Task(
    subagent_type: "general-purpose",
    description: "Integrate analysis plan",
    run_in_background: true,
    prompt: |
        You are producing an integrated analysis plan that maps biology hypotheses
        to specific bioinformatics methods, functions, and code templates in an
        ordered analytical workflow.

        ## Your Inputs (read ALL)
        - **Project context**: {context_file_path}
        - **Fitness summary**: projects/{project}/bioinformatics/fitness_summary.md
        - **Biology extraction**: projects/{project}/.design_extract_bio.md
        - **Methods extraction**: projects/{project}/.design_extract_methods.md
        - **Ecosystems extraction**: projects/{project}/.design_extract_ecosystems.md
        - **Output file**: projects/{project}/analysis_plan.md

        ## Critical Principles
        1. Every hypothesis gets mapped to a specific method + function + code template
        2. The pipeline order follows fitness_summary.md's recommendation
        3. All code must be syntactically valid in the project's chosen language(s)
        4. Every method choice must cite rationale from both biology and bioinformatics sides
        5. Account for ALL constraints from the project context (non-functional
           markers, small panels, sample-size limits, enrichment effects, etc.)
        6. Gene names must use the standard symbol convention for the project's
           species (HUGO for human, MGI for mouse), applying any `gene_aliases`
           map in the project context

        ## Your Task

        ### 1. Read all inputs
        Read project context first. Then fitness_summary.md. Then all 3 extraction files.

        ### 2. Build the Integration Matrix
        For each hypothesis from the bio extraction:
        - Match its analytical_need(s) to the method-task matrix from methods extraction
        - Identify the primary method and secondary method
        - Pull the specific API functions from ecosystem extraction
        - Note which analysis phase it belongs to

        ### 3. Design the Ordered Pipeline
        Using the fitness_summary pipeline backbone, slot hypotheses into phases.
        A typical pipeline has phases like:
        - Data Processing (QC, normalization) — foundational, no hypotheses
        - Reduction / Embedding (dimensionality reduction, batch integration) — enables downstream
        - Classification / Annotation (cell type or state assignment)
        - Hypothesis Testing (compositional, differential expression, module scoring,
          multimodal concordance, variance decomposition — most hypotheses here)
        - Discovery (novel cross-paper hypotheses, conflict resolution, exploratory)

        Adapt phase names and ordering to what the fitness summary recommends.

        ### 4. Generate Code Templates
        For each phase, produce complete Python code blocks that:
        - Import the right libraries
        - Use real function names from ecosystem extraction
        - Include real gene lists from the bio extraction signatures
        - Set parameters appropriate for this project's constraints
        - Include inline comments explaining biological rationale

        ### 5. Build the Master Mapping Table
        Create a single table mapping ALL hypotheses to their analytical homes:
        | Rank | Hypothesis | Phase | Primary Method | Key Function | Code Section | Priority |

        ### 6. Write the output file

        Write to: projects/{project}/analysis_plan.md

        Use the schema below. The 5-phase framework (Data Processing → Joint
        Embedding/Reduction → Classification/Annotation → Hypothesis Testing →
        Discovery) is a reasonable default for many single-cell analyses but is
        not prescriptive — reorder, rename, add, or drop phases based on what
        the fitness summary's pipeline backbone and the project context require.
        Number the phases yourself based on the actual analysis order.

        ```markdown
        ---
        project: {project}
        context_file: {context_file}
        literature_synthesis: {literature_synthesis}
        fitness_summary: fitness_summary.md
        methods_integrated: {n}
        hypotheses_mapped: {n}
        analytical_phases: {n}
        designed_date: {today}
        ---

        # Integrated Analysis Plan: {Project Title}

        ## Overview
        {2-3 sentence summary: what data, what biology questions, what methods, what output}

        | Metric | Count |
        |--------|-------|
        | Biology hypotheses integrated | {n} |
        | Bioinformatics methods used | {n} |
        | Analytical phases | {n} |
        | Code templates provided | {n} |
        | Gene signatures applied | {n} |

        ---

        ## Critical Constraints (Biology + Bioinformatics)

        These constraints apply to ALL phases of this analysis plan.

        ### Biology Constraints (from literature synthesis)
        {Copy translation constraints from bio extraction — numbered list}

        ### Bioinformatics Constraints (from fitness assessment)
        {Copy cross-cutting concerns from methods extraction — numbered list}

        ### Combined Impact
        {2-3 sentences on how the biology constraints interact with the
         bioinformatics constraints to shape method choices for THIS project.
         Reference specific markers, sample-size limits, or technical issues
         from the project context.}

        ---

        ## Phase {N}: {Phase Name}

        > **Goal**: {one-line goal of this phase}
        > **Methods**: {primary methods used in this phase, from fitness summary}
        > **Hypotheses addressed**: {hypothesis ranks/IDs, or "None directly (foundational)"}

        ### {N}.{M} {Sub-step name}

        **Rationale**: {why this step, referencing both fitness summary and biology}

        **Project-specific considerations**:
        - {constraints from context.md that affect this step — e.g., broken markers,
           QC outliers, batch structure}

        ```{language}
        # Code template using REAL function names from ecosystem extraction
        # and REAL gene lists / parameter values from bio + methods extraction.
        # No placeholders inside code blocks — substitute project specifics.
        ```

        {Repeat sub-steps for each step in this phase. Each sub-step that
         addresses a hypothesis should explicitly cite the hypothesis rank/ID.}

        ---

        {Repeat phase blocks for each analytical phase, in execution order.
         Typical phase categories — adapt to the project:

         - DATA PROCESSING: QC, filtering, normalization (per modality)
         - REDUCTION/EMBEDDING: dimensionality reduction, batch integration
         - ANNOTATION: cell type / state classification
         - HYPOTHESIS TESTING: compositional, differential expression,
           differential abundance, module scoring, multimodal concordance,
           variance decomposition
         - DISCOVERY: novel cross-paper hypotheses, gap-filling, conflict
           resolution from the synthesis}

        ---

        ## Master Hypothesis-Method Mapping

        | Rank | Hypothesis | Type | Phase | Primary Method | Key Function | Priority Score |
        |------|-----------|------|-------|---------------|-------------|----------------|
        {ALL hypotheses from bio extraction, sorted by priority score,
         with their analytical phase and method assignments. Top hypotheses
         get detailed test plans inline in the relevant phase; lower-priority
         ones are listed here with brief method mapping only.}

        ---

        ## Execution Dependency Graph

        Show the actual phase/sub-step DAG for THIS project. Each node is a
        sub-step; arrows show what produces input for what. Example structure:

        ```
        Phase 1: {Phase 1 name}
            ├── 1.1 {sub-step} ──────┐
            ├── 1.2 {sub-step} ──────┤
            └── 1.3 {sub-step} ──────┤
                                     ▼
        Phase 2: {Phase 2 name}      │
            ├── 2.1 {sub-step} ◄─────┘
            └── 2.2 {sub-step}
                    │
                    ▼
        Phase 3: {Phase 3 name}
            ├── 3.1 {sub-step} ◄── Phase 1.2
            └── 3.2 {sub-step} ◄── Phase 2
                    │
                    ▼
        Phase 4: {Phase 4 name}
            └── ...
        ```

        ---

        ## Appendix A: Method Configuration Reference

        | Method | Language | Key Parameters | Project Setting | Rationale |
        |--------|----------|---------------|-----------------|-----------|
        {For each method used in the plan: the specific parameter values chosen
         and why, referencing both biology constraints and method documentation}

        ## Appendix B: Complete Gene Signature Dictionary

        ```{language}
        # Master gene signatures for {Project Title}
        # Source: Literature synthesis ({n} papers)
        # For use with: {scoring functions identified in ecosystem extraction}

        signatures = {
            # COMPLETE dictionary from bio extraction:
            # one entry per cell type / state, with core / supporting / extended tiers
        }
        ```

        ---
        *Generated by `/design-analysis` on {today}*
        *Biology source: {literature_synthesis}*
        *Bioinformatics source: fitness_summary.md + {n} method docs + {n} ecosystem indexes*
        ```

        ### 7. Report completion

        After writing, output:
        INTEGRATION_COMPLETE: true
        OUTPUT: projects/{project}/analysis_plan.md
        HYPOTHESES_MAPPED: {n}
        METHODS_USED: {n}
        CODE_TEMPLATES: {n}
        PHASES: 5
)
```

---

## Step 6: Wait for Integration Agent

```
TaskOutput(task_id: {integration_agent_id}, block: true, timeout: 600000)
```

---

## Step 7: Verify and Clean Up

### 7a: Verify output exists

```
Glob: projects/{project}/analysis_plan.md
```

If missing, report failure and stop.

### 7b: Spot-check quality

Read the first 100 lines of the output. Verify:
- YAML frontmatter is present and complete
- Overview section exists with metrics table
- Phase 1 headers exist
- At least one Python code block present

Also check that the file has substantial content:
```
Bash: wc -l projects/{project}/analysis_plan.md
```
(Should be 500+ lines for a proper plan)

### 7c: Clean up intermediate files

Remove the temporary extraction files:
```
Bash: rm projects/{project}/.design_extract_*.md
```

### 7d: Report to user

```
## Integrated Analysis Plan Complete

**Output**: projects/{project}/analysis_plan.md

### What's in it:
{Per-phase summary, one bullet per phase, naming the methods used and
 hypotheses addressed in each phase. Use the actual phase names from the
 generated analysis_plan.md.}

### Integration metrics:
- {n} biology hypotheses mapped to bioinformatics methods
- {n} methods with project-specific configurations
- {n} code-ready templates ({language})
- {n} gene signatures integrated into scoring workflows

### Top priority analysis:
{Brief description of the highest-priority hypothesis and which method tests it}
```

---

## Important Notes

1. **Do not read 0_synthesis_literature.md in the orchestrator**: It is too large. Let the Extract-Bio agent handle it. You only need the project context file and fitness_summary.md for orchestration decisions.

2. **fitness_summary.md is the method backbone**: The integration agent should use fitness_summary.md's pipeline recommendation as the scaffold, not invent a new pipeline ordering. The biology hypotheses are slotted into this scaffold.

3. **Code must be syntactically valid Python**: All code blocks must parse without errors. Use proper indentation, quoting, and dict/list syntax. Gene lists must be actual HUGO gene symbols from the literature synthesis, not placeholders.

4. **Gene name standardization**: Use the standard symbol convention for the project's species (HUGO for human, MGI for mouse). If the project context defines a `gene_aliases` map (e.g., for protein-name ↔ gene-symbol pairs common in the project's domain), apply it consistently. Protein names are acceptable in comments and prose; gene names in code must use the standard symbol.

5. **Method constraints must propagate**: Any cross-cutting concerns flagged in the fitness summary (e.g., "method X has Y limitation given the project's data") must appear in the analysis plan wherever those methods are recommended.

6. **Hypothesis priorities drive detail level**: Top 5–10 hypotheses get detailed code templates. Lower-priority hypotheses get method mappings with brief code outlines. Do not generate equal detail for all hypotheses.

7. **Cross-species hypotheses**: Hypotheses originating from papers in a different species than the project should be labeled as "cross-species validation" with explicit caveats in the test plan.

8. **The plan supersedes individual documents**: The analysis_plan.md is the authoritative workflow document. It integrates and supersedes the code templates in 0_synthesis_literature.md and the pipeline recommendation in fitness_summary.md.

---

## Output File Map

```
projects/{project}/
├── literature/
│   ├── *_intel.md                      # Individual paper intel
│   └── 0_synthesis_literature.md          # Biology synthesis (input)
├── bioinformatics/
│   ├── fitness_summary.md               # Method overview (input)
│   └── *_fitness_assessment.md          # Individual assessments
├── .design_extract_bio.md               # TEMPORARY (deleted)
├── .design_extract_methods.md           # TEMPORARY (deleted)
├── .design_extract_ecosystems.md        # TEMPORARY (deleted)
└── analysis_plan.md                     # THIS SKILL'S OUTPUT
```
