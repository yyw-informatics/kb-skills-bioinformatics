---
name: split-supplement
description: "Split large supplementary PDFs into smaller chunks for processing, then combine extracted information"
---

# Codex Adapter

This adapter is generated from `skills/split-supplement/SKILL.md`. Edit the source Claude skill, then run `python3 scripts/sync_codex_skills.py` to refresh the Codex mirror.

Preserve the shared workflow contract: `knowledge_base/`, `projects/<name>/literature/`, `fitness_summary.md`, `analysis_plan.md`, audit files, and progress files remain the expected outputs.

## Claude-to-Codex Term Map

- `/skill-name` examples mean `$skill-name` or explicit plugin/skill invocation in Codex.
- `Task` / `TaskOutput` mean delegated/fresh-agent execution when available; otherwise run phases sequentially and verify files.
- `AskUserQuestion` means ask the user directly when required.
- `WebFetch` / `WebSearch` mean Codex web/search tools when available.

## Source Skill Instructions

# Split Supplement Skill

This skill handles large supplementary PDF files that exceed Claude's file size limit (20MB). It splits the PDF into smaller chunks, processes each chunk, and combines the extracted information.

## Workflow

### Step 1: Analyze the PDF

Check the PDF file:
```bash
pdfinfo "<pdf_path>"
```

Extract:
- Total pages
- File size
- Whether splitting is needed (>20MB)

### Step 2: Determine Chunk Strategy

Calculate optimal chunk size:
- Target: ~15-20 pages per chunk (typically keeps size under 15MB for text-heavy PDFs)
- For figure-heavy PDFs: may need smaller chunks (5-10 pages)

Ask user if they want to:
1. Process entire document (if under limit)
2. Process specific page ranges (e.g., "Methods" section)
3. Split and process all chunks

### Step 3: Split the PDF

Use `gs` (ghostscript) to extract page ranges:

```bash
gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dSAFER \
   -dFirstPage=<start> -dLastPage=<end> \
   -sOutputFile=<output_chunk.pdf> <input.pdf>
```

Or use `pdfseparate` for individual pages:
```bash
pdfseparate -f <start> -l <end> <input.pdf> <output_dir>/page_%d.pdf
```

Save chunks to scratchpad directory.

### Step 4: Process Each Chunk

For each chunk:
1. Read the PDF chunk using the Read tool
2. Extract relevant information based on context:
   - Mathematical formulations
   - Figure descriptions
   - Supplementary methods
   - Tables and data

3. Save extracted content to a temporary markdown file

### Step 5: Combine Extracted Information

Merge all extracted content into a coherent document:
- Organize by section/topic
- Remove duplicates
- Maintain proper ordering
- Note page references

### Step 6: Enhance Knowledge Base Files

Update the relevant knowledge base files with extracted supplementary content:

#### 6a: Enhance `concept.md`

Append a new section to `concept.md` with supplementary insights:

```markdown
---

## Supplementary Material Insights

*Extracted from Supplementary PDF using `/split-supplement` skill*

### Extended Background
[Additional context about the problem, motivation, or biological background]

### Method Comparisons
[Detailed comparisons with other methods from supplementary tables]

### Additional Applications
[Extended use cases or applications mentioned in supplementary]

### Data Sources & Benchmarks
[Details about datasets used for validation, benchmark designs]
```

Look for these types of content to add to `concept.md`:
- Extended motivation/background not in main paper
- Detailed method comparisons (Supplementary Tables)
- Additional use cases or applications
- Dataset descriptions and sources
- Author-provided benchmarking details

#### 6b: Enhance `theory.md`

Append a new section to `theory.md` with supplementary mathematical/technical details:

```markdown
---

## Supplementary Material Details

*Extracted from Supplementary PDF using `/split-supplement` skill*

### Extended Mathematical Formulations
[Detailed equations, proofs, derivations]

### Algorithm Pseudocode
[Step-by-step algorithms if provided]

### Parameter Selection Guidelines
[Detailed parameter tuning guidance]
```

#### 6c: Create Figure Documentation (if applicable)

For figures: create `figures_supplementary.md` or append to existing figure documentation

### Step 7: Verify and Refine

Re-read all enhanced files and perform an editorial review:

#### Completeness Check
- [ ] All extracted content properly attributed to supplementary source
- [ ] No critical information lost during chunking (check chunk boundaries)
- [ ] Mathematical formulations integrated correctly into `theory.md`
- [ ] Background/context information integrated into `concept.md`
- [ ] Page references included for traceability

#### Integration Quality
- [ ] New sections blend naturally with existing content (consistent style)
- [ ] No contradictions between main paper and supplementary content
- [ ] Cross-references between files are accurate
- [ ] Supplementary section headers clearly distinguish new content

#### Flow and Clarity
- [ ] Enhanced files maintain logical flow despite additions
- [ ] Supplementary content doesn't repeat main paper content
- [ ] Technical detail level is consistent throughout
- [ ] Section transitions are smooth

#### Efficiency Improvements
- Remove any duplicate information (main paper vs supplementary)
- Consolidate related supplementary content into coherent sections
- Eliminate verbose or tangential details that don't add value
- Ensure tables/lists are properly formatted

#### Final Validation
- Re-read `concept.md` end-to-end for coherence
- Re-read `theory.md` end-to-end for mathematical consistency
- Verify all LaTeX equations render correctly
- Check that no placeholder text remains

Make corrections directly to the files, then confirm completion.

## Usage Examples

### Example 1: Process entire supplementary
```
/split-supplement "/path/to/supplementary.pdf"
```

### Example 2: Process specific pages
```
/split-supplement "/path/to/supplementary.pdf" pages 1-20
```

### Example 3: Extract only figures
```
/split-supplement "/path/to/supplementary.pdf" figures
```

## Parameters

- `pdf_path`: Path to the large PDF file
- `pages` (optional): Specific page range (e.g., "1-20", "5,10,15-25")
- `mode` (optional): "all", "figures", "methods", "tables"
- `chunk_size` (optional): Pages per chunk (default: 15)

## Output Structure

### Temporary Files (scratchpad)
```
scratchpad/
├── pdf_chunks/
│   ├── chunk_001_pages_1-15.pdf
│   ├── chunk_002_pages_16-30.pdf
│   └── ...
├── extracted/
│   ├── chunk_001_content.md
│   ├── chunk_002_content.md
│   └── ...
└── combined_supplement.md
```

### Knowledge Base Updates
```
knowledge_base/<method>/
├── concept.md        # ← Enhanced with "Supplementary Material Insights" section
├── theory.md         # ← Enhanced with "Supplementary Material Details" section
└── figures/          # ← Optional: supplementary figures if extracted
    └── supplementary/
```

### What Gets Added

| Target File | Content Added |
|-------------|---------------|
| `concept.md` | Extended background, method comparisons, applications, datasets |
| `theory.md` | Mathematical details, algorithms, parameter guidelines |
| `figures/` | Supplementary figure diagrams (if applicable) |

## Important Notes

- Chunks are saved to the scratchpad directory (session-specific)
- Processing is sequential to maintain context
- Large figure-heavy sections may require smaller chunks
- Some context may be lost at chunk boundaries - the skill attempts to handle this by including overlap
- For very large PDFs (>100 pages), consider processing only relevant sections
