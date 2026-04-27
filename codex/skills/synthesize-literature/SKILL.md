---
name: synthesize-literature
description: "Synthesize cross-paper consensus knowledge and testable hypotheses from mined literature intel files"
---

# Codex Adapter

This adapter is generated from `skills/synthesize-literature/SKILL.md`. Edit the source Claude skill, then run `python3 scripts/sync_codex_skills.py` to refresh the Codex mirror.

Preserve the shared workflow contract: `knowledge_base/`, `projects/<name>/literature/`, `fitness_summary.md`, `analysis_plan.md`, audit files, and progress files remain the expected outputs.

## Claude-to-Codex Term Map

- `/skill-name` examples mean `$skill-name` or explicit plugin/skill invocation in Codex.
- `Task` / `TaskOutput` mean delegated/fresh-agent execution when available; otherwise run phases sequentially and verify files.
- `AskUserQuestion` means ask the user directly when required.
- `WebFetch` / `WebSearch` mean Codex web/search tools when available.

## Source Skill Instructions

# Synthesize Literature Skill

You are synthesizing **cross-paper intelligence** from individually mined research paper intel files. This is NOT about summarizing individual papers — that was already done by `/mine-paper`. You are **cross-referencing, deduplicating, voting, and generating novel insights** that emerge only when multiple papers are considered together.

## Critical Principles

1. **Consensus requires provenance**: Every claim must cite which papers support it. Never state something as consensus without listing the supporting papers by `[Author Year]`.
2. **Disagreements are features, not bugs**: When papers conflict (e.g., on whether a particular cell state exists, or on the direction of an effect), frame the conflict as a research opportunity. Do NOT silently pick one side.
3. **Prioritize testability**: Rank everything by whether the user's specific dataset can actually test it. A beautiful hypothesis is worthless if the data cannot address it.
4. **Consolidation means deduplication**: When merging gene signatures, use union/intersection logic with provenance tracking. Do NOT just concatenate lists.
5. **Mouse vs human**: Keep mouse-derived data (any paper where species = mouse) separate from human consensus. Label as "cross-species hypothesis" not "consensus."

---

## Usage Modes

### Mode 1: Standard Synthesis
```
/synthesize-literature projects/{project}/context.md --project={project}
```

### Mode 2: Refresh (full rebuild)
```
/synthesize-literature projects/{project}/context.md --project={project} --refresh
```
Re-runs full synthesis from ALL intel files. If `0_synthesis_literature.md` already exists, it will be overwritten. Use when you want a clean rebuild (e.g., after editing intel files or changing project context).

### Mode 3: Update (incremental integration)
```
/synthesize-literature projects/{project}/context.md --project={project} --update
```
Detects NEW intel files not yet included in the existing synthesis. Extracts only the new papers, then spawns a **merge agent** that integrates them into the existing `0_synthesis_literature.md`. Much faster than `--refresh` when adding a few papers to a large existing synthesis.

Requires an existing `0_synthesis_literature.md` — if none exists, falls back to standard (Mode 1).

### Optional: `--review=path` (supplementary literature review)
```
/synthesize-literature context.md --project=name --review=NewLiteratureSummary.md
/synthesize-literature context.md --project=name --update --review=NewLiteratureSummary.md
```
Passes an external literature review markdown as **supplementary context** to the synthesis/merge agent. Works with any mode. The review provides:
- Broader conceptual framing beyond the mined papers
- Additional references and mechanistic themes from the wider field
- Cross-study context that strengthens or challenges hypotheses

The review is used as supporting context, NOT as primary data. Claims from external reviews are cited as `[External Review]` and do not count toward consensus tiers (which require mined intel files with provenance).

---

## Architecture: Two-Phase Orchestrator

**Why two phases?** Intel files can total 200-400KB of markdown. Reading all of them plus producing a synthesis output exceeds a single context window. The solution: extraction agents compress each paper's intel into a compact structured format, then a synthesis agent cross-references the compressed data.

```
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (you, lightweight)                │
│  1. Read project context ONCE                                   │
│  2. Discover intel files, split into balanced batches            │
│  3. Spawn 3 extraction agents in parallel (background)          │
│  4. Wait for all agents                                         │
│  5. Spawn 1 synthesis agent                                     │
│  6. Verify output, clean up, report                             │
│  DO NOT read any intel files yourself — save context             │
└─────────────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Extract 1  │ │  Extract 2  │ │  Extract 3  │
│  ~4-5 papers│ │  ~4-5 papers│ │  ~4-5 papers│
│             │ │             │ │             │
│ Read intels │ │ Read intels │ │ Read intels │
│ Compress →  │ │ Compress →  │ │ Compress →  │
│ Structured  │ │ Structured  │ │ Structured  │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       ▼               ▼               ▼
  .extract_1.md   .extract_2.md   .extract_3.md
       │               │               │
       └───────────────┼───────────────┘
                       ▼
         ┌───────────────────────┐
         │   SYNTHESIS AGENT     │
         │  Read context + 3     │
         │  extract files        │
         │  Cross-reference      │
         │  → synthesis.md       │
         └───────────────────────┘
```

### Update Mode Architecture

When `--update` is specified, the orchestrator follows a lighter path: only new papers are extracted, and a **merge agent** integrates them into the existing synthesis rather than building from scratch.

```
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (you, lightweight)                │
│  1. Read existing synthesis YAML frontmatter                    │
│  2. Discover ALL intel files, diff against synthesized list     │
│  3. Report new papers found                                     │
│  4. Extract ONLY new papers (1-2 batches max)                   │
│  5. Wait for extraction                                         │
│  6. Spawn 1 MERGE agent (old synthesis + new extracts + review) │
│  7. Verify output, clean up, report delta                       │
│  DO NOT read any intel files yourself — save context             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  Extract (new    │
│  papers only)    │
│  1-2 batches     │
└────────┬─────────┘
         ▼
   .update_extract_1.md
         │
         ▼
┌──────────────────────────┐
│     MERGE AGENT          │
│  Read existing synth     │
│  + new extractions       │
│  + optional --review     │
│  → updated synthesis.md  │
└──────────────────────────┘
```

---

## Step 0: Parse Arguments

Extract from `$ARGUMENTS`:
- **context_file** (required): Path to the project context markdown
- **--project=folder** (required): Project folder name under `projects/`
- **--refresh** (optional): Force full re-synthesis even if output exists
- **--update** (optional): Incremental update — integrate only new papers into existing synthesis
- **--review=path** (optional): Path to an external literature review markdown for supplementary context

Validation:
- `--refresh` and `--update` are mutually exclusive. If both are specified, warn and use `--refresh`.
- If `--update` is specified but no `0_synthesis_literature.md` exists, warn and fall back to standard Mode 1.
- If `--review` path doesn't exist, warn and continue without it.
- If context_file or --project is missing, ask the user:

**"I need both a project context file and a --project flag. Example: `/synthesize-literature projects/{project}/context.md --project={project}`"**

---

## Step 1: Discover Intel Files

Find all intel files:

```
Glob: projects/{project}/literature/*_intel.md
```

Exclude files starting with `.` (hidden files like `.mining_progress.md`).

Count and report:

```
Found {n} intel files in projects/{project}/literature/
Papers: {short_name_1}, {short_name_2}, ...
```

If no intel files found: **"No intel files found. Run `/mine-paper --all` first to mine your papers."** and STOP.

### Standard/Refresh mode behavior:
If `0_synthesis_literature.md` already exists and neither `--refresh` nor `--update` was specified: ask the user if they want to overwrite.

### Update mode behavior (`--update`):
If `--update` was specified:

1. Read the YAML frontmatter of `projects/{project}/literature/0_synthesis_literature.md`
2. Extract the list of paper slugs already synthesized. The paper slugs are derived from intel filenames — e.g., `jaeger_diversity_group1_ilc_intel.md` → `jaeger_diversity_group1_ilc`. To match against the frontmatter's `papers_high`, `papers_moderate`, `papers_low` lists (which use `[Author Year]` format), read Appendix A of the existing synthesis to get the filename-to-citation mapping.
3. Diff the discovered intel files against the already-synthesized list.
4. Report:

```
## Update Mode: Paper Diff

Existing synthesis: {m} papers (synthesized {date})
Current intel files: {n} total
New papers to integrate: {k}
  - {new_paper_1}
  - {new_paper_2}
  ...
Already synthesized: {m} (will be preserved)
```

5. If no new papers found: **"All {n} intel files are already in the synthesis. Nothing to update. Use `--refresh` for a full rebuild."** and STOP.
6. Continue to Step 2 with only the NEW intel files marked for extraction.

---

## Step 2: Read Project Context

Read the context file and build the **Project Parameters Checklist**:

| Parameter | Extract |
|-----------|---------|
| Species | human/mouse/other |
| Tissue | PBMC/blood/tissue/etc. |
| Cell types of interest | {from context} |
| Technology | scRNA-seq / CITE-seq / flow / spatial / etc. |
| ADT panel | List exact antibodies, flag broken ones |
| Experimental design | Groups, timepoints, comparisons |
| Enrichment strategy | {sorting/enrichment method, what was enriched} |

You will pass the context_file path to sub-agents (they read it themselves).

---

## MODE BRANCH: Standard/Refresh vs Update

After Step 2, the flow diverges based on mode:
- **Standard or Refresh**: Continue to Step 3 (all papers) → Step 4-8
- **Update**: Jump to Step U1 (new papers only) → Step U2-U5

---

# STANDARD/REFRESH PATH (Steps 3-8)

## Step 3: Split Files into Balanced Batches

Get file sizes:
```
Bash: wc -c projects/{project}/literature/*_intel.md
```

Sort files by size descending. Assign to 3 batches using round-robin on sorted list (largest file → batch 1, second → batch 2, third → batch 3, fourth → batch 1, etc.). This ensures roughly balanced total sizes across batches.

If there are fewer than 6 intel files, use 2 batches instead. If fewer than 3, use 1 batch (single extraction agent).

Report the batch assignments:

```
Batch 1 ({n} papers, ~{size}KB): {paper_list}
Batch 2 ({n} papers, ~{size}KB): {paper_list}
Batch 3 ({n} papers, ~{size}KB): {paper_list}
```

---

## Step 4: Spawn Extraction Agents

For each batch, spawn a background Task agent. Use this exact prompt template, filling in the variables:

```
Task(
    subagent_type: "general-purpose",
    description: "Extract batch {batch_num}",
    run_in_background: true,
    prompt: |
        You are extracting compact structured data from literature intel files
        for a cross-paper synthesis.

        ## Your Inputs
        - **Project context file**: {context_file_path}
        - **Intel files to process** (read ALL of these):
          {file_path_1}
          {file_path_2}
          {file_path_3}
          ...
        - **Output file**: projects/{project}/literature/.synthesis_extract_{batch_num}.md

        ## Your Task

        ### 1. Read the project context
        Read {context_file_path} to understand:
        - Species, tissue, cell types of interest
        - ADT panel (and which are broken)
        - Experimental design (groups, comparisons)
        - Enrichment strategy

        ### 2. Read each intel file and extract compact structured data

        For EACH intel file, read the full file, then produce a compact extraction
        following this EXACT format. Be thorough but compact — include ALL markers,
        ALL gene signatures, ALL hypotheses. Do not summarize away specific gene names
        or numbers.

        #### Extraction Format (per paper):

        ```
        ## Paper: {paper_slug}
        - **Meta**: {first_author} {year}, {journal}, {relevance}, {species}, {tissue}, {technology}
        - **Key contribution**: {one sentence}

        ### Markers
        | Gene | Cell Type | Confidence | ADT? |
        |------|-----------|------------|------|
        | {gene} | {cell_type} | {High/Mod/Low} | {YES/NO/BROKEN} |
        (Include EVERY marker gene mentioned in the intel file's marker tables)

        ### Gene Signatures
        - {signature_name}: [{GENE1}, {GENE2}, {GENE3}, ...]
        (Include EVERY gene signature from the intel file's Python code blocks.
         Use the variable name as signature_name. List ALL genes.)

        ### Frequencies
        | Cell Type | Frequency | Population | Tissue |
        |-----------|----------|------------|--------|
        (Include ALL frequency data from the intel file)

        ### Gating Strategy
        {One-paragraph summary of the gating hierarchy recommended by this paper,
         noting which markers are in the ADT panel and which must use RNA}

        ### Hypotheses
        | ID | Prediction | Theme | Direction | Evidence |
        |----|-----------|-------|-----------|----------|
        | H1 | {specific prediction} | {aging/vaccination/composition/plasticity/metabolism/other} | {increase/decrease/stable/shift} | {Strong/Moderate/Weak} ({brief basis}) |
        (Include EVERY hypothesis from the intel file)

        ### Translation Gaps
        | Gap | Severity |
        |-----|----------|
        | {gap description} | {HIGH/MODERATE/LOW} |
        (Include ALL translation gaps)

        ### Key Caveats
        - {Important caveat 1}
        - {Important caveat 2}
        (2-5 bullet points of the most important caveats/warnings)
        ```

        ### 3. Write the output file

        Write ALL paper extractions to a single output file:

        ```
        mkdir -p projects/{project}/literature
        ```

        Write to: projects/{project}/literature/.synthesis_extract_{batch_num}.md

        Start the file with:
        ```
        ---
        batch: {batch_num}
        papers_extracted: {count}
        extracted_date: {today}
        ---
        ```

        Then include all paper extractions sequentially.

        ### 4. Report completion

        After writing, output:
        BATCH: {batch_num}
        PAPERS_EXTRACTED: {count}
        OUTPUT: projects/{project}/literature/.synthesis_extract_{batch_num}.md
)
```

Spawn all batch agents simultaneously (parallel).

---

## Step 5: Wait for Extraction Agents

Wait for all extraction agents to complete:

```
for each agent_id:
    TaskOutput(task_id: {agent_id}, block: true, timeout: 600000)
```

Verify all extract files were created. Apply the **Output Verification Protocol** to each:

```
Glob: projects/{project}/literature/.synthesis_extract_*.md
Bash: wc -l projects/{project}/literature/.synthesis_extract_*.md
```

Each extract file must:
1. Exist on disk
2. Be ≥ 2 KB (each batch should produce a substantial structured extract)
3. Have YAML frontmatter with `batch:` and `papers_extracted:` fields
4. Contain at least one `## Paper:` section per extracted paper

Background agents can complete without writing — they may have summarized in their output instead of calling Write. If any agent fails verification, report the agent ID and output log path to the user, and stop. Do not proceed to synthesis with partial extractions, since a missing batch will silently drop those papers from the synthesis.

---

## Step 6: Spawn Synthesis Agent

Spawn a single synthesis agent that reads the compact extracts and produces the final output.

```
Task(
    subagent_type: "general-purpose",
    description: "Synthesize literature",
    prompt: |
        You are producing a cross-paper literature synthesis from pre-extracted
        structured data. Your job is to cross-reference, deduplicate, find consensus,
        identify conflicts, and generate novel insights.

        ## Your Inputs
        - **Project context file**: {context_file_path}
        - **Extraction files** (read ALL):
          {extract_file_1_path}
          {extract_file_2_path}
          {extract_file_3_path}
        - **Output file**: projects/{project}/literature/0_synthesis_literature.md
        {IF --review was specified:}
        - **External literature review** (supplementary context): {review_file_path}
          Read this file for broader conceptual framing and additional
          mechanistic themes. Cite as [External Review] when it adds context
          beyond the mined papers. External review claims do NOT count toward
          consensus tiers — only mined intel files with provenance do.

        ## Critical Principles
        1. Every claim must cite supporting papers by [Author Year]
        2. Conflicting findings = research opportunities, not errors
        3. Rank everything by testability in THIS specific dataset
        4. Mouse-derived data stays separate from human consensus
        5. Gene names must be HUGO symbols

        ## Your Task

        ### 1. Read all inputs
        Read the project context file first. Then read ALL extraction files.

        Build a mental registry of all papers with their metadata.

        ### 2. Cross-Reference Markers (Consensus Marker Panel)

        For every marker gene that appears in ANY paper's marker table:
        - Count how many papers cite it
        - Note which cell type(s) it marks
        - Note if it is in the ADT panel (YES/NO/BROKEN)
        - Check for CONFLICTING cell type assignments across papers

        Tier markers:
        - **CORE** (3+ papers cite it for the same cell type): highest confidence
        - **SUPPORTING** (2 papers): moderate confidence
        - **EXPLORATORY** (1 paper only): use cautiously

        Produce a ranked marker table sorted by citation count.

        ### 3. Merge Gene Signatures (Consolidated Signatures)

        For each cell type / state mentioned in any paper's signatures:
        - Collect ALL gene signature lists from ALL papers for that cell type
        - Compute gene frequency: how many papers include each gene?
        - CORE genes: appear in 3+ paper signatures for that cell type
        - SUPPORTING genes: appear in 2 paper signatures
        - EXTENDED genes: appear in 1 paper signature

        Produce code-ready Python dictionaries:
        ```python
        signatures = {
            '{cell_type_1}': {
                'core': ['GENE1', 'GENE2', ...],      # [Paper1, Paper2, Paper3]
                'supporting': ['GENE3', ...],           # [Paper1, Paper2]
                'extended': ['GENE4', ...],             # [Paper1]
            },
            '{cell_type_2}': { ... },
            # one entry per cell type / state seen across papers
        }
        ```

        Include a comment after each gene list noting which papers contribute.

        ### 4. Synthesize Gating Strategy

        Read all papers' gating/classification strategies. Produce ONE recommended
        classification hierarchy that:
        - Uses ONLY markers available in the user's panel (per the project context)
        - Substitutes RNA expression for any broken / non-functional protein markers
          (use the project's gene_aliases map if provided)
        - Is supported by the maximum number of papers at each branch
        - Notes where papers disagree on a gate

        Present as both:
        a) ASCII flowchart with paper citations at each branch
        b) Code template (Python or R, matching the project's analysis language)

        ### 5. Aggregate Cell Frequencies

        For each cell type, collect all frequency estimates across papers.
        Produce a range table: min, max, and which papers provide each estimate.
        Annotate how the user's enrichment / sample preparation affects these
        expectations (frequencies in enriched / sorted samples are not directly
        comparable to whole-sample frequencies in the literature).

        ### 6. Unify Translation Constraints

        Collect all translation gaps across papers. Rank by how many papers
        flag each gap type. The most universal constraints go first.

        ### 7. Build Agreement/Disagreement Table

        Identify key biological topics where papers either:
        - AGREE (consensus) — list the agreeing papers
        - DISAGREE (conflict) — list both sides with supporting papers

        Format as a table with: Topic, Papers Agreeing, Papers Disagreeing, Status

        ### 8. Strengthen Multi-Paper Hypotheses

        Group all hypotheses by theme (aging, vaccination, composition, plasticity,
        metabolism, etc.). Within each theme:
        - Identify hypotheses supported by 2+ papers independently
        - Assign a consensus evidence strength
        - Rate testability (1-5) based on whether this dataset can address it:
          5 = directly testable with available data
          4 = testable with some assumptions
          3 = partially testable
          2 = weakly addressable
          1 = not testable with this data
        - Rate impact (1-5) based on novelty and field importance

        For the top 5 hypotheses, write detailed test plans including:
        - Specific genes/markers to examine
        - Expected outcomes for each direction
        - Statistical approach
        - Caveats and confounders

        ### 9. Identify Conflicting Findings

        Find where papers explicitly disagree. Frame each conflict as a
        research question with:
        - Side A: which papers, what they claim, evidence
        - Side B: which papers, what they claim, evidence
        - How this project can resolve it: specific markers, analysis approach

        ### 10. Gap-Filling Opportunities

        Identify capabilities UNIQUE to this dataset that no paper fully exploited.
        Examples of the kinds of things to look for:
        - Multimodal data when prior work used only one modality
        - Specific timepoints, conditions, or comparisons no prior study had
        - Specific markers (in the user's panel) that resolve a question
          previously addressed only with proxies
        - Within-study comparisons (same technology, same lab) where prior
          work had to compare across studies

        Pull the actual gap-filling opportunities from the project context's
        unique characteristics. Frame each as a "first-in-class" opportunity.

        ### 11. Novel Cross-Paper Hypotheses

        Generate hypotheses that emerge ONLY by combining findings from different
        papers — insights not stated in any individual paper. These arise from:
        - Combining marker / signature knowledge from one paper with phenotype
          data from another
        - Connecting pathway findings across papers
        - Species comparison (e.g., human vs mouse papers on the same biology)
        - Reconciling different technologies studying the same biology

        For each novel hypothesis, cite which papers are combined and explain
        the logical chain.

        ### 12. Master Hypothesis Ranking

        Create a single ranked table of ALL hypotheses (multi-paper, conflicting,
        gap-filling, novel). Score each:
        - Testability (1-5)
        - Impact (1-5)
        - Evidence weight = number_supporting_papers / total_papers
        - Priority Score = Testability × Impact × Evidence weight × 100

        Sort by Priority Score descending.

        ### 13. Consolidated Code Resources

        Produce a single Python code section containing:
        a) Master gene signature dictionary (all signatures, all tiers)
        b) Recommended classification pipeline (complete, copy-pasteable)
        c) Hypothesis testing code templates for top 3 hypotheses

        All code must be syntactically valid Python.

        ### 14. Write the output file

        **CRITICAL: The output file is too large for a single Write call (will exceed
        output token limits). You MUST write it in sequential chunks:**

        **Step 14a**: Write CHUNK 1 to `projects/{project}/literature/.synthesis_chunk_1.md`
        Contents: YAML frontmatter + Overview + Part 1 (Sections 1.1 through 1.7)

        **Step 14b**: Write CHUNK 2 to `projects/{project}/literature/.synthesis_chunk_2.md`
        Contents: Part 2 (Sections 2.1 through 2.5, including all detailed test plans)

        **Step 14c**: Write CHUNK 3 to `projects/{project}/literature/.synthesis_chunk_3.md`
        Contents: Part 3 (Code Resources 3.1-3.3) + Appendix A + Appendix B + footer

        **Step 14d**: Concatenate chunks into final file:
        ```
        Bash: cat projects/{project}/literature/.synthesis_chunk_1.md projects/{project}/literature/.synthesis_chunk_2.md projects/{project}/literature/.synthesis_chunk_3.md > projects/{project}/literature/0_synthesis_literature.md
        ```

        **Step 14e**: Clean up chunk files:
        ```
        Bash: rm projects/{project}/literature/.synthesis_chunk_*.md
        ```

        Use this overall structure across the chunks:

        **CHUNK 1:**
        ```markdown
        ---
        project: {project}
        context_file: {context_file}
        papers_synthesized: {n}
        papers_high: [{list}]
        papers_moderate: [{list}]
        papers_low: [{list}]
        synthesized_date: {today}
        consensus_markers: {n}
        consolidated_signatures: {n}
        total_hypotheses: {n}
        ---

        # Literature Synthesis: {Project Title}

        ## Overview
        {2-3 sentence summary}

        | Metric | Count |
        |--------|-------|
        (metrics table)

        ---

        ## Part 1: Consensus Knowledge

        ### 1.1 Universal Translation Constraints
        ### 1.2 Consensus Cell Type Marker Panel
        ### 1.3 ADT Panel Utility Summary
        ### 1.4 Consensus Gating Strategy
        ### 1.5 Consolidated Gene Signatures
        ### 1.6 Expected Cell Frequencies
        ### 1.7 Agreement vs Disagreement Summary
        ```

        **CHUNK 2:**
        ```markdown

        ---

        ## Part 2: Research Questions & Hypotheses

        ### 2.1 Multi-Paper Hypotheses (High Confidence)
        #### Top 5 Detailed Test Plans
        ### 2.2 Conflicting Findings (Research Opportunities)
        ### 2.3 Gap-Filling Opportunities
        ### 2.4 Novel Cross-Paper Hypotheses
        ### 2.5 Master Hypothesis Ranking
        ```

        **CHUNK 3:**
        ```markdown

        ---

        ## Part 3: Consolidated Code Resources

        ### 3.1 Master Gene Signature Dictionary
        ### 3.2 Recommended Classification Pipeline
        ### 3.3 Hypothesis Testing Templates

        ---

        ## Appendix A: Paper-by-Paper Summary
        ## Appendix B: Gene Provenance Table

        ---
        *Generated by `/synthesize-literature` on {date}*
        ```

        ### 15. Report completion

        After writing, output:
        SYNTHESIS_COMPLETE: true
        OUTPUT: projects/{project}/literature/0_synthesis_literature.md
        PAPERS_SYNTHESIZED: {n}
        CONSENSUS_MARKERS: {n}
        SIGNATURES: {n}
        HYPOTHESES: {n}
)
```

---

## Step 7: Wait for Synthesis Agent

```
TaskOutput(task_id: {synthesis_agent_id}, block: true, timeout: 600000)
```

---

## Step 8: Verify and Clean Up

### 8a: Verify output exists

```
Glob: projects/{project}/literature/0_synthesis_literature.md
```

If missing, report failure and stop.

### 8b: Spot-check quality

Read the first 100 lines of the synthesis output. Verify:
- YAML frontmatter is present and complete
- Part 1 headers exist
- At least one table has data
- Python code blocks have `signatures = {` structure

### 8c: Clean up intermediate files

Remove the temporary extraction and chunk files:

```
Bash: rm -f projects/{project}/literature/.synthesis_extract_*.md projects/{project}/literature/.synthesis_chunk_*.md
```

### 8d: Report to user

```
## Literature Synthesis Complete

**Papers synthesized**: {n} ({m} HIGH, {k} MODERATE, {j} LOW)
**Output**: projects/{project}/literature/0_synthesis_literature.md

### What's in it:
- Part 1: Consensus knowledge (markers, signatures, gating, frequencies)
- Part 2: Research questions & hypotheses (ranked by testability × impact)
- Part 3: Code-ready resources (gene signatures dict, classification pipeline)

Top priority hypothesis: {brief description}
```

---

# UPDATE PATH (Steps U1-U5)

These steps are followed ONLY when `--update` is specified. They replace Steps 3-8.

## Step U1: Extract New Papers Only

### U1a: Get file sizes of NEW intel files only

```
Bash: wc -c {new_file_1} {new_file_2} ...
```

### U1b: Batch the new files

Use the same batching logic as Step 3, but ONLY for the new files:
- Fewer than 3 new files → 1 batch (single extraction agent)
- 3-5 new files → 2 batches
- 6+ new files → 3 batches

Report:

```
Extracting {k} new papers in {b} batch(es):
Batch 1 ({n} papers, ~{size}KB): {paper_list}
```

### U1c: Spawn extraction agents

Use the **same extraction agent prompt** as Step 4, but:
- Only process the NEW intel files
- Write to `.update_extract_{batch_num}.md` instead of `.synthesis_extract_{batch_num}.md`

Spawn all batch agents simultaneously (parallel).

---

## Step U2: Wait for Extraction Agents

Same as Step 5, but verify `.update_extract_*.md` files.

---

## Step U3: Back Up Existing Synthesis

Before merging, create a timestamped backup:

```
Bash: cp projects/{project}/literature/0_synthesis_literature.md projects/{project}/literature/.0_synthesis_literature_pre_update.md
```

Report:

```
Backed up existing synthesis → .0_synthesis_literature_pre_update.md
```

---

## Step U4: Spawn Merge Agent

Spawn a single merge agent that reads the existing synthesis, the new extractions, and optionally an external review, then produces an updated synthesis.

```
Task(
    subagent_type: "general-purpose",
    description: "Merge new papers into synthesis",
    prompt: |
        You are performing an **incremental update** of an existing literature
        synthesis. New papers have been mined and extracted. Your job is to
        integrate their findings into the existing synthesis document while
        preserving all existing content and maintaining internal consistency.

        ## Your Inputs
        - **Project context file**: {context_file_path}
        - **Existing synthesis** (read FIRST — this is your base document):
          projects/{project}/literature/0_synthesis_literature.md
        - **New paper extraction files** (read ALL):
          {update_extract_file_1_path}
          {update_extract_file_2_path}
          ...
        - **Output file**: projects/{project}/literature/0_synthesis_literature.md
          (overwrites existing — backup was already made)
        {IF --review was specified:}
        - **External literature review** (supplementary context): {review_file_path}
          Read this file for broader conceptual framing and additional
          mechanistic themes from the wider field. Cite as [External Review]
          when it adds context beyond the mined papers. External review claims
          do NOT count toward consensus tiers.

        ## Critical Principles
        1. **PRESERVE first, integrate second**: The existing synthesis represents
           validated cross-paper analysis. Do NOT lose, rewrite, or weaken any
           existing content. You are ADDING to it.
        2. Every claim must cite supporting papers by [Author Year]
        3. New papers may STRENGTHEN existing findings (increase citation counts,
           promote tier), ADD new findings, or CONFLICT with existing ones
        4. Mouse-derived data stays separate from human consensus
        5. Gene names must be HUGO symbols
        6. External review content is supplementary context, not primary data

        ## Your Task

        ### 1. Read all inputs

        Read the project context file, then the FULL existing synthesis, then
        ALL new extraction files, then the external review (if provided).

        Build a registry of:
        - Existing papers (from Appendix A of the synthesis)
        - New papers (from extractions)
        - Total paper count (old + new)

        ### 2. Update YAML Frontmatter

        Update the frontmatter with:
        - `papers_synthesized`: old + new count
        - `papers_high/moderate/low`: add new papers to appropriate lists
        - `synthesized_date`: today's date
        - `updated_from`: previous paper count (for audit trail)
        - `update_added`: [list of new paper citations]
        - Recalculate `consensus_markers`, `consolidated_signatures`, `total_hypotheses`

        ### 3. Update Translation Constraints (Section 1.1)

        Check new papers for translation constraints not already in the table.
        - If a new constraint is novel: ADD a new row
        - If a new paper confirms an existing constraint: add it to "Papers Confirming"
        - Update constraint numbering

        ### 4. Update Consensus Marker Panel (Section 1.2)

        For every marker in the new papers:
        - If marker ALREADY exists in the table: update the citation count
          (e.g., "9/13" becomes "10/20" if the marker is in 1 new paper and
          total is now 20). Check if this promotes its tier (e.g., SUPPORTING → CORE).
        - If marker is NEW: add a row with the appropriate tier based on how
          many new papers cite it (usually EXPLORATORY for 1 paper)
        - Update the "Papers (n/{total})" column header to reflect new total

        ### 5. Update ADT Panel Utility (Section 1.3)

        Add any new insights about ADT markers from the new papers.

        ### 6. Update Gating Strategy (Section 1.4)

        If new papers provide gating insights (especially for cell types
        poorly covered in the original synthesis), update the ASCII flowchart
        and Python code. Add [Author Year] citations at relevant branches.

        ### 7. Update Gene Signatures (Section 1.5)

        For each cell type in the new papers' signatures:
        - Merge new genes into existing signature dictionaries
        - Recalculate tiers: a gene that was EXTENDED (1 paper) may become
          SUPPORTING (2 papers) if a new paper also includes it
        - Add provenance comments
        - Ensure Python code remains syntactically valid

        ### 8. Update Cell Frequencies (Section 1.6)

        Add new frequency data. Update min/max ranges if new papers extend them.

        ### 9. Update Agreement/Disagreement (Section 1.7)

        - If new papers agree with existing consensus: add them to "Papers Agreeing"
        - If new papers disagree: add to "Papers Disagreeing" and update status
        - If new papers introduce entirely new topics: add new rows

        ### 10. Update Multi-Paper Hypotheses (Section 2.1)

        - Check if new papers provide additional support for existing hypotheses
          → update evidence strength and paper counts
        - Add new hypotheses from the new papers that are supported by 2+ papers
          (counting both old and new papers)
        - Update or add detailed test plans if new papers significantly
          strengthen a hypothesis

        ### 11. Update Conflicting Findings (Section 2.2)

        - If new papers resolve existing conflicts: note the resolution
        - If new papers add to existing conflicts: update both sides
        - If new papers introduce new conflicts: add new rows

        ### 12. Update Gap-Filling Opportunities (Section 2.3)

        - If new papers partially address an existing gap: note this
        - If new papers reveal new gap-filling opportunities: add rows

        ### 13. Update Novel Cross-Paper Hypotheses (Section 2.4)

        Generate NEW cross-paper hypotheses that emerge from combining
        old synthesis findings with new paper findings. These are the most
        valuable outputs of an incremental update — insights that only
        emerge when the new papers are considered alongside the existing corpus.

        Also consider hypotheses that combine new papers with each other.

        {IF --review was specified:}
        Use the external review to identify mechanistic themes or conceptual
        frameworks that connect old and new papers in ways not captured by
        the individual intel files. For example, if the review introduces a
        framework or concept that connects findings from multiple papers,
        generate hypotheses linking that concept to specific markers/genes
        from the mined intel. Cite as [External Review] + [Author Year] for
        the specific data.

        ### 14. Recompute Master Hypothesis Ranking (Section 2.5)

        Recompute ALL scores using the updated formula:
        - Priority Score = Testability × Impact × (n_supporting_papers / total_papers) × 100
        - The total_papers denominator is now larger, which will naturally
          deflate scores for hypotheses that didn't gain new support
        - Re-sort by Priority Score descending
        - This re-ranking is important: it reveals which hypotheses gained
          or lost relative priority

        ### 15. Update Code Resources (Part 3)

        - Update the master gene signature dictionary with new genes/tiers
        - Update classification pipeline if new gating info was added
        - Update or add hypothesis testing templates for new top-ranked hypotheses
        - All code must be syntactically valid Python

        ### 16. Update Appendices

        - Appendix A: Add new papers to the paper-by-paper summary table
        - Appendix B: Add new genes to the provenance table, update existing entries

        ### 17. Add Update Log

        At the very end of the document (before the generation timestamp),
        add an update log section:

        ```markdown
        ## Update Log

        | Date | Action | Papers Added | Papers Total |
        |------|--------|-------------|-------------|
        | {original_date} | Initial synthesis | {original_count} | {original_count} |
        | {today} | Incremental update | {new_count} | {total_count} |
        ```

        {IF --review was specified:}
        Add a row noting the external review:
        ```
        | {today} | External review integrated | — | {total_count} |
        ```

        ### 18. Write the output file

        **CRITICAL: The output file is too large for a single Write call (will exceed
        output token limits). You MUST write it in sequential chunks:**

        **Step 18a**: Write CHUNK 1 to `projects/{project}/literature/.merge_chunk_1.md`
        Contents: YAML frontmatter + Overview + Part 1 (Sections 1.1 through 1.7)

        **Step 18b**: Write CHUNK 2 to `projects/{project}/literature/.merge_chunk_2.md`
        Contents: Part 2 (Sections 2.1 through 2.5, including all detailed test plans)

        **Step 18c**: Write CHUNK 3 to `projects/{project}/literature/.merge_chunk_3.md`
        Contents: Part 3 (Code Resources 3.1-3.3) + Appendix A + Appendix B + Update Log + footer

        **Step 18d**: Concatenate chunks into final file:
        ```
        Bash: cat projects/{project}/literature/.merge_chunk_1.md projects/{project}/literature/.merge_chunk_2.md projects/{project}/literature/.merge_chunk_3.md > projects/{project}/literature/0_synthesis_literature.md
        ```

        **Step 18e**: Clean up chunk files:
        ```
        Bash: rm projects/{project}/literature/.merge_chunk_*.md
        ```

        The output must follow the EXACT SAME structure as the existing
        synthesis. Do NOT change section numbering or headers. Add content
        within existing sections.

        Update the generation timestamp at the end of CHUNK 3:
        ```
        *Updated by `/synthesize-literature --update` on {date} (added {k} papers)*
        ```

        ### 19. Report completion

        After writing, output:
        MERGE_COMPLETE: true
        OUTPUT: projects/{project}/literature/0_synthesis_literature.md
        PAPERS_PREVIOUSLY: {m}
        PAPERS_ADDED: {k}
        PAPERS_TOTAL: {m+k}
        NEW_MARKERS: {n} (markers added or promoted)
        NEW_HYPOTHESES: {n} (hypotheses added)
        REVIEW_INTEGRATED: {yes/no}
)
```

---

## Step U5: Verify and Clean Up

### U5a: Verify output exists

```
Glob: projects/{project}/literature/0_synthesis_literature.md
```

If missing, report failure. The backup at `.0_synthesis_literature_pre_update.md` can be restored.

### U5b: Spot-check quality

Read the first 50 lines + last 30 lines of the updated synthesis. Verify:
- YAML frontmatter has updated `papers_synthesized` count
- `update_added` field is present in frontmatter
- Update Log section exists at the end
- Paper count in Overview table matches frontmatter

### U5c: Validate no content loss

Compare line counts:
```
Bash: wc -l projects/{project}/literature/0_synthesis_literature.md projects/{project}/literature/.0_synthesis_literature_pre_update.md
```

The updated file should be LONGER than the original (new content was added). If it's significantly shorter (>20% fewer lines), warn the user:

**"Warning: Updated synthesis is {n}% shorter than the original. This may indicate content loss. The backup is at `.0_synthesis_literature_pre_update.md`. Please review."**

### U5d: Clean up intermediate files

Remove the temporary extraction and chunk files:

```
Bash: rm -f projects/{project}/literature/.update_extract_*.md projects/{project}/literature/.merge_chunk_*.md
```

Do NOT delete the backup file — keep `.0_synthesis_literature_pre_update.md` for the user to review.

### U5e: Report to user

```
## Literature Synthesis Updated

**Previous**: {m} papers (synthesized {original_date})
**Added**: {k} new papers
**Total**: {m+k} papers

### New papers integrated:
- {paper_1}: {relevance} — {key_contribution}
- {paper_2}: {relevance} — {key_contribution}
...

### What changed:
- Markers: {n} added, {p} promoted in tier
- Gene signatures: {n} cell types updated
- Hypotheses: {n} new, {p} strengthened
- Novel cross-paper hypotheses: {n} new (combining old + new papers)

### Top NEW hypothesis:
{brief description of highest-ranked new hypothesis}

**Output**: projects/{project}/literature/0_synthesis_literature.md
**Backup**: projects/{project}/literature/.0_synthesis_literature_pre_update.md
{IF --review:}
**External review integrated**: {review_filename}
```

---

## Important Notes

0. **Output token limit management**: The final synthesis document can exceed 1000 lines of markdown. A single Write call will exceed the 32000 output token limit. Both synthesis agents (Step 6) and merge agents (Step U4) MUST write the document in sequential chunks using numbered temporary files, then concatenate. See the writing instructions within each agent prompt for details.

1. **Gene name standardization**: Use the standard symbol convention for the project's species (HUGO for human, MGI for mouse). Protein names are acceptable in prose; code must use gene symbols. If the project context defines a `gene_aliases` map (for protein-name ↔ gene-symbol pairs common in the project's domain), apply it consistently. Treat that map as the source of truth rather than hardcoding aliases here.

2. **Cross-species paper handling**: Papers in a different species than the project should have their gene signatures converted to orthologs in the project's species (often the same symbol) and labeled as "cross-species evidence." Cross-species findings should NOT count toward same-species consensus tiers, but CAN contribute to hypothesis generation.

3. **Python code validity**: All Python code blocks must be syntactically valid. The synthesis agent should use proper dict/list syntax, proper quoting, and proper indentation.

4. **Do not manufacture consensus**: If only one paper supports a finding, say "single-paper finding [Author Year]" not "the literature suggests." Three papers saying the same thing is consensus. One paper is a single observation.

5. **The synthesis supersedes `literature_summary.md`**: The older `literature_summary.md` (generated by mine-paper batch mode) is a simple catalog. This synthesis is the authoritative cross-paper analysis document.

---

## Output File Map

```
projects/{project}/literature/
├── {paper1}_intel.md                    # Individual paper intel (from /mine-paper)
├── {paper2}_intel.md
├── ...
├── .mining_progress.md                  # Mining progress tracker
├── .synthesis_extract_1.md              # TEMPORARY (deleted after standard/refresh synthesis)
├── .synthesis_extract_2.md              # TEMPORARY
├── .synthesis_extract_3.md              # TEMPORARY
├── .update_extract_1.md                 # TEMPORARY (deleted after --update merge)
├── .update_extract_2.md                 # TEMPORARY
├── .0_synthesis_literature_pre_update.md  # Backup before --update (KEPT for user review)
├── literature_summary.md                # Simple catalog (from /mine-paper batch)
└── 0_synthesis_literature.md              # THIS SKILL'S OUTPUT
```
