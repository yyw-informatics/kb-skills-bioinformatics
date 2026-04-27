---
name: adapt-method
description: "Apply a method from the knowledge base to your actual data with preliminary analysis"
---

# Codex Adapter

This adapter is generated from `skills/adapt-method/SKILL.md`. Edit the source Claude skill, then run `python3 scripts/sync_codex_skills.py` to refresh the Codex mirror.

Preserve the shared workflow contract: `knowledge_base/`, `projects/<name>/literature/`, `fitness_summary.md`, `analysis_plan.md`, audit files, and progress files remain the expected outputs.

## Claude-to-Codex Term Map

- `/skill-name` examples mean `$skill-name` or explicit plugin/skill invocation in Codex.
- `Task` / `TaskOutput` mean delegated/fresh-agent execution when available; otherwise run phases sequentially and verify files.
- `AskUserQuestion` means ask the user directly when required.
- `WebFetch` / `WebSearch` mean Codex web/search tools when available.

## Source Skill Instructions

# Adapt Method Skill

This skill helps you apply a bioinformatics method from the knowledge base to your actual data. It performs environment setup, data discovery, method-specific exploratory analysis, and generates a preliminary run with real results.

## Prerequisites

Before using this skill:
1. The method should have knowledge base entries (concept.md, code.md at minimum)
2. Ideally, run `/evaluate-fit` first to assess compatibility
3. Have your data ready in a known location

## Workflow Overview

```
Phase 1: Setup → Phase 2: Data Discovery → Phase 3: Method EDA → Phase 4: Preliminary Run → Phase 5: Report
```

---

## Phase 1: Environment & Data Setup

### Step 1.1: Identify Method

Parse `$ARGUMENTS` to determine the method name.

If no method specified, check for existing fitness assessments in the project:
```bash
ls projects/*/\*_fitness_assessment.md 2>/dev/null
```

Or list available methods:
```bash
ls knowledge_base/
```

### Step 1.2: Load Method Metadata

Read the method's code.md to determine:
- **Language**: R or Python (from YAML frontmatter `language` field)
- **Dependencies**: Required packages
- **Input format**: Expected data structure

```markdown
# Example: Extract from code.md YAML
language: R  # or Python
```

### Step 1.3: Check Conda Environment

First verify conda is available:

```bash
conda --version
```

If `conda` is not found:
- Inform the user: "conda is not installed or not on PATH. This skill assumes conda for environment management. Install Miniconda (https://docs.conda.io/projects/miniconda/) or specify an alternative environment manager (venv, virtualenv, mamba)."
- If the user has an alternative manager (venv, mamba, etc.), adapt the commands below accordingly: `mamba` is a drop-in for `conda`; for `venv`, replace `conda run -n <env>` with sourcing the activate script.
- If no environment manager: warn the user that the script may fail due to missing dependencies and ask whether to proceed system-wide.

Then ask the user about their environment:

**"Do you have a conda environment set up for this analysis?"**
- [ ] Yes, I have an environment
- [ ] No, I need to create one
- [ ] I'm using a different environment manager

If yes, ask for the environment name:
- Validate it exists: `conda env list | grep <env_name>`
- Check for required packages based on method's code.md

#### R Environment Check
```bash
# Substitute the actual package names from the method's code.md `dependencies:` field
conda run -n <env_name> R --quiet -e "installed.packages()[,'Package']" 2>/dev/null | grep -E "({pkg1}|{pkg2}|{pkg3})"
```

#### Python Environment Check
```bash
conda run -n <env_name> python -c "import pkg_resources; print([p.project_name for p in pkg_resources.working_set])" 2>/dev/null
```

If missing packages, inform the user:
```markdown
**Missing packages detected:**
- `{package_name}` - Install with: `{install command from code.md}`

Would you like to proceed anyway, or install these first?
```

### Step 1.4: Get Data Location

Ask the user:

**"Where is your data located?"**

Validate the path:
- Check if path exists
- Detect data format based on file extension or directory structure

#### Data Format Detection

| Pattern | Detected Format | Language |
|---------|-----------------|----------|
| `*.rds`, `*.RDS` | Seurat/R object | R |
| `*.h5ad` | AnnData | Python |
| `outs/filtered_feature_bc_matrix/` | CellRanger output | Either |
| `*.h5` | 10x HDF5 | Either |
| `*.csv`, `*.tsv` | Raw matrix | Either |
| `*.mtx` + `*.tsv` | Market Matrix format | Either |

If unclear, ask follow-up questions:
- What format is your data in?
- Is this a single sample or multiple samples?
- Do you have a metadata file?

### Step 1.5: Check for Existing Project Folder

Look for existing project context:
```bash
ls projects/*/
```

Ask user:
**"Which project folder should this adaptation be saved to?"**
- [ ] [List existing project folders]
- [ ] Create new project folder

---

## Phase 2: Data Discovery

### Step 2.1: Generate Data Discovery Script

Based on detected format and language, generate a script to extract basic data characteristics.

#### R Script Template (Seurat/RDS)
```r
# 01_data_discovery.R
# Generated by /adapt-method skill

library(Seurat)

# Load data
data_path <- "{DATA_PATH}"
obj <- readRDS(data_path)

# Basic stats
cat("=== DATA DISCOVERY REPORT ===\n")
cat("Object class:", class(obj), "\n")
cat("Cells:", ncol(obj), "\n")
cat("Features:", nrow(obj), "\n")

# Assays
cat("\n=== ASSAYS ===\n")
cat("Available assays:", names(obj@assays), "\n")
for (assay in names(obj@assays)) {
  cat(sprintf("  %s: %d features\n", assay, nrow(obj[[assay]])))
}

# Metadata columns
cat("\n=== METADATA ===\n")
cat("Columns:", paste(colnames(obj@meta.data), collapse = ", "), "\n")

# Sample structure (if present)
if ("sample" %in% colnames(obj@meta.data)) {
  cat("\n=== SAMPLE STRUCTURE ===\n")
  print(table(obj$sample))
}

# Save summary
discovery_results <- list(
  n_cells = ncol(obj),
  n_features = nrow(obj),
  assays = names(obj@assays),
  metadata_cols = colnames(obj@meta.data),
  sample_table = if ("sample" %in% colnames(obj@meta.data)) table(obj$sample) else NULL
)
saveRDS(discovery_results, "{OUTPUT_DIR}/data_discovery_results.rds")
cat("\nResults saved to: {OUTPUT_DIR}/data_discovery_results.rds\n")
```

#### Python Script Template (AnnData)
```python
# 01_data_discovery.py
# Generated by /adapt-method skill

import scanpy as sc
import json

# Load data
data_path = "{DATA_PATH}"
adata = sc.read_h5ad(data_path)

print("=== DATA DISCOVERY REPORT ===")
print(f"Cells: {adata.n_obs}")
print(f"Features: {adata.n_vars}")

print("\n=== LAYERS ===")
print(f"Available layers: {list(adata.layers.keys())}")

print("\n=== METADATA ===")
print(f"obs columns: {list(adata.obs.columns)}")
print(f"var columns: {list(adata.var.columns)}")

# Sample structure
if 'sample' in adata.obs.columns:
    print("\n=== SAMPLE STRUCTURE ===")
    print(adata.obs['sample'].value_counts())

# Save summary
discovery_results = {
    'n_cells': int(adata.n_obs),
    'n_features': int(adata.n_vars),
    'layers': list(adata.layers.keys()),
    'obs_columns': list(adata.obs.columns),
    'var_columns': list(adata.var.columns)
}
with open("{OUTPUT_DIR}/data_discovery_results.json", "w") as f:
    json.dump(discovery_results, f, indent=2)
print(f"\nResults saved to: {OUTPUT_DIR}/data_discovery_results.json")
```

### Step 2.2: Present Script for Review

Show the generated script to the user:

```markdown
I've generated a data discovery script. Here's what it will do:
1. Load your data from `{data_path}`
2. Extract basic statistics (cells, features, assays)
3. Identify metadata columns and sample structure
4. Save results to `{output_dir}/data_discovery_results.rds`

**Script location:** `{project_dir}/{method}_adaptation/scripts/01_data_discovery.R`

Would you like me to run this script?
```

### Step 2.3: Execute Upon Approval

Run the script:
```bash
conda run -n <env_name> Rscript {script_path}
```

Capture and parse the output.

### Step 2.4: Generate Data Discovery Report

Create `01_data_discovery.md`:

```markdown
---
phase: data_discovery
method: {method}
project: {project}
data_path: {data_path}
executed: {date}
---

# Data Discovery Report

## Dataset Overview

| Metric | Value |
|--------|-------|
| Total cells | {n_cells} |
| Total features | {n_features} |
| Data format | {format} |
| Assays/Layers | {assays} |

## Metadata Structure

Available columns:
{metadata_columns}

## Sample Structure

{sample_table}

## Results Saved

- Discovery results: `data_discovery_results.rds`
```

---

## Phase 3: Method-Specific EDA

### Step 3.1: Determine Required Diagnostics

Read the method's knowledge base files:
1. `fitness_assessment.md` - What considerations were identified?
2. `code.md` - What are the input requirements?
3. `theory.md` - What assumptions should be checked?
4. `concept.md` - What limitations apply?

Diagnostic categories to consider:
- Required input format / structure (does the data have what the method expects?)
- Per-feature distributions (sparsity, expected shape — bimodal, log-normal, etc.)
- Sample / batch metadata required by the method
- Method-specific assumptions from `theory.md` and `concept.md`

### Step 3.2: Generate EDA Script

Create a method-specific EDA script that checks the relevant diagnostics. The
script template depends on the method type, language, and input format.

The script should:
1. Load the data
2. Verify required input structure (assays, layers, metadata columns)
3. Compute method-relevant diagnostics (per-feature distributions, sparsity,
   batch composition, expected vs observed structure)
4. Save structured results (`.rds` for R, `.json` for Python) for downstream
   inspection without re-running the script
5. Print a clear summary to stdout

Save to `{project_dir}/{method}_adaptation/scripts/02_eda_{method}.{R|py}`.

Use the method's `code.md` to identify which diagnostics are most informative
— e.g., a normalization method needs distribution checks; an integration method
needs batch composition; a classification method needs reference compatibility.

### Step 3.3: Present and Execute

Same pattern as Phase 2:
1. Show script to user
2. Explain what it will check
3. Execute upon approval
4. Capture results

### Step 3.4: Generate EDA Report

Create `02_eda_report.md` with method-specific findings. The structure depends
on the method type, but should always include:

```markdown
---
phase: eda
method: {method}
project: {project}
executed: {date}
---

# Method-Specific EDA: {method}

## {Diagnostic category 1 — e.g., "Feature Panel Check" / "Sample Structure"}

| {Feature/Sample} | {Stat 1} | {Stat 2} | Status |
|------------------|----------|----------|--------|
| {item}           | {value}  | {value}  | {OK / WARN / FAIL} |

## Compatibility Notes

Based on EDA:
- {Specific finding tied to method requirements — e.g., "Feature X has
   {N}% zero rate, exceeds method's documented threshold"}
- {Cross-reference any project context constraint that surfaces here}
- {Confirm whether structural requirements are met (sample column, batch metadata, etc.)}

## Results Saved

- EDA results: `eda_results.{rds|json}`
```

---

## Phase 4: Preliminary Method Run

### Step 4.1: Configure Method Parameters

Based on EDA findings and knowledge base recommendations, determine parameters.

Read from:
- `fitness_assessment.md` → Configuration Recommendations section
- `code.md` → Key Parameters table
- EDA results → Adjust for actual data characteristics

Build a parameter dict / list whose values reflect:
- Method defaults from `code.md`'s Key Parameters table
- Project-specific overrides surfaced by EDA (e.g., excluding features that
  fail a quality check, using sample-size-appropriate hyperparameters)
- Any configuration recommendations from `fitness_assessment.md`

Each non-default parameter should have a comment naming the EDA finding or
project-context constraint that drove the choice.

### Step 4.2: Subset Data for Preliminary Run

To ensure fast iteration and reduce risk, run on a subset:

```r
# Subset strategy: random sample of cells, all samples represented
set.seed(42)
n_subset <- min(5000, ncol(obj))  # Max 5000 cells
subset_idx <- sample(1:ncol(obj), n_subset)
obj_subset <- obj[, subset_idx]
```

### Step 4.3: Generate Preliminary Run Script

Generate a script that loads the data, subsets it, runs the method with the
configured parameters, saves results, and prints a basic summary. Pull the
exact API from the method's `code.md`. The script structure (R or Python)
follows the method's language. General template:

```{R or python}
# 03_run_{method}_preliminary.{R|py}
# Preliminary run of {method} on data subset

# 1. Imports / library loads (from code.md dependencies)

# 2. Load data from {DATA_PATH}

# 3. Subset (set.seed(42); n_subset = min(5000, n_cells))
#    Subset strategy: random across cells, all samples represented

# 4. Prepare input in the format the method expects (from code.md inputs)

# 5. Run the method with the parameters configured in Step 4.1

# 6. Save results to {OUTPUT_DIR}/preliminary_results.{rds|h5ad|json}

# 7. Print a basic validation summary (output dimensions, key statistics)
```

### Step 4.4: Present and Execute

Show user what will be run, including the configured parameters and their
rationale (from EDA findings + project context). Ask for approval before
executing.

### Step 4.5: Execute and Capture Results

```bash
conda run -n <env_name> {Rscript|python} {script_path} 2>&1 | tee {output_dir}/preliminary_run.log
```

### Step 4.6: Generate Preliminary Results Report

Create `03_preliminary_results.md`:

```markdown
---
phase: preliminary_run
method: {method}
project: {project}
executed: {date}
subset_size: {n}
---

# Preliminary Results: {method}

## Run Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| {param}   | {value} | {why this value, citing EDA or project context} |

## Results Summary

- **Status**: ✅ Completed successfully | ❌ Failed
- **Runtime**: {runtime}
- **Output dimensions / structure**: {what was produced}

## Observations

{What the preliminary run revealed — anything unexpected, anything that
 confirms or challenges the configuration choices}

## Saved Artifacts

| File | Description |
|------|-------------|
| `preliminary_results.{rds|h5ad|json}` | Method output on subset |
| `preliminary_run.log` | Full execution log |

## Next Steps

1. [ ] Review output quality
2. [ ] Run on full dataset with same parameters (or adjusted based on observations)
3. [ ] Proceed to downstream analysis
```

---

## Phase 5: Adaptation Summary

### Step 5.1: Compile All Findings

Create `04_adaptation_summary.md`:

```markdown
---
method: {method}
project: {project}
completed: {date}
status: preliminary_complete
---

# Adaptation Summary: {Method} for {Project}

## Overview

This document summarizes the adaptation of {Method} to your dataset.

## Environment

- **Conda environment**: {env_name}
- **Language**: {R/Python}
- **Key packages**: {packages_verified}

## Data Characteristics

| Metric | Value |
|--------|-------|
| Total cells | {n_cells} |
| Features | {n_features} |
| Samples | {n_samples} |
| Data format | {format} |

## Method Configuration

Based on EDA and knowledge base recommendations:

```{language}
{final_configuration_code}
```

## Preliminary Results

- **Subset size**: {subset_size} cells
- **Status**: {success/failed}
- **Key observations**: {observations}

## Saved Artifacts

All outputs saved to: `projects/{project}/{method}_adaptation/`

| Phase | File | Description |
|-------|------|-------------|
| Discovery | `data_discovery_results.rds` | Basic data stats |
| EDA | `eda_results.rds` | Method-specific diagnostics |
| Preliminary | `preliminary_results.rds` | Normalized subset |

## Scripts for Full Run

Ready-to-use scripts:
1. `scripts/01_data_discovery.R` - Data exploration
2. `scripts/02_eda.R` - Method-specific EDA
3. `scripts/03_run_{method}_preliminary.R` - Preliminary run (modify for full)

## Recommendations

{recommendations_based_on_all_findings}

## Integration Notes

This adaptation report can be used by `/finalize-workflow` to:
- Combine with other method adaptations
- Generate complete analytical pipeline
- Validate workflow against real preliminary results

---

*Generated by `/adapt-method` skill on {date}*
```

---

## Output Structure

After running this skill, the project folder will contain:

```
projects/{project}/
├── {method}_fitness_assessment.md      # From /evaluate-fit (if run)
└── {method}_adaptation/
    ├── 00_environment_check.md
    ├── 01_data_discovery.md
    ├── 02_eda_report.md
    ├── 03_preliminary_results.md
    ├── 04_adaptation_summary.md
    ├── scripts/
    │   ├── 01_data_discovery.R
    │   ├── 02_eda_{method}.R
    │   └── 03_run_{method}_preliminary.R
    └── results/
        ├── data_discovery_results.rds
        ├── eda_results.rds
        ├── preliminary_results.rds
        └── preliminary_run.log
```

---

## Example Usage

```
/adapt-method <method-name>
```

The skill will then:
1. Ask about conda environment
2. Ask for data path
3. Generate and run data discovery
4. Generate and run method-specific EDA
5. Configure and run preliminary analysis
6. Produce comprehensive adaptation report

---

## Method-Specific EDA Templates

The skill should include EDA templates for different method types. These are determined by reading the method's code.md and concept.md.

### Normalization Methods (ADTnorm, SCTransform, etc.)
- Distribution checks per feature
- Zero inflation rates
- Batch structure

### Integration Methods (Harmony, Seurat Integration, etc.)
- Batch composition overlap
- Cell type balance across batches
- PCA variance by batch

### Clustering Methods (Seurat, Scanpy, etc.)
- Dimensionality reduction quality
- Cluster stability metrics
- Marker gene detection

### Annotation Methods (SingleR, Azimuth, etc.)
- Reference compatibility
- Feature overlap
- Confidence score distributions

---

## Error Handling

### Environment Issues
- Missing conda: Provide installation instructions
- Missing packages: List install commands
- Wrong R/Python version: Warn and suggest alternatives

### Data Issues
- Path not found: Ask for correct path
- Unrecognized format: Ask user to specify
- Corrupted file: Report error and suggest checks

### Method Issues
- Missing required columns: Explain what's needed
- Incompatible data structure: Suggest preprocessing
- Method failure: Capture error log, suggest fixes

---

## Tips

- Always run `/evaluate-fit` first to understand compatibility
- Start with preliminary runs on subsets before committing to full analysis
- Review generated scripts before execution
- Keep the adaptation reports for workflow integration later
- If preliminary run fails, check the log file for detailed errors

---

*This skill bridges the gap between method knowledge and actual implementation, producing real preliminary results that validate your analytical approach.*
