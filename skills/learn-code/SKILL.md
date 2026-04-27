---
name: learn-code
description: Deep dive into a method's implementation, mapping theory to code and documenting architecture
argument-hint: [method-name] [--repo=url] [--web-search-repos]
allowed-tools: Read, Glob, Grep, Write, Bash, Task, WebSearch, WebFetch
---

# Learn Code Skill

This skill analyzes the source code of a bioinformatics method to understand its implementation details and map theoretical concepts to actual code.

## Prerequisites & Outputs

**Requires**:
- `knowledge_base/<method>/concept.md` exists (from `/read-paper`)
- A repository URL — resolved via the chain in Step 1 below
- `knowledge_base/<method>/theory.md` is recommended but not strictly required

**Produces**: `knowledge_base/<method>/code.md` documenting architecture, key APIs, parameters, and theory↔code mapping. If no repo can be resolved, produces a minimal `code.md` stub noting that implementation documentation is not available, and records the failure with reasons.

## Workflow

### Step 1: Resolve Repository

Try each source in order. Stop at the first that yields a verified URL.

```
1. --repo=<url>         (explicit user input — highest priority, no verification)
2. methods.yaml         (project-root override file, see schema below)
3. concept.md github:   (extracted by /read-paper from the paper)
4. web search           (only if --web-search-repos is set; verification gated)
5. MISSING              (write the no_repo stub, log reasons)
```

Record the chosen source, URL, and any verification notes in `code.md`'s frontmatter (`repo_source`, `repo_confidence`, `repo_notes`) so downstream consumers can audit.

#### 1a. Explicit `--repo=` flag

If passed, use as-is. Confidence: high. Source: `flag`.

#### 1b. `methods.yaml` lookup

Look for `methods.yaml` (or `methods.yml`) at the project root. Schema:

```yaml
# methods.yaml — optional method → repo URL overrides.
# Consulted by /learn-code AFTER --repo= and BEFORE concept.md.
# Use when:
#   - the paper doesn't list a GitHub URL
#   - paper extraction picked the wrong link (old fork, mirror)
#   - you want to pin a specific fork or commit

totalVI: https://github.com/scverse/scvi-tools
dsb: https://github.com/niaid/dsb
ADTnorm: https://github.com/yezhengSTAT/ADTnorm
```

Lookup is by `<method>` (case-sensitive match against the keys). If found, use the URL. Confidence: high. Source: `yaml`.

#### 1c. `concept.md` extraction (existing behavior)

```bash
grep -A1 "github:" knowledge_base/<method>/concept.md
```

If a `github:` URL is present and `code_status` is not `no_repo`, use it. Confidence: high. Source: `paper`.

#### 1d. Web search (opt-in via `--web-search-repos`)

Only runs if `--web-search-repos` is set AND all prior steps failed.

**Search**:
```
WebSearch: "<method-name> github"
WebSearch: "<method-name> <first-author-surname> github"   # if author available
```

Take the top 2–3 candidate `github.com/<owner>/<repo>` URLs (deduplicated, ignoring forks of the same upstream).

**Verify**: for each candidate, `WebFetch` the README (`https://raw.githubusercontent.com/<owner>/<repo>/HEAD/README.md` or the GitHub page). Apply this gate — **2 of 3 must pass**:

| Check | Pass criteria |
|-------|---------------|
| **Method name in README** | The method name appears as a case-insensitive whole-token match (e.g. "totalVI" or "total VI", not just "total") in the README first 5KB |
| **Paper linkage** | README contains the paper title, DOI, or arXiv ID (extract from `concept.md` frontmatter if present); OR repo description references the paper |
| **Has analysis code** | Repo contains `.py`, `.R`, `.ipynb`, `pyproject.toml`, `DESCRIPTION`, or `setup.py` (filters out paper-list indexes, slide decks, mirrors); use the GitHub repo metadata or root tree |

**On 2/3 pass**: use the candidate. Confidence: medium. Source: `search`. Record which checks passed in `repo_notes`.

**On 0–1 pass**: do NOT use that candidate. Try the next one. If no candidate passes, fall through to MISSING. Record all candidates considered in `repo_notes` so a human can review.

**Never**: pick a candidate based on search ranking alone, without the verification gate.

#### 1e. MISSING fallback

If all sources failed (or `code_status: no_repo` was already set), write the minimal stub:

```markdown
---
name: <method>
language: unknown
code_status: no_repo
repo_source: none
repo_notes: |
  Resolution attempted in order:
  - --repo=: not provided
  - methods.yaml: <not present | no entry for {method}>
  - concept.md github:: <not present | code_status: no_repo>
  - web search: <skipped (--web-search-repos not set) | tried [list candidates] but none passed verification>
---

# <method> — Code Documentation

No public repository was identified for this method. Implementation details
cannot be documented here.

To resolve:
- Add an entry to `methods.yaml` at the project root, OR
- Re-run `/build-knowledge <paper.pdf> --method=<method> --repo=<url>`, OR
- Re-run `/read-paper` to update concept.md if a URL has since become available.
```

Then stop. Skip the rest of the workflow.

#### 1f. Clone the resolved repo

If repository not already cloned, clone to scratchpad:
```bash
git clone <github_url> <scratchpad>/<method>
```

### Step 2: Analyze Repository Structure

Map the codebase architecture:
- Identify main entry points
- Find core algorithm implementations
- Locate utility/helper functions
- Identify test files and examples

```bash
# For R packages
ls -la R/
ls -la src/  # compiled code
ls -la tests/

# For Python packages
ls -la src/ or <package_name>/
ls -la tests/
```

### Step 3: Map Theory to Code

For each theoretical concept in `theory.md`:
1. Find the corresponding implementation
2. Document file path and line numbers
3. Note any deviations from theory (approximations, optimizations)
4. Identify key parameters and defaults

Create a mapping table:
| Theoretical Concept | Implementation | File:Lines |
|---------------------|----------------|------------|
| Concept from theory.md | Function/class name | path:L##-L## |

### Step 4: Document Key Functions

For each core function:
- **Purpose**: What it does
- **Inputs**: Parameters with types and descriptions
- **Outputs**: Return values
- **Algorithm**: Step-by-step logic
- **Dependencies**: External packages/functions called
- **Complexity**: Time/space complexity if notable

### Step 5: Identify Design Patterns

Document architectural decisions:
- Data structures used
- Error handling approach
- Parallelization strategy
- Memory management
- API design patterns

### Step 6: Note Implementation Details

Capture practical details often missing from papers:
- Default parameter values and their rationale
- Edge case handling
- Performance optimizations
- Known limitations in code comments
- Version-specific behaviors

### Step 7: Create code.md

Generate `knowledge_base/<method>/code.md` with:

```markdown
---
name: <method>
repository: <github_url>
language: <R|Python|etc>
last_analyzed: <date>
version_analyzed: <version/commit>
---

# <Method> - Implementation Details

## Repository Structure
[Directory layout and organization]

## Core Components
[Main modules/files and their purposes]

## Theory-to-Code Mapping
[Table mapping theoretical concepts to implementations]

## Key Functions

### function_name
[Detailed documentation]

## Data Flow
[How data moves through the pipeline]

## Dependencies
[External packages and their purposes]

## Configuration & Parameters
[Default values and configuration options]

## Extension Points
[How to customize or extend the method]

## Code Quality Notes
[Testing, documentation, maintenance observations]
```

### Step 8: Verify and Refine

Re-read the generated `code.md` and perform an editorial review:

#### Completeness Check
- [ ] Repository structure accurately reflects the actual codebase
- [ ] All core functions documented with inputs, outputs, and purpose
- [ ] Theory-to-Code mapping table covers all concepts from `theory.md`
- [ ] File paths and line numbers are accurate and up-to-date
- [ ] Dependencies list is complete with version requirements noted

#### Accuracy Check
- [ ] Code snippets/examples are syntactically correct
- [ ] Function signatures match actual implementation
- [ ] Default parameter values match source code
- [ ] Data flow diagram accurately represents the pipeline

#### Cross-Reference Validation
- [ ] Theory concepts in mapping table match `theory.md` exactly
- [ ] Function names match actual code in repository
- [ ] Referenced files exist at stated paths

#### Flow and Clarity
- [ ] Documentation flows from high-level structure → core components → detailed functions
- [ ] No orphaned sections (each section referenced elsewhere or clearly standalone)
- [ ] Code examples are minimal but illustrative
- [ ] Complex logic is explained step-by-step

#### Efficiency Improvements
- Remove redundant function documentation (consolidate similar utilities)
- Ensure mapping table has no duplicate entries
- Tighten verbose code explanations
- Group related functions under meaningful subsections

Make corrections directly to the file, then confirm completion.

## Output

Creates/updates:
- `knowledge_base/<method>/code.md` - Implementation documentation
- `knowledge_base/<method>/repo/` - Cloned repository (git clone)
- `knowledge_base/<method>/scripts/` - Key scripts extracted for reference

### Folder Structure
```
knowledge_base/<method>/
├── concept.md          # From /read-paper
├── theory.md           # From /understand-theory
├── code.md             # From /learn-code (this skill)
├── repo/               # Cloned GitHub repository
│   └── <repo-contents>
└── scripts/            # Extracted key scripts with annotations
    ├── core_algorithm.R
    ├── preprocessing.R
    └── ...
```

The `scripts/` folder contains annotated copies of the most important source files for quick reference, with added comments explaining the code's relationship to the theory.

## Usage Examples

```
/learn-code ADTnorm
/learn-code Seurat
/learn-code scanpy
```

## Tips

- Use `Grep` to find specific function implementations
- Read test files to understand expected behavior
- Check vignettes/tutorials for usage patterns
- Look at DESCRIPTION (R) or setup.py/pyproject.toml (Python) for dependencies
- Git history can reveal evolution of implementation decisions
