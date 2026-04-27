---
name: index-docs
description: Index a documentation site (readthedocs/sphinx) to create a navigation layer for AI agents
argument-hint: <docs-url> <ecosystem-name>
allowed-tools: Read, Glob, Grep, Write, Edit, WebFetch, Bash(mkdir *), Task, TaskOutput, AskUserQuestion
---

# Index Documentation Skill

This skill indexes documentation sites (readthedocs, sphinx, pkgdown) to create a **navigation layer** for AI agents. Instead of storing full documentation, it creates a structured map that tells agents *where to look* for specific information.

## Design Philosophy

- **Don't duplicate docs** - AI can WebFetch live content
- **Create a compass** - Tell agents which section answers which questions
- **Track structure** - Module hierarchy, function index, capability map
- **Handle evolution** - Overwrite on update, track sync metadata

## Output Structure

```
knowledge_base/ecosystems/{ecosystem}/
├── navigation.md        # Human-readable overview
├── capabilities.yaml    # Module-level: what each section covers
├── function_index.yaml  # Flat function lookup with signatures
├── workflows.yaml       # Tutorial-derived function clusters
└── sync_metadata.yaml   # When synced, version, URLs checked
```

---

## Workflow

### Step 0: Parse Arguments

Extract from `$ARGUMENTS`:
- **docs-url** (required): Root URL of documentation site (e.g., `https://scanpy.readthedocs.io/en/stable/`)
- **ecosystem-name** (required): Name for the ecosystem (e.g., `scanpy`, `seurat`, `scvi-tools`)

If arguments missing, ask user:

**"Please provide the documentation URL and ecosystem name:"**
- Documentation URL: [text input]
- Ecosystem name: [text input]

### Step 1: Initialize Working Directory

```bash
mkdir -p knowledge_base/ecosystems/{ecosystem}/_working/modules
```

Create initial `sync_metadata.yaml`:

```yaml
ecosystem: {ecosystem}
docs_url: {docs-url}
sync_started: {timestamp}
sync_status: in_progress
phases_completed: []
```

### Step 2: Detect Documentation Type

Documentation frameworks differ structurally; the WebFetch prompts must adapt or extraction will produce empty/partial results. Detect the type BEFORE Phase 1.

Probe the URL pattern and a quick fetch:

| Signal | Likely Type |
|--------|-------------|
| URL contains `readthedocs.io` or `/en/stable/` | Sphinx |
| URL contains `satijalab.org`, `bioconductor.org/packages`, or has `/reference/index.html` | pkgdown (R) |
| URL contains `docs.{project}.org` and uses Sphinx CSS | Sphinx (custom domain) |
| HTML has `<div class="bd-sidebar">` or `pydata-sphinx-theme` | PyData Sphinx |
| HTML has `<nav class="navbar">` with pkgdown classes | pkgdown |
| None of the above | Custom |

```
WebFetch(
    url: "{docs-url}",
    prompt: "Look at the page structure (CSS classes, nav element layout, link patterns). Tell me: is this Sphinx, pkgdown, MkDocs, Docusaurus, or custom? Also extract the main navigation: list the top-level section names with their URLs."
)
```

Record the detected type in `sync_metadata.yaml`:

```yaml
doc_type: sphinx  # or pkgdown, mkdocs, docusaurus, custom
```

Use this type to choose appropriate prompts in subsequent phases:
- **Sphinx/PyData**: Look for `autosummary`, `_modules`, `genindex.html`. Function names appear as `module.submodule.function`.
- **pkgdown**: Look for `reference/` index, `articles/` for vignettes. Function names are bare (no module prefix in R).
- **MkDocs/Docusaurus**: Look for `mkdocs.yml`-derived nav, often less structured for API extraction. May need to follow individual function pages.
- **Custom**: Ask the user to point at the API reference URL directly.

---

## Phase 1: Map Documentation Structure

### 1.1: Fetch Main Index

Use WebFetch to get the documentation index/API page:

```
WebFetch(
    url: "{docs-url}",
    prompt: "Extract the main navigation structure. List all top-level sections/modules with their URLs. Format as a simple list: - Section Name: URL"
)
```

For API documentation specifically (often at `/api/` or `/api.html`):

```
WebFetch(
    url: "{docs-url}/api/index.html" or "{docs-url}/api.html",
    prompt: "Extract the API module structure. List all module categories (e.g., preprocessing, tools, plotting) with their URLs."
)
```

### 1.2: Identify Documentation Type

Determine the documentation framework:
- **Sphinx/readthedocs**: Look for `_static/`, `genindex.html`
- **pkgdown (R)**: Look for `reference/index.html`, `articles/`
- **Custom**: Note the structure for manual handling

### 1.3: Build Module URL List

Write to `_working/module_urls.yaml`:

```yaml
doc_type: sphinx  # or pkgdown, custom
modules:
  - name: preprocessing
    url: https://scanpy.readthedocs.io/en/stable/api/preprocessing.html
    category: api
  - name: tools
    url: https://scanpy.readthedocs.io/en/stable/api/tools.html
    category: api
  - name: plotting
    url: https://scanpy.readthedocs.io/en/stable/api/plotting.html
    category: api
  - name: getting-started
    url: https://scanpy.readthedocs.io/en/stable/tutorials/basics/...
    category: tutorial
```

### 1.4: Update Sync Metadata

```yaml
phases_completed: [structure_mapping]
modules_found: {count}
```

---

## Phase 2: Extract Module Details (Chunked)

**CRITICAL**: Process ONE module at a time to avoid context overflow.

For each module in `_working/module_urls.yaml`:

### 2.1: Fetch Module Page

```
WebFetch(
    url: "{module_url}",
    prompt: |
        Extract ALL functions/classes listed on this page. For each, provide:
        1. Function name (e.g., scanpy.pp.filter_cells)
        2. One-line description (first line of docstring)
        3. Basic signature if visible (parameters)
        4. Any "See Also" references

        Format as YAML:
        functions:
          - name: full.function.name
            signature: "(param1, param2, ...)"
            one_liner: "Brief description"
            see_also: [related_func1, related_func2]
)
```

### 2.2: Write Module File

Save to `_working/modules/{module_name}.yaml`:

```yaml
module: preprocessing
url: https://scanpy.readthedocs.io/en/stable/api/preprocessing.html
category: api
functions:
  - name: scanpy.pp.filter_cells
    signature: "(adata, min_counts=None, min_genes=None, max_counts=None, max_genes=None)"
    one_liner: "Filter cell outliers based on counts and numbers of genes expressed"
    see_also: [filter_genes]
  - name: scanpy.pp.filter_genes
    signature: "(adata, min_cells=None, min_counts=None, max_cells=None, max_counts=None)"
    one_liner: "Filter genes based on number of cells or counts"
    see_also: [filter_cells]
  # ... more functions
```

### 2.3: Progress Tracking

After each module, update `sync_metadata.yaml`:

```yaml
modules_processed:
  - preprocessing: complete
  - tools: complete
  - plotting: in_progress
```

### 2.4: Repeat for All Modules

Continue until all modules processed. The key is: **fetch one page, extract, write to disk, move on**.

---

## Phase 3: Semantic Enrichment

For each module file in `_working/modules/`:

### 3.1: Add Workflow Context

Read the module file and enrich with:
- `purpose`: What does this module do overall?
- `typical_workflow_position`: When in an analysis would you use this?
- `covers`: List of tasks/problems this module addresses
- `when_to_consult`: Natural language description of when to look here

### 3.2: Add Related Tasks Tags

For each function, add `related_tasks` based on what problems it solves:

```yaml
- name: scanpy.pp.normalize_total
  signature: "(adata, target_sum=None, ...)"
  one_liner: "Normalize counts per cell"
  see_also: [normalize_per_cell, scale]
  related_tasks:
    - normalization
    - library_size_correction
    - CPM_conversion
    - counts_per_cell
```

### 3.3: Cross-Reference Knowledge Base

Check if any related methods exist in knowledge base:

```bash
ls knowledge_base/*/concept.md
```

For each method found, check if it relates to functions in this ecosystem. Add cross-references:

```yaml
- name: scvi.model.SCVI
  # ...
  kb_references:
    - method: totalVI
      relationship: "totalVI extends SCVI for CITE-seq data"
```

### 3.4: Write Enriched Module Files

Overwrite `_working/modules/{module}.yaml` with enriched version.

---

## Phase 4: Assemble Final Output

### 4.1: Generate capabilities.yaml

Read all `_working/modules/*.yaml` and create:

```yaml
# knowledge_base/ecosystems/{ecosystem}/capabilities.yaml
# Auto-generated by /index-docs skill
# Last sync: {timestamp}

ecosystem: {ecosystem}
docs_url: {docs-url}
doc_type: sphinx

modules:
  preprocessing:
    url: https://scanpy.readthedocs.io/en/stable/api/preprocessing.html
    purpose: "Transform raw count matrices into analysis-ready data"
    typical_workflow_position: "After loading, before dimensionality reduction"
    covers:
      - quality control and filtering
      - normalization strategies
      - feature selection (highly variable genes)
      - batch correction basics
    when_to_consult: "User needs to clean, normalize, or prepare raw data"
    function_count: 25

  tools:
    url: https://scanpy.readthedocs.io/en/stable/api/tools.html
    purpose: "Core analysis algorithms"
    typical_workflow_position: "After preprocessing, for main analysis"
    covers:
      - dimensionality reduction (PCA, neighbors, UMAP)
      - clustering (leiden, louvain)
      - differential expression
      - trajectory inference
      - gene scoring
    when_to_consult: "User needs to run analysis algorithms"
    function_count: 40

  plotting:
    url: https://scanpy.readthedocs.io/en/stable/api/plotting.html
    purpose: "Visualization functions"
    typical_workflow_position: "Throughout analysis for visualization"
    covers:
      - embedding plots (UMAP, tSNE)
      - gene expression visualization
      - QC plots
      - heatmaps and dotplots
    when_to_consult: "User needs to visualize results"
    function_count: 35
```

### 4.2: Generate function_index.yaml

Create flat, searchable function index:

```yaml
# knowledge_base/ecosystems/{ecosystem}/function_index.yaml
# Flat index for quick function lookup
# Use Ctrl+F or grep to find functions

ecosystem: {ecosystem}
total_functions: {count}

functions:
  filter_cells:
    full_name: scanpy.pp.filter_cells
    module: preprocessing
    url: "https://scanpy.readthedocs.io/en/stable/api/generated/scanpy.pp.filter_cells.html"
    signature: "(adata, min_counts=None, min_genes=None, ...)"
    one_liner: "Filter cell outliers based on counts and numbers of genes expressed"
    related_tasks: [quality_control, filtering, cell_QC]
    see_also: [filter_genes]

  filter_genes:
    full_name: scanpy.pp.filter_genes
    module: preprocessing
    url: "https://scanpy.readthedocs.io/en/stable/api/generated/scanpy.pp.filter_genes.html"
    signature: "(adata, min_cells=None, min_counts=None, ...)"
    one_liner: "Filter genes based on number of cells or counts"
    related_tasks: [quality_control, filtering, gene_QC]
    see_also: [filter_cells]

  normalize_total:
    full_name: scanpy.pp.normalize_total
    module: preprocessing
    url: "https://scanpy.readthedocs.io/en/stable/api/generated/scanpy.pp.normalize_total.html"
    signature: "(adata, target_sum=None, exclude_highly_expressed=False, ...)"
    one_liner: "Normalize counts per cell to target sum"
    related_tasks: [normalization, library_size, CPM]
    see_also: [log1p, scale]

  # ... all other functions in flat structure
```

### 4.3: Generate navigation.md

Create human-readable overview:

```markdown
---
ecosystem: {ecosystem}
docs_url: {docs-url}
last_sync: {timestamp}
version: {if detectable}
---

# {Ecosystem} Documentation Navigation

> This file helps AI agents navigate {ecosystem} documentation efficiently.
> Instead of storing full docs, it maps where to find information.

## Overview

{Ecosystem} is a {brief description extracted from docs}.

**Documentation**: [{docs-url}]({docs-url})
**Total modules indexed**: {count}
**Total functions indexed**: {count}

## Quick Reference

| Task | Module | Key Functions |
|------|--------|---------------|
| Quality control | preprocessing | filter_cells, filter_genes |
| Normalization | preprocessing | normalize_total, log1p |
| Dim reduction | tools | pca, neighbors, umap |
| Clustering | tools | leiden, louvain |
| Diff expression | tools | rank_genes_groups |
| Visualization | plotting | umap, dotplot, heatmap |

## Module Overview

### Preprocessing (`scanpy.pp`)

**Purpose**: Transform raw count matrices into analysis-ready data

**When to use**: After loading raw data, before running analysis algorithms

**Key capabilities**:
- Quality control: `filter_cells`, `filter_genes`, `calculate_qc_metrics`
- Normalization: `normalize_total`, `log1p`, `scale`
- Feature selection: `highly_variable_genes`

**Documentation**: [preprocessing API]({url})

### Tools (`scanpy.tl`)

[Similar structure for each module]

## Usage for AI Agents

When a user asks about {ecosystem}:

1. **Check this file first** - Identify which module likely has the answer
2. **Check function_index.yaml** - Find specific function details
3. **WebFetch the URL** - Get live, current documentation for details

Example workflow:
- User: "How do I normalize my data in scanpy?"
- Agent checks navigation.md → preprocessing module handles normalization
- Agent checks function_index.yaml → `normalize_total` is the key function
- If more detail needed → WebFetch the specific function URL

## Cross-References to Knowledge Base

{List any methods in knowledge_base/ that relate to this ecosystem}

---

*Generated by /index-docs skill on {timestamp}*
*Sync metadata: sync_metadata.yaml*
```

### 4.4: Finalize sync_metadata.yaml

```yaml
ecosystem: {ecosystem}
docs_url: {docs-url}
doc_type: sphinx
sync_started: {timestamp}
sync_completed: {timestamp}
sync_status: complete

stats:
  modules_indexed: {count}
  functions_indexed: {count}
  tutorials_indexed: {count}

phases_completed:
  - structure_mapping
  - module_extraction
  - semantic_enrichment
  - assembly

version_detected: {if found in docs}
```

### 4.5: Hold Working Directory

Do NOT clean up yet - we need `_working/` for Phase 5.

---

## Phase 5: Extract Tutorial Workflows

Tutorials show which functions work together for specific tasks. This phase extracts those "function clusters" and links them to our function_index.

### 5.1: Identify Tutorial Pages

From Phase 1 structure mapping, identify tutorial URLs. For Scanpy:

```
WebFetch(
    url: "{docs-url}/tutorials/index.html",
    prompt: "List all tutorials with their URLs and a brief description of what each covers."
)
```

Write to `_working/tutorial_urls.yaml`:

```yaml
tutorials:
  - name: "Preprocessing and clustering 3k PBMCs"
    url: "https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering.html"
    category: basics
  - name: "Visualization"
    url: "https://scanpy.readthedocs.io/en/stable/tutorials/plotting/core.html"
    category: plotting
  - name: "Trajectory inference"
    url: "https://scanpy.readthedocs.io/en/stable/tutorials/trajectories/..."
    category: trajectories
```

### 5.2: Extract Function Sequences (Chunked)

**CRITICAL**: Process ONE tutorial at a time.

For each tutorial:

```
WebFetch(
    url: "{tutorial_url}",
    prompt: |
        Extract the sequence of scanpy function calls used in this tutorial.
        For each function, note:
        1. Full function name (e.g., scanpy.pp.filter_cells)
        2. Brief purpose in this context

        Format as YAML:
        functions_used:
          - name: scanpy.pp.filter_cells
            purpose: "Remove cells with too few genes"
          - name: scanpy.pp.filter_genes
            purpose: "Remove genes expressed in too few cells"

        Also extract:
        - goal: What is the overall goal of this tutorial?
        - when_to_use: When would someone follow this workflow?
)
```

### 5.3: Write Tutorial Extraction

Save to `_working/tutorials/{tutorial_name}.yaml`:

```yaml
name: "Preprocessing and clustering 3k PBMCs"
url: "https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering.html"
category: basics
goal: "Go from raw 10X data to clustered and annotated cells"
when_to_use: "Starting a standard scRNA-seq analysis"

functions_used:
  - name: scanpy.read_10x_mtx
    purpose: "Load 10X Genomics data"
  - name: scanpy.pp.filter_cells
    purpose: "Remove low-quality cells"
  - name: scanpy.pp.filter_genes
    purpose: "Remove unexpressed genes"
  - name: scanpy.pp.normalize_total
    purpose: "Normalize counts per cell"
  - name: scanpy.pp.log1p
    purpose: "Log-transform data"
  - name: scanpy.pp.highly_variable_genes
    purpose: "Select informative genes"
  - name: scanpy.tl.pca
    purpose: "Dimensionality reduction"
  - name: scanpy.pp.neighbors
    purpose: "Compute cell neighborhood graph"
  - name: scanpy.tl.umap
    purpose: "Compute 2D embedding"
  - name: scanpy.tl.leiden
    purpose: "Cluster cells"
  - name: scanpy.pl.umap
    purpose: "Visualize clusters"
```

### 5.4: Validate Against Function Index

For each tutorial extraction, check that functions exist in our index:

```python
# Pseudocode for validation logic
for tutorial in tutorials:
    for func in tutorial.functions_used:
        short_name = func.name.split('.')[-1]  # e.g., "filter_cells"

        if short_name not in function_index:
            warnings.append(f"{tutorial.name}: {func.name} not in function_index")
        elif function_index[short_name].full_name != func.name:
            # Name collision - same short name, different full name
            notes.append(f"{tutorial.name}: {func.name} - verify correct function")
```

Write validation results to `_working/tutorial_validation.yaml`:

```yaml
validated: true
warnings:
  - "Tutorial 'Integration' references 'bbknn.bbknn' - external package, not in index"
notes:
  - "Tutorial 'Visualization' uses both scanpy.tl.umap and scanpy.pl.umap"
coverage:
  functions_in_tutorials: 45
  functions_in_index: 120
  overlap_percentage: 37.5%
```

### 5.5: Generate workflows.yaml

Assemble all tutorials into final workflows file:

```yaml
# knowledge_base/ecosystems/{ecosystem}/workflows.yaml
# Tutorial-derived function clusters
# Links to function_index.yaml for details

ecosystem: {ecosystem}
docs_url: {docs-url}
last_sync: {timestamp}
total_workflows: {count}

# Validation summary
validation:
  all_functions_found: true  # or false with warnings
  warnings: []
  external_packages_referenced:
    - bbknn
    - harmonypy

workflows:
  preprocessing_clustering_3k:
    name: "Preprocessing and clustering 3k PBMCs"
    tutorial_url: "https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering.html"
    category: basics
    goal: "Go from raw 10X data to clustered and annotated cells"
    when_to_use: "Starting a standard scRNA-seq analysis from 10X data"

    steps:
      # Each step references function_index.yaml by full_name
      - function: scanpy.read_10x_mtx
        purpose: "Load 10X Genomics data"
        index_key: read_10x_mtx  # key in function_index.yaml

      - function: scanpy.pp.filter_cells
        purpose: "Remove low-quality cells"
        index_key: filter_cells

      - function: scanpy.pp.filter_genes
        purpose: "Remove unexpressed genes"
        index_key: filter_genes

      - function: scanpy.pp.normalize_total
        purpose: "Normalize counts per cell"
        index_key: normalize_total

      - function: scanpy.pp.log1p
        purpose: "Log-transform data"
        index_key: log1p

      - function: scanpy.pp.highly_variable_genes
        purpose: "Select informative genes"
        index_key: highly_variable_genes

      - function: scanpy.tl.pca
        purpose: "Dimensionality reduction"
        index_key: pca

      - function: scanpy.pp.neighbors
        purpose: "Compute cell neighborhood graph"
        index_key: neighbors

      - function: scanpy.tl.umap
        purpose: "Compute 2D embedding"
        index_key: umap
        note: "This is scanpy.tl.umap (compute), not scanpy.pl.umap (plot)"

      - function: scanpy.tl.leiden
        purpose: "Cluster cells"
        index_key: leiden

      - function: scanpy.pl.umap
        purpose: "Visualize clusters"
        index_key: umap
        note: "This is scanpy.pl.umap (plot), not scanpy.tl.umap (compute)"

  visualization_basics:
    name: "Basic Visualization"
    tutorial_url: "..."
    # ... similar structure

  trajectory_inference:
    name: "Trajectory Inference with PAGA"
    tutorial_url: "..."
    # ... similar structure
```

### 5.6: Update Sync Metadata

```yaml
phases_completed:
  - structure_mapping
  - module_extraction
  - semantic_enrichment
  - api_assembly
  - tutorial_extraction  # NEW

stats:
  modules_indexed: {count}
  functions_indexed: {count}
  tutorials_indexed: {count}
  workflows_extracted: {count}
```

---

## Phase 6: Generate Navigation

Now generate navigation.md with references to BOTH API and workflows.

### 6.1: Cleanup Working Directory

```bash
rm -rf knowledge_base/ecosystems/{ecosystem}/_working
```

---

## Phase 7: Verification

### 7.1: Verify Output Files Exist

```bash
ls -la knowledge_base/ecosystems/{ecosystem}/
```

Expected:
- navigation.md
- capabilities.yaml
- function_index.yaml
- workflows.yaml
- sync_metadata.yaml

### 7.2: Spot Check Content

**Function Index**: Read a few entries from function_index.yaml and verify:
- URLs are valid format
- Signatures look reasonable
- One-liners are populated

**Workflows**: Read workflows.yaml and verify:
- Function references use full names (e.g., scanpy.pp.filter_cells)
- Steps are in logical workflow order
- Validation section shows any warnings about missing functions

### 7.3: Report to User

```markdown
## Documentation Index Complete

**Ecosystem**: {ecosystem}
**Source**: {docs-url}

**Files created**:
- `navigation.md` - Human-readable overview with decision tree
- `capabilities.yaml` - Module capability map ({module_count} modules)
- `function_index.yaml` - Function lookup ({function_count} functions)
- `workflows.yaml` - Tutorial-derived workflows ({workflow_count} workflows)
- `sync_metadata.yaml` - Sync tracking

**API Coverage**:
- Modules indexed: {module_count}
- Functions indexed: {function_count}

**Workflow Coverage**:
- Tutorials processed: {tutorial_count}
- Workflows extracted: {workflow_count}
- Validation: {PASS or list warnings}

**Next steps**:
- Review the generated files, especially workflows.yaml validation section
- Edit navigation.md if you want to add custom notes
- Re-run `/index-docs` anytime to refresh with latest docs

**To update later**:
/index-docs {docs-url} {ecosystem}
(This will overwrite with fresh content)
```

---

## Handling Different Documentation Types

### Sphinx/readthedocs (Python)

Standard structure:
- `/api/` or `/api.html` - API reference
- `/tutorials/` - Tutorial pages
- `/genindex.html` - Generated index (useful for function discovery)

### pkgdown (R packages like Seurat)

Standard structure:
- `/reference/index.html` - Function reference
- `/articles/` - Vignettes/tutorials
- `/news/` - Changelog

Adapt WebFetch prompts for HTML table structure common in pkgdown.

### Custom Documentation

If structure is non-standard:
1. Ask user to provide key URLs manually
2. Note the custom structure in sync_metadata.yaml
3. Document any special handling in navigation.md

---

## Error Handling

### WebFetch Failures

If a URL fails to fetch:
1. Log the failure in sync_metadata.yaml
2. Continue with other modules
3. Report failures at the end

```yaml
fetch_errors:
  - url: https://...
    error: "Connection timeout"
    phase: module_extraction
```

### Incomplete Extraction

If a module page doesn't yield expected structure:
1. Save what was extracted
2. Mark as `partial` in metadata
3. Suggest manual review

### Large Documentation Sites

For sites with 100+ functions per module:
- Process in batches of ~50 functions
- Use multiple WebFetch calls with offset prompts
- Merge results before writing module file

---

## Tips

- Run this skill periodically (monthly?) to catch documentation updates
- The function_index.yaml is intentionally flat for easy grepping
- Cross-references to knowledge_base methods are valuable - add manually if missed
- Consider creating a `CLAUDE.md` entry pointing agents to check ecosystems/ for established tools

---

## Usage Examples

```bash
# Index Scanpy documentation
/index-docs https://scanpy.readthedocs.io/en/stable/ scanpy

# Index scvi-tools documentation
/index-docs https://docs.scvi-tools.org/en/stable/ scvi-tools

# Index Seurat documentation (R)
/index-docs https://satijalab.org/seurat/ seurat

# Re-sync to get latest
/index-docs https://scanpy.readthedocs.io/en/stable/ scanpy
```

---

*This skill creates a documentation navigation layer, not a documentation mirror. AI agents use it to know WHERE to look, then fetch live docs for current details.*
