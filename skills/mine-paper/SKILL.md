---
name: mine-paper
description: Extract actionable intelligence and testable hypotheses from a biology/research paper for a specific project context
argument-hint: [paper.pdf] [context-file.md] [--project=folder] | --all [context-file.md] [--project=folder] | --papers=a.pdf,b.pdf [context-file.md] [--project=folder]
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Bash(mkdir *), Task, TaskOutput
---

# Mine Paper Skill

You are extracting **actionable intelligence** from biology/research papers for a specific experimental project. This is NOT about understanding a bioinformatics method — it is about mining a research paper for concrete information (gene names, marker panels, cell frequencies, gating strategies, expected biology) that can be directly applied to the user's analysis or generate testable hypotheses from their data.

## Critical Principles

1. **Specificity over summary**: Extract gene names, protein markers, exact frequencies, specific thresholds — not vague statements like "the authors found differences between subsets."
2. **Honesty over completeness**: If a paper is not useful for the project, say so immediately and stop. Do not manufacture relevance.
3. **Translation gaps are first-class**: Every extracted item must be annotated with how well it translates to the user's specific experimental context (species, tissue, technology, cell enrichment).
4. **Actionable means actionable**: "Directly actionable" items must be things the user can type into code TODAY — gene lists for scoring functions, marker combinations for annotation, gating thresholds. If you cannot provide that level of specificity, it belongs in "hypothesis-generating" instead.

---

## Usage Modes

### Mode 1: Single Paper
```
/mine-paper "<paper.pdf>" projects/{project}/context.md
```

### Mode 2: Single Paper with Project Flag
```
/mine-paper "<paper.pdf>" context.md --project={project}
```

### Mode 3: All Papers in Directory (Parallel)
```
/mine-paper --all projects/{project}/context.md --project={project}
```

### Mode 4: Specific Papers (Parallel)
```
/mine-paper --papers="paper1.pdf,paper2.pdf,paper3.pdf" context.md --project={project}
```

### Mode 5: All Papers with Custom Directory
```
/mine-paper --all context.md --project={project} --dir=papers/<subset>/
```

### Force Re-mining
```
/mine-paper --all context.md --project={project} --force
```

---

## Architecture Overview

### Single Paper Mode
Runs in the current context window. Follow Steps 0-9 directly.

### Batch/Parallel Mode (--all or --papers)

**Context management is critical.** A single research paper PDF can consume 50-100k tokens. With 13 papers, that exceeds any single context window. The orchestrator pattern isolates each paper in its own background agent.

```
┌──────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (lightweight)                         │
│  - Reads project context ONCE (for summary generation later)          │
│  - Discovers papers to process                                        │
│  - Spawns mining agents in parallel (background)                      │
│  - Tracks progress in .mining_progress.md                             │
│  - Waits for all agents                                               │
│  - Generates cross-paper literature_summary.md                        │
│  - Does NOT read any PDFs itself (saves context for orchestration)    │
│  Estimated orchestrator context: ~20-30k tokens                       │
└──────────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Agent 1    │ │  Agent 2    │ │  Agent 3    │ │  Agent N    │
│  (paper 1)  │ │  (paper 2)  │ │  (paper 3)  │ │  (paper N)  │
│             │ │             │ │             │ │             │
│ Fresh ctx   │ │ Fresh ctx   │ │ Fresh ctx   │ │ Fresh ctx   │
│ (~200k tok) │ │ (~200k tok) │ │ (~200k tok) │ │ (~200k tok) │
│             │ │             │ │             │ │             │
│ 1. Read ctx │ │ 1. Read ctx │ │ 1. Read ctx │ │ 1. Read ctx │
│ 2. Screen   │ │ 2. Screen   │ │ 2. Screen   │ │ 2. Screen   │
│ 3. Deep read│ │ 3. NOT USED │ │ 3. Deep read│ │ 3. Deep read│
│ 4. Extract  │ │    → STOP   │ │ 4. Extract  │ │ 4. Extract  │
│ 5. Write    │ │             │ │ 5. Write    │ │ 5. Write    │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │               │
       ▼               ▼               ▼               ▼
  paper1_intel.md  paper2_intel.md  paper3_intel.md  paperN_intel.md
                                                        │
                                         ┌──────────────┘
                                         ▼
                                 literature_summary.md
```

---

## Workflow: Single Paper Mode

### Step 0: Parse Arguments

Extract from `$ARGUMENTS`:
- **Paper PDF path** (required unless `--all`): Path to the PDF
- **Context file path** (required): Markdown file describing the user's project
- **--project=folder** (optional): Project subfolder name under `projects/`

If no paper specified and not in batch mode, list available PDFs:

```bash
ls *.pdf
```

Then ask the user which paper to mine.

If no context file specified, ask:

**"I need your project context file to assess relevance. Please provide the path to your project context markdown file."**

### Step 1: Load Project Context

Read the project context file and extract these critical parameters. You will use these as filters throughout the evaluation.

#### Project Parameters Checklist

Build this checklist mentally — you will reference it at every extraction step:

| Parameter | What to Extract | Why It Matters |
|-----------|----------------|----------------|
| **Species** | human/mouse/other | Species mismatch = translation gap |
| **Tissue/compartment** | PBMC/blood/tissue-resident/etc. | Tissue-resident vs circulating biology differs |
| **Cell types of interest** | {from context} | Paper must discuss these cells |
| **Technology** | scRNA-seq / CITE-seq / flow / bulk / spatial / etc. | Determines which data types are extractable |
| **Available RNA measurements** | Full transcriptome? Targeted? | Determines if gene markers are detectable |
| **ADT panel (exact antibodies)** | List of surface protein antibodies | Paper markers must be in this panel to be directly usable as protein |
| **Broken/non-functional reagents** | Any failed antibodies | Must flag every time these markers appear |
| **Experimental design** | Conditions, timepoints, comparisons | Determines which findings are testable |
| **Enrichment/sorting strategy** | What was enriched, what was depleted | Affects expected cell composition |
| **Known technical issues** | Low depth, high dropout, etc. | Constrains what is usable |
| **Flow gates (reference)** | Ground truth classification criteria | Benchmark for annotation strategies |

### Step 2: First-Pass Relevance Screen

Read the first 3-5 pages of the PDF (abstract, introduction, beginning of methods):

```
Read(file_path: "{paper_path}", pages: "1-5")
```

Apply the **Relevance Decision Tree**:

```
Q1: Does this paper study any of the user's cell types of interest?
    NO  → NOT USEFUL (stop here)
    YES → continue

Q2: Is the species the same as the user's project?
    YES → strong match, continue
    NO  → Is it a closely translatable model (e.g., mouse→human for conserved pathways)?
          YES → continue with TRANSLATION_GAP flag
          NO  → NOT USEFUL (stop here)

Q3: Is the tissue/compartment relevant?
    SAME tissue → strong match
    RELATED tissue (e.g., secondary lymphoid for blood study, when same lineage) → continue with TISSUE_GAP flag
    UNRELATED tissue (e.g., tissue-resident cells for circulating study) → LOW RELEVANCE at best

Q4: Does the paper contain extractable molecular data?
    (gene lists, protein markers, flow panels, scRNA-seq clusters, signatures)
    YES → continue
    NO (purely clinical/epidemiological/review without original data) → LOW RELEVANCE

Q5: How many of the paper's key markers/measurements are detectable in the user's data?
    MOST → HIGH or MODERATE RELEVANCE
    SOME → MODERATE RELEVANCE
    FEW/NONE → LOW RELEVANCE
```

#### Assign Relevance Verdict

| Verdict | Criteria | Action |
|---------|----------|--------|
| **HIGH RELEVANCE** | Same species + same/similar tissue + same cell types + extractable molecular data + most markers detectable | Full extraction (Steps 3-8) |
| **MODERATE RELEVANCE** | 1-2 translation gaps (species OR tissue OR technology) but core cell biology overlaps | Full extraction with Translation Gap Assessment |
| **LOW RELEVANCE** | Multiple translation gaps, but some hypothesis-generating content | Abbreviated extraction (hypotheses only, skip "directly actionable" section) |
| **NOT USEFUL** | No meaningful overlap with project | Write minimal file and STOP |

**If NOT USEFUL**, create a minimal output file and stop:

```markdown
---
paper: "{paper_filename}"
project: {project}
verdict: NOT USEFUL
assessed: {date}
---

# {Paper Title}

**Verdict: NOT USEFUL for this project.**

**Reason**: {2-3 sentences explaining why. Cite the specific gaps — species mismatch,
unrelated tissue compartment, incompatible technology, no extractable molecular data, etc.
Be concrete about which aspects of the user's project this paper cannot address.}
```

Save to `projects/{project}/literature/{paper_slug}_intel.md` and STOP. Do not proceed to Step 3.

### Step 3: Deep Read (Full Paper)

For HIGH, MODERATE, or LOW relevance papers, read the full paper systematically.

**For large PDFs (>15 pages)**, read in targeted passes:

#### 3a: Methods Section
Read the methods to understand:
- Cell isolation and sorting strategy
- Technology platform (flow panel, scRNA-seq platform, bulk RNA-seq)
- Marker panel / antibodies used
- Sample sizes, conditions, timepoints
- Gating strategies (critical for any panel-based classification)
- Computational methods (clustering, DE analysis)

```
Read(file_path: "{paper_path}", pages: "{methods_pages}")
```

#### 3b: Results Section
Read results section by section, extracting:
- **Marker genes/proteins** mentioned for each cell type
- **Gene signatures** (especially if provided as lists or supplementary tables)
- **Cell frequencies/proportions** with specific numbers
- **Differential expression results** with gene names
- **Flow cytometry gating hierarchies**
- **Pathway analysis results** with pathway names
- **Specific numerical thresholds** used for classification

```
Read(file_path: "{paper_path}", pages: "{results_pages}")
```

#### 3c: Figures and Tables
Figures often contain the most extractable data:
- Heatmaps with gene lists on axes
- Flow cytometry dot plots with gating boundaries
- Volcano plots with labeled genes
- Tables of differentially expressed genes
- UMAP/tSNE plots with cluster annotations and markers

```
Read(file_path: "{paper_path}", pages: "{figure_pages}")
```

#### 3d: Supplementary Data (if embedded in PDF)
Check later pages for supplementary tables — these are gold mines:
- Full DE gene lists
- Complete marker panels
- Extended flow cytometry data
- Gene signature definitions

```
Read(file_path: "{paper_path}", pages: "{supplement_pages}")
```

### Step 4: Extract Directly Actionable Intelligence

**Skip this section entirely for LOW RELEVANCE papers — go to Step 5.**

For each item extracted, apply the **Actionability Filter**:

#### Actionability Filter

An item is "directly actionable" ONLY if ALL of these are true:

1. **Measurable**: The gene/protein can be detected in the user's data (RNA for genes, ADT for surface proteins in the user's panel)
2. **Specific**: It is a concrete item (gene name, protein, threshold), not a vague concept
3. **Applicable**: The biological context is close enough that the finding should hold (same species, compatible tissue)
4. **Implementable**: The user could write code using this information today

Items that fail any criterion go to "Hypothesis-Generating" (Step 5) instead.

#### Categories of Directly Actionable Intelligence

**4a: Cell Type Markers for Annotation**

| Cell Type | Markers (RNA) | Markers (Protein/ADT) | In User's ADT Panel? | Confidence | Source |
|-----------|---------------|----------------------|----------------------|------------|--------|
| {cell type} | {gene1}, {gene2}, {gene3} | {protein names with gene symbols in parens} | {yes/no/BROKEN per marker} | {High/Med/Low} | {Fig/Table} |

For each marker, note:
- Whether detectable in the user's specific data (RNA? ADT panel?)
- If an ADT antibody is broken/non-functional, explicitly flag it
- Confidence level based on context match

**4b: Gene Signatures for Scoring**

Provide as **copy-paste-ready Python/R lists**:

```python
# {cell_type or pathway} signature from {Author et al., Year}
# Source: {Figure/Table reference}
# Context: {species, tissue, technology}
# Translation: {any gaps noted}
{var_name} = [
    "{GENE1}", "{GENE2}", "{GENE3}", "{GENE4}",
]
# Usage: sc.tl.score_genes(adata, gene_list={var_name}, score_name='{score_name}')
```

**4c: Expected Cell Frequencies**

| Cell Type | Frequency | Of What Population | Condition | Notes for User's Data |
|-----------|-----------|-------------------|-----------|----------------------|
| {cell type} | {%} | {parent population} | {condition} | {how user's enrichment / preparation affects this} |

Flag if the user's enrichment strategy would change these frequencies.

**4d: Gating/Classification Strategies**

```
Paper's gating hierarchy:
  {Reproduce the paper's hierarchy verbatim — sequence of marker gates leading
   to each cell type}

Translation to user's available markers:
  {For each gate node in the paper's hierarchy:
   - If the marker IS in the user's functional panel: mark as available ✓
   - If the marker IS in the user's panel but is BROKEN: flag and suggest
     RNA substitution (gene symbol from gene_aliases or HUGO)
   - If the marker is NOT in the user's panel: note as RNA-only or unavailable}

Limitations:
  {what cannot be gated with user's panel — e.g., gates requiring multiple
   missing markers cannot be reconstructed}
```

**4e: QC/Technical Considerations**

Specific technical insights relevant to user's data (minimum gene counts, doublet markers, ambient contamination markers, etc.)

### Step 5: Extract Hypothesis-Generating Intelligence

These are findings that cannot be directly applied today but suggest what to look for in the data.

**5a: Age-Related Changes** (if applicable to user's comparisons)

| Prediction | Direction | Cell Type | Evidence Strength | Testable With User's Data? | How to Test |
|------------|-----------|-----------|-------------------|---------------------------|-------------|
| {specific prediction} | {up/down/shift} | {cell type} | {Strong/Moderate/Weak} ({N, p-value if reported}) | {YES/PARTIAL/NO} ({reason}) | {analytical approach} |

**5b: Pathway/Functional Predictions**

| Pathway/Process | Expected Change | Relevant Genes | Scoring Strategy |
|----------------|-----------------|----------------|------------------|
| IL-33 signaling | Reduced in aged | IL1RL1, IL33, MYD88 | Score pathway, compare groups |

**5c: Cell Composition Predictions**

What the paper predicts should differ between the user's conditions.

**5d: Stimulation/Vaccination Response Predictions** (if applicable to user's timepoints)

| Response | Cell Type | Timeframe | Genes/Markers | Source |
|----------|-----------|-----------|---------------|--------|
| {response description} | {cell type} | {timepoints} | {genes/markers and direction} | {Fig/Table} |

**5e: Novel/Exploratory Leads**

Unexpected findings worth investigating in user's data.

### Step 6: Translation Gap Assessment

For every piece of extracted intelligence, document translation gaps honestly.

#### Translation Gap Matrix

| Gap Type | Paper Context | User's Context | Severity | Impact on Intelligence | Mitigation |
|----------|---------------|----------------|----------|------------------------|------------|
| Species | Mouse | Human | HIGH | Gene names may differ, biology may not translate | Use ortholog mapping; treat as hypothesis only |
| Species | Human | Human | NONE | Direct translation | N/A |
| Tissue | Tonsil-resident | PBMC (blood) | MODERATE | Resident vs circulating phenotypes differ | Use blood-specific markers |
| Technology | {paper assay} | {user assay} | {LOW/MOD/HIGH} | {what carries over, what doesn't} | {bridging strategy} |
| Enrichment | {paper sample preparation} | {user sample preparation} | {LOW/MOD/HIGH} | {effect on composition / cell representation} | {how to adjust} |
| Age range | {paper subjects} | {user subjects} | {LOW/MOD/HIGH} | {biological comparability} | {how to handle} |
| Clinical state | {paper subject health} | {user subject health} | {LOW/MOD/HIGH} | {disease/treatment effects on biology of interest} | {filter / caveat} |

For each gap:
- **What is lost**: What information cannot transfer
- **What survives**: What still applies
- **How to bridge**: Specific strategies to work around the gap

### Step 7: Generate Output File

Create the output at: `projects/{project}/literature/{paper_slug}_intel.md`

Where `{paper_slug}` is derived from the filename:
- Extract author surname and 2-3 key words
- Lowercase, underscore-separated
- Example: `"<First Author> - <Topic keywords>.pdf"` → `<lastname>_<topic>_<keywords>`

Ensure the output directory exists:
```bash
mkdir -p projects/{project}/literature
```

#### Output Template

```markdown
---
paper: "{full_paper_filename}"
title: "{extracted paper title}"
first_author: "{first_author}"
year: {year}
journal: "{journal}"
project: {project}
context_file: "{context_filename}"
relevance: {HIGH RELEVANCE|MODERATE RELEVANCE|LOW RELEVANCE}
assessed: {date}
species: {paper species}
tissue: {paper tissue/compartment}
cell_types: [{cell types studied}]
technology: [{technologies used}]
translation_gaps: [{list of gap types}]
---

# Intelligence Report: {Short Paper Title}
## For: {Project Title}

### Paper Overview

**Full title**: {title}
**Citation**: {First Author et al., Journal, Year}
**Study design**: {1-2 sentences: what they did}
**Key cell types**: {what cells they studied}
**Technology**: {what platform/assay}
**Species/Tissue**: {species, tissue compartment}
**Sample size**: {N subjects, conditions}

---

### Relevance Verdict: {HIGH/MODERATE/LOW} RELEVANCE

{2-3 sentences explaining the verdict, referencing specific overlaps and gaps with the user's project.}

**Translation gaps identified**:
- {gap 1 with severity}
- {gap 2 with severity}

---

### Section 1: Directly Actionable Intelligence

> Items in this section can be used in your analysis code TODAY. Each item has been
> verified against your specific data capabilities (ADT panel, RNA availability,
> experimental design).

#### 1.1 Cell Type Markers

| Cell Type | Marker Gene (RNA) | Marker Protein (ADT) | In Your Panel? | Confidence | Source |
|-----------|-------------------|---------------------|----------------|------------|--------|
| {type} | {genes} | {proteins} | {yes/no/BROKEN} | {High/Med/Low} | {Fig/Table} |

#### 1.2 Gene Signatures (Code-Ready)

\```python
# {Signature name} from {Author et al., Year}
# Context: {species, tissue, technology}
# Use: sc.tl.score_genes(adata, gene_list={var_name}, score_name='{score_name}')
{var_name} = [
    "GENE1", "GENE2", "GENE3",
]
\```

#### 1.3 Expected Cell Frequencies

| Cell Type | Expected Frequency | Of What Population | Condition | Notes for Your Data |
|-----------|-------------------|-------------------|-----------|---------------------|
| {type} | {%} | {reference pop} | {condition} | {enrichment effects, etc.} |

#### 1.4 Gating/Classification Strategy

\```
Paper's classification hierarchy:
  {hierarchy}

Translation to your data:
  {translated with ADT panel mapping and RNA substitutions}

Limitations:
  {what cannot be gated with your panel}
\```

#### 1.5 QC/Technical Considerations

{Bulleted list of technical insights}

---

### Section 2: Hypothesis-Generating Intelligence

> Items in this section suggest what to LOOK FOR in your data. They require
> validation and should be treated as hypotheses, not established facts for
> your specific context.

#### 2.1 Predicted Changes: {User's Primary Comparison}

| Prediction | Direction | Cell Type | Evidence Strength | Testable? | How to Test |
|------------|-----------|-----------|-------------------|-----------|-------------|
| {finding} | {up/down/shift} | {type} | {Strong/Moderate/Weak} | {YES/PARTIAL/NO} | {approach} |

#### 2.2 Pathway/Functional Predictions

| Pathway/Process | Expected Change | Relevant Genes | Scoring Strategy |
|----------------|-----------------|----------------|------------------|
| {pathway} | {direction} | {genes} | {how to test} |

#### 2.3 Cell Composition Predictions

| Cell Type | Predicted Shift | Magnitude | Caveat |
|-----------|----------------|-----------|--------|
| {type} | {direction} | {fold-change or %} | {translation gap} |

#### 2.4 Stimulation/Vaccination Response Predictions

| Response | Cell Type | Timeframe | Genes/Markers | Source |
|----------|-----------|-----------|---------------|--------|
| {response} | {type} | {days} | {genes} | {figure/table} |

#### 2.5 Novel/Exploratory Leads

{Unexpected findings worth investigating}

---

### Section 3: Translation Gap Assessment

| Gap | Paper Context | Your Context | Severity | Impact | Mitigation |
|-----|---------------|--------------|----------|--------|------------|
| {type} | {paper} | {user} | {HIGH/MOD/LOW} | {what's affected} | {strategy} |

#### What Is Lost
- {items that do NOT translate}

#### What Survives
- {items that DO translate reliably}

#### Bridging Strategies
- {specific strategies to work around gaps}

---

### Summary Statistics

| Category | Count |
|----------|-------|
| Directly actionable marker genes | {n} |
| Directly actionable protein markers | {n} (of which {m} in your ADT panel) |
| Code-ready gene signatures | {n} |
| Testable hypotheses | {n} |
| Translation gaps identified | {n} |

---

### Cross-References

{If other papers in the literature/ folder corroborate or contradict findings, note them.
Leave blank if this is the first paper mined.}

---

*Generated by `/mine-paper` skill on {date}*
*Context: {context_file}*
```

### Step 8: Verify and Refine

Re-read the generated intel file and check:

#### Honesty Check
- [ ] Every "directly actionable" item passes the Actionability Filter (measurable, specific, applicable, implementable)
- [ ] No vague statements in Section 1 (must be concrete genes, numbers, thresholds)
- [ ] Translation gaps are honestly assessed (not minimized)
- [ ] Items that should be "hypothesis-generating" are NOT in "directly actionable"
- [ ] Confidence levels are defensible

#### Completeness Check
- [ ] All YAML metadata fields populated
- [ ] All relevant cell types from the paper covered
- [ ] Gene signatures are provided as actual gene lists, not descriptions of gene lists
- [ ] Frequencies include specific numbers, not "increased" or "decreased"
- [ ] Gating strategy translated to user's available markers

#### Specificity Check
- [ ] Gene names use official HUGO symbols (human) or MGI symbols (mouse)
- [ ] Protein names include both common name and gene name (e.g., "ProteinName (GENESYMBOL)")
- [ ] Numerical values include units and reference populations
- [ ] Source column traces back to specific figure/table in paper

Make corrections directly to the file.

### Step 9: Report to User

Present a concise summary:

```markdown
## Mining Complete: {Paper Short Title}

**Relevance**: {verdict}

**Extracted**:
- {n} directly actionable marker genes
- {n} code-ready gene signatures
- {n} testable hypotheses
- {n} translation gaps documented

**Key Highlights**:
1. {Most important actionable finding}
2. {Most important hypothesis}
3. {Most important caveat/translation gap}

**Output saved**: `projects/{project}/literature/{paper_slug}_intel.md`

**Suggested next steps**:
- Mine additional papers: `/mine-paper "{next_paper.pdf}" {context_file}`
- Mine all papers: `/mine-paper --all {context_file} --project={project}`
```

---

## Workflow: Batch/Parallel Mode (--all or --papers)

### Step P0: Parse Arguments

Extract from `$ARGUMENTS`:
- **--all**: Process all PDFs in the directory
- **--papers=a.pdf,b.pdf**: Comma-separated list of specific papers
- **context_file.md** (required): Project context file path
- **--project=folder** (optional): Project folder name under `projects/`
- **--dir=path** (optional): Directory containing PDFs (defaults to current directory)
- **--force**: Re-process papers that already have intel files

### Step P1: Discover Papers

```bash
ls {dir}/*.pdf
```

If `--papers` specified, validate each file exists.

### Step P2: Check for Existing Intel Files

```bash
ls projects/{project}/literature/*_intel.md 2>/dev/null
```

Skip papers that already have intel files (unless `--force`).

Report to user:
```markdown
Found {n} papers. {m} already processed, {k} new to process.
```

If all papers already processed and no `--force`, inform user and stop.

### Step P3: Initialize Progress Tracker

Ensure output directory exists:
```bash
mkdir -p projects/{project}/literature
```

Create `projects/{project}/literature/.mining_progress.md`:

```markdown
---
project: {project}
context: {context_file}
started: {date}
architecture: parallel-agents
total_papers: {n}
---

# Literature Mining Progress

| # | Paper | Status | Agent ID | Relevance | Actionable | Hypotheses | Updated |
|---|-------|--------|----------|-----------|------------|------------|---------|
| 1 | {paper_1} | pending | - | - | - | - | - |
| 2 | {paper_2} | pending | - | - | - | - | - |
| ... | ... | ... | ... | ... | ... | ... | ... |

## Agent Log

| Timestamp | Paper | Agent ID | Status |
|-----------|-------|----------|--------|
```

### Step P4: Read Project Context (Orchestrator)

Read the project context file ONCE. You will NOT embed the full context in agent prompts (they will read it themselves), but you need the project name and context file path.

### Step P5: Spawn Mining Agents in Parallel

For each paper, spawn a background agent. Spawn up to 6 agents simultaneously.

```
Task(
    subagent_type: "general-purpose",
    description: "Mine {paper_short_name}",
    prompt: |
        You are mining a biology/research paper for actionable intelligence
        for a specific experimental project.

        ## Your Inputs
        - **Paper PDF**: {paper_path}
        - **Project context file**: {context_file_path}
        - **Output file**: projects/{project}/literature/{paper_slug}_intel.md

        ## Your Task
        Follow this exact workflow:

        ### 1. Read the project context
        Read {context_file_path} and build the Project Parameters Checklist:
        - Species, tissue, cell types of interest
        - Technology, ADT panel (exact antibodies), broken reagents
        - Experimental design, enrichment strategy
        - Known technical issues, flow gate references

        ### 2. First-pass relevance screen
        Read pages 1-5 of the paper:
        Read(file_path: "{paper_path}", pages: "1-5")

        Apply the Relevance Decision Tree:
        - Q1: Does paper study user's cell types? NO → NOT USEFUL
        - Q2: Same species? NO → translatable? NO → NOT USEFUL
        - Q3: Relevant tissue? UNRELATED → LOW RELEVANCE at best
        - Q4: Extractable molecular data? NO → LOW RELEVANCE
        - Q5: User's markers detectable? FEW → LOW RELEVANCE

        Assign: HIGH / MODERATE / LOW / NOT USEFUL

        If NOT USEFUL: Write minimal file with 2-3 sentence explanation and STOP.

        ### 3. Deep read (if relevant)
        Read the full paper systematically (methods, results, figures, supplements).
        For large PDFs (>15 pages), read in targeted page ranges.

        ### 4. Extract Directly Actionable Intelligence (HIGH/MODERATE only)
        Apply the Actionability Filter (measurable + specific + applicable + implementable):
        - Cell type markers (RNA + protein, cross-referenced against user's ADT panel)
        - Gene signatures as copy-paste Python lists
        - Expected cell frequencies
        - Gating strategies translated to user's available markers
        - QC/technical considerations

        CRITICAL: If an ADT antibody is broken/non-functional in the user's data,
        flag it EVERY TIME that marker appears. Suggest RNA alternatives.

        ### 5. Extract Hypothesis-Generating Intelligence
        - Age-related changes, pathway predictions, cell composition shifts
        - Stimulation/vaccination responses (if applicable to user's timepoints)
        - Novel/exploratory leads

        ### 6. Translation Gap Assessment
        For every extracted item, document:
        - Gap type (species, tissue, technology, enrichment, age, clinical)
        - Severity (HIGH/MODERATE/LOW)
        - What is lost, what survives, how to bridge

        ### 7. Write output file
        Create: projects/{project}/literature/{paper_slug}_intel.md
        Ensure directory exists: mkdir -p projects/{project}/literature

        Use the structured template with YAML frontmatter including:
        paper, title, first_author, year, journal, project, context_file,
        relevance, assessed, species, tissue, cell_types, technology, translation_gaps

        ### 8. Quality check
        Re-read your output and verify:
        - All "directly actionable" items pass the Actionability Filter
        - Gene names use HUGO symbols (human) or MGI symbols (mouse)
        - No vague statements in Section 1
        - Translation gaps are honestly documented
        - Source references point to specific figures/tables

        ### After completion, output this summary:
        PAPER: {paper_filename}
        RELEVANCE: [HIGH RELEVANCE|MODERATE RELEVANCE|LOW RELEVANCE|NOT USEFUL]
        ACTIONABLE_MARKERS: [count]
        GENE_SIGNATURES: [count]
        HYPOTHESES: [count]
        TRANSLATION_GAPS: [count]
        OUTPUT_FILE: projects/{project}/literature/{paper_slug}_intel.md
    ,
    run_in_background: true
)
```

Update progress tracker with agent ID.

If more than 6 papers, queue remaining papers. After each agent completes, check if there are queued papers and spawn new agents:

```
TaskOutput(
    task_id: {agent_id},
    block: false,
    timeout: 1000
)
```

### Step P6: Monitor Progress

While agents are running, periodically check their status:

```
TaskOutput(
    task_id: {agent_id},
    block: false,
    timeout: 1000
)
```

Update the progress tracker with status changes.

### Step P7: Wait for All Agents

Wait for all agents to complete (with timeout):

```
for each agent_id:
    TaskOutput(
        task_id: {agent_id},
        block: true,
        timeout: 600000  # 10 minutes
    )
```

### Step P8: Verify Outputs

Background agents can complete successfully without writing the expected file (e.g., due to sandboxed Write denials). Apply the **Output Verification Protocol** to each agent's output:

```bash
ls -la projects/{project}/literature/{paper_slug}_intel.md
wc -l projects/{project}/literature/{paper_slug}_intel.md
```

Each intel file must pass all four checks:
1. **Existence**: file exists on disk
2. **Size**: ≥ 500 bytes (a NOT USEFUL stub is shorter than a full intel file but still has a verdict; anything below this threshold is a write failure)
3. **Frontmatter**: YAML parses and contains `paper:`, `relevance:` fields
4. **Verdict**: relevance is one of HIGH/MODERATE/LOW/NOT USEFUL

For any agent whose output fails verification:
- Mark the paper as `verification_failed` in `.mining_progress.md`
- Record the agent ID and output log path
- Continue with successful agents
- Surface failed papers in the final summary so the user can re-run them

**Do not silently retry** — re-running the same prompt usually reproduces the failure.

### Step P9: Generate Literature Summary

After all evaluations complete, read each `_intel.md` file and create `projects/{project}/literature/literature_summary.md`:

```markdown
---
project: {project}
context: {context_file}
papers_evaluated: {n}
completed: {date}
---

# Literature Mining Summary: {Project Title}

## Overview

| Metric | Count |
|--------|-------|
| Papers evaluated | {n} |
| High relevance | {n} |
| Moderate relevance | {n} |
| Low relevance | {n} |
| Not useful | {n} |
| Total actionable markers | {n} |
| Total gene signatures | {n} |
| Total testable hypotheses | {n} |

## Papers by Relevance

### HIGH RELEVANCE

| Paper | Key Contribution | Actionable Items | Hypotheses |
|-------|-----------------|------------------|------------|
| {paper} | {1-line} | {n} | {n} |

### MODERATE RELEVANCE

| Paper | Key Contribution | Actionable Items | Hypotheses | Primary Gap |
|-------|-----------------|------------------|------------|-------------|
| {paper} | {1-line} | {n} | {n} | {gap} |

### LOW RELEVANCE

| Paper | Why Low | Hypotheses |
|-------|---------|------------|
| {paper} | {reason} | {n} |

### NOT USEFUL

| Paper | Reason |
|-------|--------|
| {paper} | {1-line reason} |

## Consolidated Marker Panel

Markers cited by multiple papers (higher confidence):

| Marker | Cell Type | Papers Citing | RNA? | In ADT Panel? | Consensus Confidence |
|--------|-----------|---------------|------|---------------|----------------------|
| {gene} | {cell type} | {n}/{total} | {YES/NO} | {YES/NO/BROKEN} | {High/Medium/Low} |

## Consolidated Hypotheses

Hypotheses supported by multiple papers:

| Hypothesis | Papers Supporting | Strength | Testable? | Priority |
|------------|------------------|----------|-----------|----------|
| {hypothesis} | {n} papers | {Strong/Moderate/Weak} | {YES/PARTIAL/NO} | {HIGH/MED/LOW} |

## Recommended Analysis Strategy

Based on the accumulated intelligence:

1. **Cell type annotation**: {strategy using consolidated markers}
2. **Primary comparison ({user's comparison})**: {what to test first}
3. **Pathway analysis**: {which pathways to score}
4. **Unexpected leads**: {novel findings worth exploring}

## Individual Reports

- [{paper_1_slug}_intel.md]({paper_1_slug}_intel.md)
- [{paper_2_slug}_intel.md]({paper_2_slug}_intel.md)
- ...

---

*Generated by `/mine-paper --all` on {date}*
```

### Step P10: Report to User

```markdown
## Literature Mining Complete

Evaluated **{n} papers** for your {project} project.

### Results by Relevance:

| Relevance | Count | Papers |
|-----------|-------|--------|
| High | {n} | {names} |
| Moderate | {n} | {names} |
| Low | {n} | {names} |
| Not Useful | {n} | {names} |

### Key Numbers:
- {n} unique marker genes across all papers
- {n} code-ready gene signatures
- {n} testable hypotheses ({m} supported by multiple papers)

### Files Generated:
- Summary: `projects/{project}/literature/literature_summary.md`
- Individual reports: `projects/{project}/literature/*_intel.md`

### Top Recommendations:
1. {Most confident annotation strategy from consolidated markers}
2. {Highest-priority testable hypothesis}
3. {Most important caveat to keep in mind}
```

---

## Error Handling

### Agent Timeout (Batch Mode)
If a mining agent times out (>10 minutes):
- Log failure in progress tracker
- Continue with other papers
- Report incomplete evaluations at end

### PDF Read Failures
If a PDF cannot be read (corrupt, too large, password-protected):
- Log the error
- Create a minimal intel file noting the failure
- Continue to next paper

### Missing Context File
If context file cannot be found:
- Stop immediately and ask user for valid path
- Cannot proceed without project context

---

## Important Notes

- **Do not pad relevance**: It is expected that some papers are NOT USEFUL. 5 honest evaluations beat 13 forced ones.
- **Gene names must be exact**: Use HUGO symbols for human (UPPERCASE), MGI for mouse (Capitalized). Note common protein names alongside in parens, e.g., "ProteinName (GENESYMBOL)".
- **ADT panel awareness**: Always cross-reference extracted protein markers against the user's actual ADT panel. A beautiful flow strategy is useless without the antibodies.
- **Broken / non-functional reagents**: If the project context flags any antibody or probe as non-functional, flag it EVERY TIME that marker appears in the paper. Suggest the documented RNA (or other) alternative.
- **Enrichment bias**: The user's enrichment strategy creates non-representative composition. Note how this affects frequency data from papers using whole PBMC or different sorting.
- **Code-ready output**: Gene signatures must be formatted as Python lists or R vectors that can be copy-pasted. Include source comments.
- **Reviews vs original research**: Review papers without original data can still be HIGH RELEVANCE if they consolidate marker panels or provide consensus gating strategies. But flag that the data is secondary.

---

## Directory Structure After Mining

```
<your-project-root>/
├── *.pdf                                  # Source papers (or in papers/ subdir)
├── projects/
│   └── <project-name>/
│       ├── context.md                     # Project context (input)
│       └── literature/                    # Mining outputs
│           ├── .mining_progress.md        # Progress (batch mode)
│           ├── literature_summary.md      # Cross-paper summary (batch mode)
│           ├── <paper-slug-1>_intel.md
│           ├── <paper-slug-2>_intel.md
│           └── ...
└── .claude/skills/                        # this set of skills
```

---

*This skill bridges the gap between reading papers and applying their findings. It transforms passive literature review into active intelligence extraction, producing machine-readable and human-actionable output.*
