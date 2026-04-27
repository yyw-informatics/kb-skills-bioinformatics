---
name: harmonize
description: "Harmonize all knowledge base documents for a method - ensure consistency, remove redundancy, add cross-references"
---

# Codex Adapter

This adapter is generated from `skills/harmonize/SKILL.md`. Edit the source Claude skill, then run `python3 scripts/sync_codex_skills.py` to refresh the Codex mirror.

Preserve the shared workflow contract: `knowledge_base/`, `projects/<name>/literature/`, `fitness_summary.md`, `analysis_plan.md`, audit files, and progress files remain the expected outputs.

## Claude-to-Codex Term Map

- `/skill-name` examples mean `$skill-name` or explicit plugin/skill invocation in Codex.
- `Task` / `TaskOutput` mean delegated/fresh-agent execution when available; otherwise run phases sequentially and verify files.
- `AskUserQuestion` means ask the user directly when required.
- `WebFetch` / `WebSearch` mean Codex web/search tools when available.

## Source Skill Instructions

# Harmonize Skill

This skill is the final step in building a knowledge base entry. It reads all generated documents (concept.md, theory.md, code.md, figures.md) and harmonizes them into a cohesive, consistent, and well-cross-referenced set.

## Prerequisites

Before running this skill, the following files should exist:
- `knowledge_base/<method>/concept.md` (from `/read-paper`)
- `knowledge_base/<method>/theory.md` (from `/understand-theory`)
- `knowledge_base/<method>/code.md` (from `/learn-code`)
- `knowledge_base/<method>/figures.md` (from `/extract-figures`) — optional; absent when the build was run with `--skip-figures`

At minimum, `concept.md` and one other file should exist. The skill works with whatever files are available — do not stub out a missing `figures.md`, do not warn about it, and skip every figures.md row, column, and cross-reference step below.

## Workflow

### Step 1: Inventory Available Documents

Check which files exist for this method:

```bash
ls knowledge_base/<method>/*.md
```

Read all available markdown files to understand the current state.

### Step 1.5: Validate YAML Frontmatter

Before harmonizing, verify each file's YAML frontmatter parses and contains the expected fields. The cross-reference and metadata steps depend on this.

For each file, extract the frontmatter (between the `---` delimiters at the top) and check:

| File | Required fields |
|------|-----------------|
| concept.md | `name`, `journal`, `doi`, `task`, `modality` |
| theory.md | `name`, `theory_type` |
| code.md | `name`, `language`, `repository` (or `code_status: no_repo`) |
| figures.md | `name`, `total_main_figures` |

If any file lacks frontmatter, has malformed YAML (unbalanced quotes, broken indentation), or is missing required fields:
- Stop and surface the issue with file path + missing/broken field
- Ask the user whether to skip that file or have them fix it manually
- Do NOT auto-add fields with placeholder values — that masks the underlying problem

### Step 2: Build Terminology Index

Create a working index of key terms, concepts, and notation used across all documents:

| Term/Concept | concept.md | theory.md | code.md | figures.md |
|--------------|------------|-----------|---------|------------|
| Example term | "peak detection" | "landmark identification" | "findPeaks()" | "peak locations" |

Identify inconsistencies:
- Same concept with different names
- Same term used for different concepts
- Notation mismatches (e.g., `X` vs `x` vs `\mathbf{X}`)

### Step 3: Establish Canonical Terminology

Define the authoritative term for each concept:

| Concept | Canonical Term | Source | Variations to Update |
|---------|---------------|--------|---------------------|
| Detecting peaks in density | "peak detection" | concept.md | "landmark identification" → "peak detection" |

Priority order for canonical terms:
1. **Paper terminology** (what authors call it)
2. **Code terminology** (function/variable names)
3. **Common field usage** (standard bioinformatics terms)

### Step 4: Identify Cross-Reference Opportunities

Find places where documents should reference each other:

#### concept.md → other files
- "Key Approach" section → link to `theory.md` for mathematical details
- "Input/Output" section → link to `code.md` for implementation specifics
- Benchmarking mentions → link to `figures.md` for visualization

#### theory.md → other files
- Algorithm steps → link to `code.md` for implementation
- Equations → link to `figures.md` if figure illustrates the concept
- Assumptions → link to `concept.md` for biological context

#### code.md → other files
- Theory-to-Code mapping → link to specific `theory.md` sections
- Function purposes → link to `concept.md` for biological motivation
- Output formats → link to `figures.md` for visualization examples

#### figures.md → other files
- Data sources → link to `code.md` for data processing
- Methods shown → link to `theory.md` for equations
- Biological interpretation → link to `concept.md`

### Step 5: Identify Redundancy

Find content that appears in multiple files:

| Content | Appears In | Action |
|---------|------------|--------|
| Full algorithm description | concept.md, theory.md | Keep detail in theory.md, summarize in concept.md with link |
| Parameter defaults | theory.md, code.md | Keep in code.md, reference from theory.md |
| Method overview | All files | Keep only in concept.md, other files reference it |

Redundancy resolution principles:
- **concept.md**: High-level overview, biological context, use cases
- **theory.md**: Mathematical details, equations, statistical framework
- **code.md**: Implementation specifics, parameters, functions
- **figures.md**: Visual representations, data shown, reproduction specs

### Step 6: Apply Harmonization

Make the following edits across all files:

#### 6a: Terminology Standardization
- Update all terminology variations to canonical terms
- Ensure mathematical notation is consistent (same symbol for same variable)
- Standardize formatting (e.g., function names always in `backticks`)

#### 6b: Add Cross-References
Add links between documents using this format:
```markdown
For mathematical details, see [Theory: Peak Detection Algorithm](theory.md#peak-detection-algorithm).

Implementation details are documented in [Code: findPeaks function](code.md#findpeaks).

This concept is visualized in [Figure 1B](figures.md#panel-b-peak-detection).
```

#### 6c: Consolidate Redundancy
- Replace duplicated content with cross-references
- Keep detailed content in the most appropriate file
- Add brief summaries with "see X for details" links

#### 6d: Update YAML Metadata
Ensure all files have consistent metadata:
- Same method name across all files
- Matching version numbers
- Consistent date formats
- Add `harmonized: <date>` field to track this step

### Step 7: Create Navigation Index

Add a navigation section to each file (at the top, after YAML frontmatter):

```markdown
## Quick Navigation

| Document | Purpose |
|----------|---------|
| [concept.md](concept.md) | Overview, motivation, use cases, limitations |
| [theory.md](theory.md) | Mathematical formulation, algorithms, equations |
| [code.md](code.md) | Implementation, functions, parameters, dependencies |
| [figures.md](figures.md) | Figure documentation, visual specifications |
```

### Step 8: Verify and Refine

Perform a final review of all harmonized documents:

#### Consistency Check
- [ ] Same term used for same concept across all files
- [ ] Mathematical notation matches between theory.md and code.md
- [ ] Function names in code.md match those referenced in other files
- [ ] Figure references in other files match actual figure numbers

#### Cross-Reference Validation
- [ ] All cross-reference links are valid (correct file, correct section)
- [ ] No orphaned sections (everything connects to something)
- [ ] Bidirectional references where appropriate (A→B and B→A)

#### Redundancy Resolution
- [ ] No significant content duplication remains
- [ ] Each file has a clear, distinct purpose
- [ ] Summaries with links replace duplicated details

#### Flow Check
- [ ] Reader can start at concept.md and navigate to any detail
- [ ] Each file stands alone but benefits from cross-references
- [ ] Navigation index is accurate and helpful

#### Final Polish
- [ ] Consistent heading levels and formatting
- [ ] No broken markdown syntax
- [ ] All placeholder text removed
- [ ] Dates and versions are current

Make final corrections, then confirm completion.

## Cross-Reference Format Guide

Use consistent link formats:

### Internal Section Links
```markdown
See [Section Name](#section-name) below.
```

### Cross-Document Links
```markdown
See [Document: Section](document.md#section-name).
```

### Specific Examples
```markdown
# In concept.md:
The warping function (see [Theory: Warping Function](theory.md#warping-function)) transforms...

# In theory.md:
This equation is implemented in [Code: warpFunction()](code.md#warpfunction).

# In code.md:
This function implements the algorithm described in [Theory: Algorithm Steps](theory.md#algorithm-steps).

# In figures.md:
This panel visualizes the concept explained in [Concept: Peak Detection](concept.md#key-approach).
```

## Output

Updates all existing knowledge base files with:
- Consistent terminology
- Cross-references between documents
- Reduced redundancy
- Navigation index
- `harmonized: <date>` metadata field

### Before/After Example

**Before (concept.md):**
```markdown
## Key Approach

ADTnorm uses landmark registration to align peaks and valleys...
[Full algorithm description repeated from theory.md]
```

**After (concept.md):**
```markdown
## Key Approach

ADTnorm uses landmark registration to align peaks and valleys in ADT density distributions. The method identifies negative and positive expression peaks, then applies a warping function to align them across samples.

For the complete mathematical formulation, see [Theory: Core Model](theory.md#core-model--algorithm). Implementation details are in [Code: ADTnorm_normalize()](code.md#adtnorm_normalize).
```

## Usage Examples

```
/harmonize ADTnorm
/harmonize Seurat
/harmonize scanpy
```

## Tips

- Run this skill after all other documentation skills are complete
- The skill is idempotent - running it multiple times won't cause issues
- If new content is added to any file later, re-run `/harmonize` to update cross-references
- Pay special attention to notation consistency between theory.md and code.md
- When in doubt about canonical terminology, prefer the original paper's language

## Common Inconsistency Patterns

| Pattern | Example | Resolution |
|---------|---------|------------|
| Synonym usage | "normalize" vs "standardize" | Pick one, update all |
| Case variations | "UMAP" vs "Umap" vs "umap" | Use official capitalization |
| Notation drift | `X` in theory, `x` in code | Align with paper notation |
| Abbreviation expansion | "ADT" vs "antibody-derived tag" | Define once, abbreviate after |
| Function name formats | `find_peaks` vs `findPeaks` | Match actual code |
