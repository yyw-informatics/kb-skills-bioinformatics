---
name: extract-figures
description: Extract and document figures from papers with detailed descriptions for AI reproducibility
argument-hint: [method-name]
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion
---

# Extract Figures Skill

This skill analyzes figures from scientific papers and creates detailed documentation that would allow an AI agent to recreate them. Focus is on main paper figures which tell the core story.

## Prerequisites

Before running this skill:
1. `concept.md` must exist (from `/read-paper`)
2. Main paper PDF must be available

## Workflow

### Step 1: Locate the Paper

Find the main paper PDF:
```bash
# Check for PDF in knowledge base
ls knowledge_base/<method>/*.pdf

# Or check concept.md for paper location
grep -i "pdf\|paper" knowledge_base/<method>/concept.md
```

### Step 2: Read and Analyze Figures

Read the paper PDF and for each figure, extract:

1. **Figure identifier** (Figure 1, Figure 2a, etc.)
2. **Figure type** (density plot, heatmap, UMAP, scatter plot, bar chart, box plot, workflow diagram, etc.)
3. **Axes definitions**:
   - X-axis: variable, units, scale (linear/log)
   - Y-axis: variable, units, scale
   - Color axis (if applicable): what it represents
4. **Data shown**:
   - What data/samples are plotted
   - Number of conditions/groups
   - Any subsetting or filtering applied
5. **Visual elements**:
   - Color scheme (categorical palette, gradient, specific colors if notable)
   - Annotations (arrows, labels, statistical indicators)
   - Panel layout (if multi-panel)
6. **Scientific objective**: What question does this figure answer?
7. **Key findings**: What conclusion should the reader draw?

### Step 3: Document Figure Details

Scientific figures typically contain multiple panels (A, B, C, D...) that together tell a story. Document at two levels:

1. **Figure level**: Overall narrative and how panels connect
2. **Panel level**: Detailed specifications for each panel

#### Template for Multi-Panel Figures

```markdown
### Figure X: [Overall Figure Title]

**Panel Layout:** [rows × cols] or [custom arrangement description]

**Narrative:** [How do the panels flow together? What story does this figure tell?]

---

#### Panel A: [Panel Title]

**Type:** [density plot | heatmap | UMAP | scatter | bar | box | line | workflow | other]

**Axes:**
- X-axis: [variable name] ([units]) - [scale type]
- Y-axis: [variable name] ([units]) - [scale type]
- Color: [what color represents] - [palette type/specific colors]

**Data:**
- Source: [what data is being visualized]
- Samples/conditions: [number and description]
- Filtering: [any data subsetting]

**Visual Elements:**
- [Legends, annotations, reference lines, error bars, etc.]

**Message:** [What does this specific panel show?]

---

#### Panel B: [Panel Title]

**Type:** [...]

[Continue for each panel...]

---

**Figure Objective:** [What scientific question does the complete figure address?]

**Key Findings:** [What should the reader conclude from this figure as a whole?]

**Reproduction Notes:** [Algorithms, parameters, thresholds, software used]
```

#### Template for Single-Panel Figures

```markdown
### Figure X: [Descriptive Title]

**Type:** [density plot | heatmap | UMAP | scatter | bar | box | line | workflow | other]

**Axes:**
- X-axis: [variable name] ([units]) - [scale type]
- Y-axis: [variable name] ([units]) - [scale type]
- Color: [what color represents] - [palette type]

**Data:**
- Source: [what data is being visualized]
- Samples/conditions: [number and description]
- Filtering: [any data subsetting]

**Visual Elements:**
- [List key visual features: legends, annotations, reference lines, etc.]

**Objective:** [What scientific question does this figure address?]

**Key Findings:** [What should the reader conclude from this figure?]

**Reproduction Notes:** [Any specific details needed to recreate: algorithms, parameters, thresholds]
```

#### Panel Relationship Patterns

Common ways panels relate to each other (non-exhaustive — name additional patterns as you encounter them):

| Pattern | Description | Example |
|---------|-------------|---------|
| **Sequential** | A→B→C shows a process | Raw data → Processing → Result |
| **Comparative** | Same visualization, different conditions | Method A vs Method B vs Method C |
| **Zoom** | Overview then detail | Full dataset → Subset → Single sample |
| **Multi-metric** | Same data, different measurements | Accuracy, Precision, Recall |
| **Before/After** | Pre- and post-processing | Unnormalized vs Normalized |
| **Temporal** | Same entity over time | Cells profiled at multiple timepoints |
| **Hierarchical** | Broad classification → progressive detail | All cells → cluster → subset markers |
| **Correlation** | Pairwise relationships | Correlation matrix, pairwise scatter |
| **Network** | Entities + relationships | Cell-cell communication, gene regulatory |

### Step 4: Categorize Figures

Group figures by their purpose:

| Category | Description | Typical Figure Types |
|----------|-------------|---------------------|
| **Workflow** | Method overview/pipeline | Flow diagrams, schematics |
| **Demonstration** | Show the method working | Before/after comparisons, density plots |
| **Benchmarking** | Compare to other methods | Bar charts, box plots, heatmaps |
| **Validation** | Ground truth comparison | Scatter plots, confusion matrices |
| **Application** | Real-world use cases | UMAPs, heatmaps, biological results |

### Step 5: Create figures.md

Generate `knowledge_base/<method>/figures.md`:

### Step 6: Verify and Refine

Re-read the generated `figures.md` and perform an editorial review:

#### Completeness Check
- [ ] All main figures documented (check paper for total figure count)
- [ ] All panels within each figure documented (A, B, C, D...)
- [ ] Figure Summary table covers all figures
- [ ] Panel Index table covers all panels
- [ ] Every panel has: type, axes, data, visual elements, message

#### Accuracy Check
- [ ] Figure/panel numbers match the paper exactly
- [ ] Axis labels and units are accurate
- [ ] Data sources described match what's shown
- [ ] Color descriptions match actual figure colors
- [ ] Statistical annotations (p-values, significance) are correct

#### Reproducibility Check
- [ ] Could an AI recreate this figure from the description alone?
- [ ] All algorithms/parameters mentioned in reproduction notes
- [ ] Data filtering/subsetting criteria are explicit
- [ ] Software packages/versions noted where relevant

#### Flow and Clarity
- [ ] Narrative flow between panels is clear and accurate
- [ ] Panel relationship pattern is correctly identified (sequential, comparative, etc.)
- [ ] Scientific objectives are clearly stated
- [ ] Key findings align with paper's conclusions

#### Efficiency Improvements
- Consolidate repetitive panel descriptions where appropriate
- Ensure figure summaries are concise (1-2 sentences)
- Remove filler phrases from panel messages
- Standardize terminology across all panel descriptions (use consistent axis names, etc.)

#### Cross-Reference Validation
- [ ] Figure categories align with content
- [ ] Panel types match the Figure Type Reference table
- [ ] References to method concepts align with `concept.md`

Make corrections directly to the file, then proceed to generate output:

```markdown
---
name: <method>
paper: <paper reference>
total_main_figures: <count>
total_panels: <count>
last_analyzed: <date>
---

# <Method> - Figure Documentation

## Overview

### Figure Summary

| Figure | Panels | Category | Overall Message |
|--------|--------|----------|-----------------|
| Fig 1 | A-D | Workflow | Method overview and pipeline |
| Fig 2 | A-F | Demonstration | Batch effect before/after |
| Fig 3 | A-C | Benchmarking | Comparison with other methods |
| ... | ... | ... | ... |

### Panel Index

| Panel | Type | What It Shows |
|-------|------|---------------|
| Fig 1A | workflow diagram | Input data and preprocessing |
| Fig 1B | density plot | Peak detection illustration |
| Fig 1C | line plot | Warping function visualization |
| Fig 1D | density plot | Normalized output |
| Fig 2A | ridge plot | Raw ADT distributions by sample |
| Fig 2B | ridge plot | Normalized distributions |
| ... | ... | ... |

## Main Figures

### Figure 1: Method Overview and Workflow

**Panel Layout:** 2×2 grid (A-D)

**Narrative:** Panel A introduces the input data format, B shows the peak detection step,
C illustrates the warping function alignment, and D shows the final normalized output.
Together they walk through the complete ADTnorm pipeline.

---

#### Panel A: Input Data Structure
[Detailed panel description...]

#### Panel B: Peak Detection
[Detailed panel description...]

[Continue for each panel...]

---

**Figure Objective:** Provide a complete visual overview of the ADTnorm method.

**Key Findings:** ADTnorm transforms variable ADT distributions into aligned, normalized profiles.

---

### Figure 2: [Title]
[Detailed description using multi-panel template]

...

## Supplementary Figures (Key)

[Only include supplementary figures that add significant information not captured in main figures]

---

*Generated by `/extract-figures` skill on <date>*
```

## Figure Type Reference

Common figure types in bioinformatics papers:

| Type | Description | Key Elements to Document |
|------|-------------|-------------------------|
| **Density/Ridge plot** | Distribution of values | Variable, grouping, bandwidth |
| **Heatmap** | Matrix visualization | Row/col variables, clustering, color scale |
| **UMAP/t-SNE** | Dimensionality reduction | Perplexity/n_neighbors, color mapping |
| **Scatter plot** | Two variables | Both axes, point coloring, trend lines |
| **Box/Violin plot** | Distribution comparison | Groups, statistical tests shown |
| **Bar chart** | Categorical comparisons | Categories, error bars, significance |
| **Line plot** | Trends over continuous variable | X variable, multiple lines meaning |
| **Workflow diagram** | Method pipeline | Steps, decision points, inputs/outputs |
| **Sankey/Alluvial** | Flow between categories | Source/target, flow width meaning |

## Output

Creates:
- `knowledge_base/<method>/figures.md` - Comprehensive figure documentation

### Folder Structure
```
knowledge_base/<method>/
├── concept.md          # From /read-paper
├── theory.md           # From /understand-theory
├── code.md             # From /learn-code
├── figures.md          # From /extract-figures (this skill)
├── repo/               # Cloned repository
└── scripts/            # Key scripts
```

## Usage Examples

```
/extract-figures ADTnorm
/extract-figures Seurat
/extract-figures scanpy
```

## Tips

- Main figures prioritized over supplementary (main figures tell the story)
- Focus on figures that demonstrate the method's contribution
- Include enough detail that someone could recreate the figure with different data
- Note any statistical methods shown (p-values, confidence intervals)
- Document color choices if they convey meaning (e.g., red=high, blue=low)

### Multi-Panel Figure Tips

- Always document the **narrative flow** between panels (how they connect)
- Identify the **panel relationship pattern** (sequential, comparative, zoom, etc.)
- Each panel should have its own complete specification
- Note shared elements (legends, color scales) that apply across panels
- If panels share axes or scales, document this explicitly
- Panels often have implicit left-to-right or top-to-bottom reading order
