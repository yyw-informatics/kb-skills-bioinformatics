# Worked example: CITE-seq ILC/NK aging study

This is the project the workflow was originally built for. It illustrates how the skills compose and what realistic outputs look like. Numerical values, ages, and experimental specifics have been genericized — the dataset is unpublished.

## The project

- **Question**: How do circulating NK and ILC populations change with age and post-vaccine response?
- **Data**: X human donors (Y young aged A–B, Z aged C–D) × 2 timepoints (Day 0, Day N post-vaccine), totaling P samples (some donors have technical replicates at both timepoints)
- **Assay**: 10x CITE-seq (Single Cell 3' v3.1 Dual Index + Feature Barcode), small TotalSeq-B ADT panel focused on ILC/NK markers
- **Wrinkle**: one ADT marker in the panel turned out to be non-functional in this dataset and had to be treated as uninformative. Effectively a smaller panel.
- **Wrinkle 2**: cells were MACS-enriched for ILC + NK and recombined at a non-physiological ratio before sequencing. Composition is intentionally non-physiological.

These wrinkles are exactly the kind of project specifics that make literature findings hard to apply directly — and exactly what the workflow is designed to surface.

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
- **Groups**: young vs aged.
- **Assay**: 10x Chromium Next GEM Single Cell 3' v3.1 Dual Index + Feature Barcode (cell-surface protein).
- **Biology**: PBMC-derived NK + ILC–enriched cells.
- **Design**: X donors (Y young aged A–B, Z aged C–D) × Day 0 vs Day N post-vaccine.
- **Samples**: P total; libraries split into GEX + ADT per sample.
- **Technical replicates**: Donor_Y* and Donor_A* have replicate_1 / replicate_2 at both timepoints.

## 2) Wet-lab enrichment (analysis-relevant)
Two-step MACS enrichment, recombined before 10x at a non-physiological ILC:NK ratio.

## 3) CITE-seq ADT panel (sequenced features)
Small TotalSeq-B panel of ILC/NK markers. One marker (CD127) is flagged status: non-functional and treated as uninformative throughout downstream analysis.
```

Marking one marker as non-functional propagates through every downstream skill — they all substitute the corresponding RNA (IL7R for CD127) where the paper-recommended gating uses that protein.

## Step 3: mine the biology literature

Biology papers on ILC/NK biology, aging, and vaccine response were mined in batches:

```bash
/mine-paper --all projects/<project_name>/context.md \
            --project=<project_name> --dir=papers/
```

Outcomes broke down roughly into HIGH / MODERATE / LOW / NOT USEFUL / UNABLE TO ASSESS verdicts. A NOT USEFUL verdict (e.g., a study in a tissue compartment that didn't match) is a feature, not a failure — it stops at one paragraph of explanation rather than padding a useless intel file.

Each HIGH paper produced an intel file with directly-actionable items (gene lists ready for `sc.tl.score_genes()`, marker tables annotated against the user's ADT panel) and hypothesis-generating items (predictions to test in the data).

**Example intel artifact** — one paper's intel extracted the canonical surface marker panel for human ILC subsets, annotated against the project's functional ADT panel:

```markdown
### Consensus Surface Marker Panel for Human ILC Subsets

| Marker | NK (CD127-) | ILC1 (CD127-) | ILC1 (CD127+) | ILC2 | LTi | ILC3 (NKp44-) | ILC3 (NKp44+) |
|--------|-------------|---------------|---------------|------|-----|---------------|---------------|
| CD7    | +           | +             | +             | +    | +   | +             | +             |
| CD16   | +/-         | -             | -             | -    | -   | -             | -             |
| CD56   | +           | +             | -             | -    | -   | -             | +/-           |
| CD117  | -           | -             | +/-           | low  | +   | +             | +             |
| CD127  | -           | -             | +             | +    | +   | +             | +             |
| CRTH2  | -           | -             | -             | +    | -   | -             | -             |
```

The intel file flags the non-functional marker as uninformative for this project (per `context.md`) and recommends the corresponding RNA as the substitute gating signal.

## Step 4: synthesize across papers

```bash
/synthesize-literature projects/<project_name>/context.md \
                       --project=<project_name>
```

**What the synthesis produced** (counts genericized):

```markdown
## Overview

This synthesis integrates findings from many papers spanning scRNA-seq, CITE-seq, CyTOF,
flow cytometry, spectral flow cytometry, bulk RNA-seq, and review articles of human and
mouse ILC/NK biology, including antiviral defense and influenza vaccination contexts.

Core consensus established:
 (1) ILC1 identity in human blood is actively debated — some studies find no genuine ILC1
     while others identify a distinct TBX21+ cluster
 (2) ILC2 and ILC3 frequencies decline with age while ILC1/NK remain stable
 (3) the broken ADT marker in this panel can be effectively replaced by its corresponding
     RNA expression, as validated by multiple independent studies
 (4) IFN-gamma directly suppresses ILC2 function via IFNGR1/IFNGR2 signaling
 (5) CD57 (B3GAT1) is a universal pan-innate-cell aging marker

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

Conflicts (e.g., whether ILC1 exists as a distinct circulating population in humans) are framed as research opportunities the dataset can address.

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
| scglmmr    | Good      | Purpose-built for CITE-seq vaccination with mixed effects     | Small donor cohort pushes mixed-model limits                     |
| milo       | Good      | Cluster-free differential abundance for rare ILC subsets      | RNA-only; ADT not natively integrated                            |
| ThresholdR | Good      | GMM-based ADT denoising with flow-cytometry-style gating      | Very small panel limits reference-marker selection               |
| ADTnorm    | Good      | Interpretable ADT normalization                               | Small panel untested                                             |
| dsb        | Moderate  | Exact modality match; ambient noise correction                | No isotype controls; too few functional markers for Step II GMM  |
| MMoCHi     | Moderate  | Hierarchical CITE-seq classification mirrors flow gating      | Functional panel far below validated panel size (270+)           |
| MrVI       | Moderate  | Powerful cluster-free DE and DA with sample-level modeling    | RNA-only; no ADT integration; small cohort                       |
| scCODA     | Moderate  | Bayesian compositional analysis works with low replicates     | MACS enrichment distorts compositions fundamentally              |
| scArches   | Moderate  | Reference mapping with protein imputation potential           | No suitable ILC/NK reference atlas likely exists                 |
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
- Project constraints (non-functional marker, MACS enrichment, small cohort) propagated into every phase
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
- Major populations identified: NK_CD56dim, NK_CD56bright, NK_unresolved, ILC2_CD117neg/pos,
  ILCP, ILCP_KITlow, ILC3, ILC1_like, pDC_like
- Contaminants removed: T cell, B cell, Mono/DC, Lineage
```

## What the workflow did well

1. **Caught the non-functional marker trap automatically.** Every paper that referenced gating on the affected marker got a footnote in its intel file noting the marker is uninformative for this project and recommending the corresponding RNA signal. The fitness summary flagged ThresholdR as Moderate (not Good) because of the panel-size constraint. The analysis plan substitutes the gate everywhere it appears.

2. **Surfaced a research opportunity.** The synthesis flagged that HIGH-relevance papers disagreed on whether ILC1 exists in human blood. The dataset has multimodal markers that can address this directly — a finding that would have been buried in two separate intel files.

3. **Made cross-species data explicit.** Mouse papers were kept separate from the human consensus, but their hypotheses fed into the "novel cross-paper" section with explicit translation caveats.

## What needed manual intervention

- One method's `theory.md` failed `/review-knowledge` twice; the third pass with focused refinement guidance ("focus on missing notation table") passed.
- The analysis plan's Phase 1 needed a manual edit to reference a sample-specific QC threshold not captured by the project context.
- The mouse paper authors' surnames showed up in the design-analysis "cross-species" section — fine, but worth knowing the skill names them rather than just labeling the data.

## Total cost (approximate)

- Method KB: ~5 hours of agent runtime across 11 methods (mostly background)
- Literature mining: ~25 minutes for the initial batch of papers in parallel; incremental for later additions
- Synthesis: ~5 minutes per regeneration (use `--update` for incremental merges)
- Fitness evaluation: ~10 minutes for 11 methods in parallel
- Design analysis: ~5 minutes

The KB layer is reusable for any future CITE-seq project — that's the multiplicative payoff.
