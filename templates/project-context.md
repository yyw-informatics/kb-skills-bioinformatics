# {Project name} — agent context

> This file is read by `/mine-paper`, `/synthesize-literature`, `/evaluate-fit`, `/design-analysis`, and `/adapt-method`.
> The skills use it to filter relevance, flag translation gaps, and generate project-specific recommendations.
> Be specific. Vague context produces vague output.
>
> Delete this blockquote when you start filling it in. Replace `{placeholders}` with your project's facts.
> Sections marked **(optional)** can be omitted if not applicable to your project.

---

## 1) Dataset & design

- **Study question**: {one sentence — what biological question are you answering?}
- **Comparison(s)**: {e.g., "treated vs control"; "responder vs non-responder"; "baseline vs follow-up"}
- **Assay / technology**: {e.g., "10x Chromium 3' v3.1 + Feature Barcoding (CITE-seq)"; "Smart-seq2"; "Visium spatial"}
- **Biology**: {what cells, tissue, organism — e.g., "PBMC T cell enriched, human"}
- **Sample structure**: {N donors, N samples, N libraries, replicate structure}
- **Technical replicates** *(optional)*: {which donors / conditions have replicates}

## 2) Wet-lab considerations *(optional)*

Anything that makes the data non-standard. Examples:

- Enrichment / sorting strategy that creates non-physiological cell composition
- Spike-ins, doping experiments, calibration controls
- Specific protocol deviations relevant to analysis

### Implications

What downstream analysis assumptions break or shift because of the above. Be explicit — e.g., "compositional analysis must account for enrichment bias; cell-type frequencies are not representative of in-vivo distributions."

## 3) Measurement panel

For multi-modal data (CITE-seq, spatial protein, etc.), list the exact panel:

| Marker | Gene symbol | Status | Notes |
|--------|-------------|--------|-------|
| {Marker_A}  | {GENE_A}       | functional | |
| {Marker_B}  | {GENE_B}       | **non-functional** | {brief reason — e.g., "high background", "failed QC", "uninformative in this dataset"} |
| ...         | ...            | ...        | |

For RNA-only data, omit this section or note "full transcriptome, no targeted panel."

**Critical**: flag every non-functional / broken marker. Skills will downstream-substitute the corresponding RNA in place of a broken protein ADT (or vice versa) only if you mark it here.

## 4) Reference gates / ground truth *(optional)*

If the project has a reference classification (flow gates, sorted populations, expert annotation), document the hierarchy here. Skills use this as a benchmark for annotation strategies.

```
Example (replace with your panel):
  Parent_type:    Marker_A+ Marker_B-
    Subtype_1:    Marker_A+ Marker_B- Marker_C+
    Subtype_2:    Marker_A+ Marker_B- Marker_C- Marker_D+
```

## 5) Sequencing / QC characteristics

- **Depth**: {mean reads/cell range, median genes/cell range}
- **Outlier samples** *(optional)*: {any samples with unusually low/high QC metrics}
- **Known technical issues** *(optional)*: {e.g., "high ambient RNA in samples X, Y"; "doublet rate higher than expected in batch 2"}

## 6) Gene name aliases *(optional)*

If your project domain uses common protein names interchangeably with gene symbols, list the canonical mapping here. The skills will apply this consistently.

```yaml
gene_aliases:
  ProteinName1: GENE_SYMBOL1
  ProteinName2: GENE_SYMBOL2
  # e.g. CD56: NCAM1, T-bet: TBX21
```

## 7) Analysis goals & priorities

What do you actually want to learn from this dataset? Be concrete — these guide hypothesis ranking and method selection:

1. {Primary question — e.g., "Which cell types change in frequency between conditions?"}
2. {Secondary question — e.g., "What transcriptional programs differ within a target cell type between conditions?"}
3. {Tertiary / exploratory — e.g., "Are there novel cell states we haven't annotated?"}

## 8) Constraints

- **Software**: {Python / R / both}
- **Compute**: {local / HPC / cloud}
- **Reference data available** *(optional)*: {atlases, prior datasets you can integrate against}

---

*Use this context file as the input to `/mine-paper`, `/synthesize-literature`, `/evaluate-fit`, `/design-analysis`, and `/adapt-method`. Re-edit it as your understanding of the project evolves; rerun affected skills with `--refresh` to propagate changes.*
