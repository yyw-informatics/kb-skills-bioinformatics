# Worked example: CITE-seq study

This is the project the workflow was originally built for. It illustrates how the skills compose and what realistic outputs look like. Biological specifics, numerical values, and experimental details have been genericized.

## The project

- **Question**: How do rare immune cell populations differ between two conditions in a defined cohort?
- **Data**: X human donors (split across two conditions) × 2 timepoints, totaling P samples (some donors have technical replicates at both timepoints)
- **Assay**: CITE-seq (paired RNA + ADT protein) with a small ADT panel focused on the target cell populations; one ADT marker turned out to be non-functional in this dataset and had to be treated as uninformative, effectively reducing the panel. Cells were enriched for the target populations and recombined at a non-physiological ratio before sequencing, so composition is intentionally non-physiological.

These project specifics are exactly the kind of details that make literature findings hard to apply directly — and exactly what the workflow is designed to surface.

## Step 1: build the method KB

11 methods were processed with `/build-knowledge`:

| Layer | Methods |
|-------|---------|
| ADT normalization | dsb, ADTnorm |
| Joint embedding | totalVI, MrVI |
| Cell classification | ThresholdR, MMoCHi |
| Compositional / DA | scCODA, milo |
| Differential expression | muscat, scglmmr |
| Reference mapping | scArches |

Plus three ecosystem indexes via `/index-docs`: scanpy, scvi-tools, seurat.

Total time: ~30 min of agent runtime per method. Most ran without intervention; a few needed one revision pass on `theory.md`.

## Step 2: write the project context

Drafted `projects/<project_name>/context.md` from the [template](../../templates/project-context.md). Critical sections that drove downstream decisions:

```markdown
## 1) Dataset & design (facts)
- **Groups**: condition_A vs condition_B.
- **Assay**: CITE-seq (paired RNA + cell-surface protein).
- **Biology**: target rare immune populations enriched from human samples.
- **Design**: X donors (split across the two conditions) × 2 timepoints.
- **Samples**: P total; libraries split into GEX + ADT per sample.
- **Technical replicates**: Donor_A* and Donor_B* have replicate_1 / replicate_2 at both timepoints.

## 2) Wet-lab enrichment (analysis-relevant)
Multi-step enrichment for the target populations, recombined before sequencing at a non-physiological ratio.

## 3) ADT panel (sequenced features)
Small ADT panel of cell-type-defining markers. One marker (Marker_X, corresponds to GENE_X RNA) is flagged status: non-functional and treated as uninformative throughout downstream analysis.
```

Marking Marker_X as non-functional propagates through every downstream skill — they all substitute GENE_X RNA where the paper-recommended gating uses Marker_X protein.

## Step 3: mine the biology literature

Biology papers on the target cell populations and the two conditions were mined in batches:

```bash
/mine-paper --all projects/<project_name>/context.md \
            --project=<project_name> --dir=papers/
```

Outcomes broke down roughly into HIGH / MODERATE / LOW / NOT USEFUL / UNABLE TO ASSESS verdicts. A NOT USEFUL verdict (e.g., a study in a tissue compartment that didn't match) is a feature, not a failure — it stops at one paragraph of explanation rather than padding a useless evidence file.

Each HIGH paper produced an evidence file with directly-actionable items (gene lists ready for `sc.tl.score_genes()`, marker tables annotated against the user's ADT panel) and hypothesis-generating items (predictions to test in the data).

**Example evidence artifact** — one paper's evidence extracted a canonical surface marker panel for the target cell subtypes, annotated against the project's functional ADT panel:

```markdown
### Consensus Surface Marker Panel for the Target Cell Family

| Marker     | Type_1 | Type_2 | Type_3 | Type_4 |
|------------|--------|--------|--------|--------|
| Marker_A   | +      | +      | +      | +      |
| Marker_B   | +/-    | -      | -      | -      |
| Marker_C   | +      | +      | -      | +/-    |
| Marker_X   | -      | +      | +      | +      |
| Marker_Y   | -      | -      | +      | -      |
```

The evidence file flags the non-functional marker as uninformative for this project (per `context.md`) and recommends the corresponding RNA as the substitute gating signal.

## Step 4: synthesize across papers

```bash
/synthesize-literature projects/<project_name>/context.md \
                       --project=<project_name>
```

**What the synthesis produced** (counts and content genericized):

```markdown
## Overview

This synthesis integrates findings from many papers spanning scRNA-seq, CITE-seq, flow
cytometry, spectral flow cytometry, bulk RNA-seq, and review articles covering the target
cell biology and both study conditions.

Core consensus established:
 (1) the identity of one cell subtype is actively debated — some studies find no genuine
     instance of it in the target compartment, others identify a distinct cluster
 (2) frequencies of some target subtypes shift with one of the conditions while others
     remain stable
 (3) the broken ADT marker in this panel can be effectively replaced by its corresponding
     RNA expression, as validated by multiple independent studies
 (4) a known signaling axis directly modulates one of the target subtypes
 (5) a universal cell-state marker (associated with the condition under study) appears
     consistently across the target cell family

| Metric                          | Count |
|---------------------------------|-------|
| Papers synthesized              | P     |
| HIGH / MODERATE / LOW relevance | … / … / … |
| Consensus marker genes          | M     |
| Consolidated gene signatures    | S     |
| Multi-paper hypotheses          | H1    |
| Novel cross-paper hypotheses    | H2    |
| Universal translation constraints | C   |
```

Conflicts (e.g., whether a particular subtype exists as a distinct population in the target compartment) are framed as research opportunities the dataset can address.

## Step 5: evaluate methods against the project

```bash
/evaluate-fit --all projects/<project_name>/context.md \
              --project=<project_name>
```

**What the fitness summary produced:**

```markdown
| Method     | Fit Score | Primary Strength                                              | Main Concern                                                     |
|------------|-----------|---------------------------------------------------------------|------------------------------------------------------------------|
| totalVI    | Good      | Purpose-built joint RNA+protein model for CITE-seq            | Few functional ADT markers limits protein benefit                |
| muscat     | Good      | Gold-standard pseudobulk DE with proper multi-donor inference | RNA-only; no ADT support                                         |
| scglmmr    | Good      | Purpose-built for CITE-seq with mixed effects                 | Small donor cohort pushes mixed-model limits                     |
| milo       | Good      | Cluster-free differential abundance for rare subtypes         | RNA-only; ADT not natively integrated                            |
| ThresholdR | Good      | GMM-based ADT denoising with flow-cytometry-style gating      | Very small panel limits reference-marker selection               |
| ADTnorm    | Good      | Interpretable ADT normalization                               | Small panel untested                                             |
| dsb        | Moderate  | Exact modality match; ambient noise correction                | No isotype controls; too few functional markers for Step II GMM  |
| MMoCHi     | Moderate  | Hierarchical CITE-seq classification mirrors flow gating      | Functional panel far below validated panel size (270+)           |
| MrVI       | Moderate  | Powerful cluster-free DE and DA with sample-level modeling    | RNA-only; no ADT integration; small cohort                       |
| scCODA     | Moderate  | Bayesian compositional analysis works with low replicates     | Enrichment strategy distorts compositions fundamentally          |
| scArches   | Moderate  | Reference mapping with protein imputation potential           | No suitable reference atlas likely exists for the target system  |
```

Each per-method assessment also produced a `<method>_fitness_assessment.md` with a Task Alignment table mapping each project need to a method capability (e.g., for totalVI: "joint RNA+protein analysis ✓", "handling non-functional ADT marker ⚠️ — user must exclude before model fitting").

Key insight surfaced: methods validated on large CITE-seq panels (dsb Step II, MMoCHi) underperform on a small functional panel. The fitness summary recommends a hybrid ADT+RNA classification approach as a workaround.

## Step 6: design the analysis

```bash
/design-analysis projects/<project_name>/literature/0_synthesis_literature.md \
                 projects/<project_name>/context.md \
                 --project=<project_name>
```

Produced `analysis_plan.md` — a 5-phase ordered pipeline with:
- Each hypothesis from the synthesis mapped to a specific method, function, and code template
- Project constraints (non-functional marker, enrichment strategy, small cohort) propagated into every phase
- Real Python code blocks using actual gene lists from the synthesis

**Pipeline status after execution** (snapshot from `analysis_plan.md`):

```markdown
| Phase                          | Status     | Scripts                                                 |
|--------------------------------|------------|---------------------------------------------------------|
| Phase 1: Data Processing       | COMPLETED  | step01_qc.py, 01_dsb_normalization.R,                   |
|                                |            | 02_thresholdr_gating.R, step04_clr_protein.py,          |
|                                |            | step05_rna_normalization.py                             |
| Phase 2: Embedding             | COMPLETED  | step06_totalvi.py, step07_scvi.py,                      |
|                                |            | step08_embedding_comparison.py                          |
| Phase 3: Classification        | COMPLETED  | step09_adt_gating.py through step14_save_and_export.py  |
| Phase 4: Hypothesis Testing    | TODO       | scripts scaffolded, not yet executed                    |
| Phase 5: Discovery             | TODO       | metadata only in implementation plan                    |

Key results from completed phases:
- A large pool of cells classified from CellRanger libraries (donors × timepoints)
- Primary embedding: totalVI (selected over scVI at Step 8)
- Major populations identified across the target cell family, with several subtype variants
- Contaminants removed
```

## What the workflow did well

1. **Caught the non-functional marker trap automatically.** Every paper that referenced gating on the affected marker got a footnote in its evidence file noting the marker is uninformative for this project and recommending the corresponding RNA signal. The fitness summary flagged ThresholdR as Moderate (not Good) because of the panel-size constraint. The analysis plan substitutes the gate everywhere it appears.

2. **Surfaced a research opportunity.** The synthesis flagged that HIGH-relevance papers disagreed on whether a particular subtype exists as a distinct population in the target compartment. The dataset has multimodal markers that can address this directly — a finding that would have been buried in two separate evidence files.

3. **Made cross-species data explicit.** Mouse papers were kept separate from the human consensus, but their hypotheses fed into the "novel cross-paper" section with explicit translation caveats.

## What needed manual intervention

- One method's `theory.md` failed `/review-knowledge` twice; the third pass with focused refinement guidance ("focus on missing notation table") passed.
- The analysis plan's Phase 1 needed a manual edit to reference a sample-specific QC threshold not captured by the project context.
- The mouse paper authors' surnames showed up in the design-analysis "cross-species" section — fine, but worth knowing the skill names them rather than just labeling the data.

## Total cost (approximate)

- Method KB: ~30–45 min wall-clock for 11 methods running in parallel as background agents (each ~30 min of agent runtime)
- Literature mining: ~25 minutes for the initial batch of papers in parallel; incremental for later additions
- Synthesis: ~5 minutes per regeneration (use `--update` for incremental merges)
- Fitness evaluation: ~10 minutes for 11 methods in parallel
- Design analysis: ~5 minutes

The KB layer is reusable for any future CITE-seq project — that's the multiplicative payoff.
