# Project context.md: what each field drives

Every Layer 2 skill (`/mine-paper`, `/synthesize-literature`, `/evaluate-fit`, `/design-analysis`, `/adapt-method`, `/run-pipeline`) reads `projects/<name>/context.md`. The fields you fill in there directly shape what those skills produce. This doc lists which fields drive which downstream behaviors so you can prioritize what to write carefully.

The template lives at [templates/project-context.md](../templates/project-context.md). Fill it out as concretely as possible — every field below has a downstream consumer.

## Highest-leverage fields

If you only fill in four things accurately, fill these:

1. **Assay / technology** (§1) — gates which methods `/evaluate-fit` recommends, drives `/mine-paper` relevance screening, shapes `/design-analysis` feasibility.
2. **Measurement panel + status** (§3) — broken markers (e.g., a mouse-reactive antibody flagged "non-functional") cascade through every hypothesis-testing template. Skills automatically substitute RNA for the broken protein everywhere the literature recommends the broken gate.
3. **Analysis goals & priorities** (§7) — determines hypothesis ranking, method selection, and the detail level of code templates in `/design-analysis`.
4. **Enrichment / sorting strategy** (§2) — changes expected cell frequencies (compositional methods adjust), affects statistical assumptions throughout synthesis and design.

## Full reference

| Field (template section) | Read by | What it does downstream |
|--------------------------|---------|-------------------------|
| Study question (§1) | mine-paper, synthesize, evaluate-fit, design-analysis | Frames relevance assessment in `/mine-paper` ("does this paper study the user's biological question?") |
| Comparisons (§1) | mine-paper, design-analysis | Determines which findings are testable in this design; shapes hypothesis prioritization and phase ordering |
| Assay / technology (§1) | mine-paper, synthesize, evaluate-fit, design-analysis | Mine-paper relevance filter; evaluate-fit method-modality matching; design-analysis measurement feasibility |
| Biology — cells, tissue, organism (§1) | mine-paper, evaluate-fit, design-analysis | Mine-paper flags species mismatches as translation gaps; evaluate-fit modality-match criterion; design-analysis gating constraint |
| Sample structure (§1) | mine-paper, design-analysis | Mine-paper identifies enrichment bias affecting expected frequencies; design-analysis drives batch/replicate handling |
| Enrichment / sorting (§2) | mine-paper, design-analysis, run-pipeline | Mine-paper flags non-representative composition; design-analysis informs compositional-analysis assumptions; run-pipeline cross-phase auditor verifies enrichment constraints are respected in the final plan |
| Wet-lab implications (§2) | mine-paper, design-analysis | Context for translation-gap severity; propagates to analysis assumptions (e.g., spike-in design constrains normalization choice) |
| Measurement panel + status (§3) | mine-paper, design-analysis | Non-functional markers trigger RNA-substitution suggestions every time they appear in the literature; excluded from gating hierarchies; code templates use only functional markers |
| Reference gates / ground truth (§4) | mine-paper, design-analysis | Benchmark for evaluating paper gating strategies; reference for validating consensus gating in the final plan |
| Sequencing depth (§5) | evaluate-fit, design-analysis | Shapes method scalability assessment; informs feature selection thresholds and sparsity handling |
| Outlier samples (§5) | design-analysis | Constrains QC filtering logic; may require per-sample handling in preprocessing |
| Known technical issues (§5) | mine-paper, evaluate-fit, design-analysis, run-pipeline | Affects translation-gap severity in mining; methods avoiding the issue score higher in evaluate-fit; QC step in design-analysis must address it; run-pipeline auditor verifies mitigation in the final plan |
| Gene aliases (§6) | mine-paper, synthesize, design-analysis | Ensures consistent protein↔gene-symbol interpretation across papers; deduplication in synthesis; consistent symbols in code templates |
| Analysis goals & priorities (§7) | mine-paper, synthesize, evaluate-fit, design-analysis | Mine-paper prioritizes "directly actionable" tagging; synthesis hypothesis ranking uses goal priorities; evaluate-fit selects matching methods; design-analysis structures phase ordering |
| Software preference (§8) | design-analysis, adapt-method | Design-analysis generates code templates in Python or R; adapt-method chooses conda env and script language |
| Compute environment (§8) | design-analysis, adapt-method | Design-analysis selects scalable-vs-lightweight methods; adapt-method validates environment exists before running |
| Reference data available (§8) | evaluate-fit, design-analysis | Available atlases improve fit scores for annotation/integration methods; informs which methods can be run |

## Worked example: how one broken marker propagates

In the [CITE-seq worked example](examples/cite-seq-example.md), one ADT marker (Marker_X, with corresponding RNA GENE_X) was found to be non-functional in the dataset. The project's `context.md` marked Marker_X status as `non-functional` in the measurement panel table (§3).

Every downstream skill saw this and acted:

- `/mine-paper` — every evidence file that quoted a gate on Marker_X added a footnote recommending GENE_X RNA as the substitute.
- `/evaluate-fit` — methods built around large CITE-seq panels (e.g., dsb Step II, MMoCHi) were demoted from "Good" to "Moderate" because the functional panel was effectively smaller than the validated minimum.
- `/design-analysis` — every code template that gated on Marker_X protein substituted `adata.X[:, gene2idx['GENE_X']]` for `adata.obsm['protein'][:, panel.index('Marker_X')]`.

This is the highest-value pattern the workflow surfaces: a single field in `context.md` ripples through dozens of downstream decisions.

## Fields not yet wired

- **Technical replicates** (§1, optional): mentioned in the template but no skill currently extracts replicate structure explicitly. Skills treat all samples as one pool unless `sample_structure` describes the design.
