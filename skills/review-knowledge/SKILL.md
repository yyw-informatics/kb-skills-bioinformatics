---
name: review-knowledge
description: Review and validate knowledge base documents for completeness, accuracy, and consistency
argument-hint: [method-name] [--phase=concept|theory|code|figures|all] [--skip-figures]
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion
---

# Review Knowledge Skill

This skill performs automated **quality review** of knowledge base documents. It checks for completeness, accuracy, consistency, and clarity, then produces a structured review report.

## What This Is NOT

This skill measures **document quality** (Is the knowledge base entry well-written and complete?), with verdicts of **PASS / NEEDS_REVISION / FAIL**.

Do not confuse with `/evaluate-fit`, which measures **project fit** (Is this method appropriate for the user's specific data and analysis goals?), with verdicts of **Excellent / Good / Moderate / Poor / Not Recommended**.

A document can PASS quality review (well-documented method) but be a Poor project fit (wrong modality), or vice versa.

## When to Use

- Called automatically by `/build-knowledge` after each phase
- Called manually to review existing knowledge base entries
- Called before `/evaluate-fit` to ensure knowledge base quality is high enough for fit assessment to be reliable

---

## Review Modes

### Single Document Review
```
/review-knowledge ADTnorm --phase=concept
```
Reviews only concept.md for the specified method.

### Full Knowledge Base Review
```
/review-knowledge ADTnorm --phase=all
```
Reviews all documents and cross-document consistency.

---

## Step 1: Load Review Context

### 1.1: Identify Method and Phase

Parse `$ARGUMENTS`:
- Method name (required)
- `--phase` flag: concept, theory, code, figures, or all (default: all)
- `--skip-figures` flag: figures.md is intentionally absent (set by `/build-knowledge --skip-figures`). When set, skip all `figures.md` completeness, accuracy, consistency, and clarity checks; do NOT flag the missing file as an issue; omit the figures.md row from the summary table. If the user explicitly asks for `--phase=figures` together with `--skip-figures`, return a single FAIL line: "figures.md was intentionally skipped — nothing to review." Combining `--phase=figures` with `--skip-figures` is a contradiction and should not be silent.

### 1.2: Load Documents

```bash
# List available documents
ls knowledge_base/{method}/
```

Load the relevant documents based on phase:
- concept.md
- theory.md
- code.md
- figures.md (skip if `--skip-figures` is set OR the file does not exist on disk; in either case do not treat its absence as a finding)

### 1.3: Load Source Material (if available)

Check for source references in documents:
- Paper PDF path (from YAML frontmatter)
- Repository URL (from code.md)
- Supplement path (if processed)

---

## Step 2: Completeness Check

### 2.1: Required Sections by Document

#### concept.md Requirements
| Section | Required | Check |
|---------|----------|-------|
| YAML frontmatter | ✓ | Has method, paper_title, tags |
| Problem Statement | ✓ | Non-empty, explains "why" |
| Core Innovation | ✓ | Describes key contribution |
| Use Cases | ✓ | At least 2 specific use cases |
| Limitations | ✓ | At least 1 documented |
| Task Tags | ✓ | Has searchable tags |
| Input Requirements | ✓ | Data format specified |
| Output Description | ✓ | What the method produces |

#### theory.md Requirements
| Section | Required | Check |
|---------|----------|-------|
| YAML frontmatter | ✓ | Has method, complexity |
| Mathematical Model | ✓ | Core equations present |
| Statistical Framework | ✓ | Distribution/model type |
| Key Assumptions | ✓ | At least 1 documented |
| Algorithm Steps | ✓ | Step-by-step procedure |
| Notation Table | Recommended | Defines symbols used |

#### code.md Requirements
| Section | Required | Check |
|---------|----------|-------|
| YAML frontmatter | ✓ | Has language, repository |
| Installation | ✓ | How to install |
| Main Functions | ✓ | Primary API documented |
| Parameters | ✓ | Key parameters explained |
| Example Usage | ✓ | Minimal working example |
| Dependencies | ✓ | Required packages listed |

#### figures.md Requirements
| Section | Required | Check |
|---------|----------|-------|
| YAML frontmatter | ✓ | Has method, figure_count |
| Figure Descriptions | ✓ | Each figure documented |
| Panel Breakdown | Recommended | Multi-panel figures explained |
| Key Takeaways | ✓ | What each figure demonstrates |

### 2.2: Generate Completeness Report

```markdown
## Completeness Check: {document}

| Section | Status | Notes |
|---------|--------|-------|
| YAML frontmatter | ✅ Present | All required fields |
| Problem Statement | ✅ Present | Clear and specific |
| Core Innovation | ⚠️ Partial | Missing comparison to alternatives |
| Use Cases | ❌ Missing | Section not found |
| ... | ... | ... |

**Completeness Score: {n}/{total} sections**
```

---

## Step 3: Accuracy Check

### 3.1: Cross-Reference with Source

If source paper is accessible, verify key claims:

#### Concept Accuracy
- Method name matches paper title/abstract
- Problem statement aligns with paper's introduction
- Use cases mentioned in paper
- Limitations discussed in paper's discussion section

#### Theory Accuracy
- Equations match those in paper
- Algorithm steps match paper's methods section
- Notation consistent with paper

#### Code Accuracy
- Repository URL is valid and accessible
- Function names match actual implementation
- Parameter names match code
- Example code is syntactically correct

### 3.2: Flag Potential Issues

```markdown
## Accuracy Check: {document}

### Verified ✅
- Method name matches paper: "ADTnorm"
- Core equation matches paper Eq. 1
- Repository URL valid

### Needs Verification ⚠️
- Claim: "Works with any panel size" - could not verify in paper
- Parameter default: "peak_type='mode'" - verify against code

### Potential Issues ❌
- Use case "trajectory analysis" not mentioned in paper
- Equation 3 notation differs from paper (paper uses θ, doc uses α)
```

---

## Step 4: Consistency Check

### 4.1: Internal Consistency

Within each document:
- Terminology used consistently
- Cross-references valid (e.g., "see Section X" exists)
- YAML frontmatter matches content

### 4.2: Cross-Document Consistency

Across all documents:
- Method name identical everywhere
- Task tags consistent
- Terminology matches (e.g., "negative peak" vs "negative mode")
- Theory equations referenced correctly in code.md
- Figures referenced in concept.md exist in figures.md (skip this check if figures.md is absent / `--skip-figures` is set)

### 4.3: Generate Consistency Report

```markdown
## Consistency Check

### Internal Consistency
| Document | Status | Issues |
|----------|--------|--------|
| concept.md | ✅ | None |
| theory.md | ⚠️ | "arcsinh" vs "asinh" inconsistent |
| code.md | ✅ | None |
| figures.md | ✅ | None |

### Cross-Document Consistency
| Check | Status | Notes |
|-------|--------|-------|
| Method name | ✅ | "ADTnorm" everywhere |
| Task tags | ⚠️ | concept.md has "normalization", theory.md has "normalize" |
| Equation refs | ❌ | code.md references Eq.3, theory.md only has Eq.1-2 |
| Figure refs | ✅ | All references valid |
```

---

## Step 5: Clarity Check

### 5.1: Evaluate Explanations

For each major section, assess:
- Could someone unfamiliar understand this?
- Are technical terms defined or linked?
- Are examples provided where helpful?
- Is the "why" explained, not just the "what"?

### 5.2: Clarity Indicators

**Good clarity signals:**
- Analogies or intuitive explanations
- Step-by-step breakdowns
- Examples with context
- Explicit assumptions stated

**Poor clarity signals:**
- Jargon without definition
- Jumping between topics
- Missing context or motivation
- Ambiguous pronouns ("it", "this")

### 5.3: Generate Clarity Report

```markdown
## Clarity Check: {document}

### Strong Sections ✅
- Problem Statement: Clear motivation with concrete example
- Algorithm Steps: Well-structured numbered list

### Needs Improvement ⚠️
- Core Innovation: Uses "landmark alignment" without definition
- Mathematical Model: Jumps from Eq.1 to Eq.2 without explanation

### Suggested Improvements
1. Add definition: "Landmark alignment refers to..."
2. Add transition between equations explaining the derivation
3. Include example values for parameters in code.md
```

---

## Step 6: Generate Review Report

### 6.1: Compile Full Report

Create `knowledge_base/{method}/.review_report.md`:

```markdown
---
method: {method}
reviewed: {date}
phase: {phase}
reviewer: automated
---

# Knowledge Base Review: {Method}

## Summary

| Document | Completeness | Accuracy | Consistency | Clarity | Overall |
|----------|--------------|----------|-------------|---------|---------|
| concept.md | 8/10 | ✅ | ✅ | ⚠️ | Good |
| theory.md | 7/10 | ⚠️ | ⚠️ | ⚠️ | Needs Work |
| code.md | 9/10 | ✅ | ✅ | ✅ | Excellent |
| figures.md | 6/10 | ✅ | ✅ | ⚠️ | Needs Work |

**Overall Status: {Ready / Needs Revision / Major Issues}**

---

## Detailed Findings

### concept.md
{completeness_report}
{accuracy_report}
{clarity_report}

### theory.md
{completeness_report}
{accuracy_report}
{clarity_report}

...

---

## Cross-Document Issues
{consistency_report}

---

## Recommended Actions

### High Priority
1. [ ] Add missing "Use Cases" section to concept.md
2. [ ] Fix equation notation mismatch in theory.md

### Medium Priority
3. [ ] Define "landmark alignment" in concept.md
4. [ ] Add transition text between equations in theory.md

### Low Priority
5. [ ] Standardize "arcsinh" vs "asinh" terminology
6. [ ] Add more detailed figure panel descriptions

---

## Review Metadata

- Documents reviewed: {n}
- Issues found: {n_high} high, {n_med} medium, {n_low} low
- Estimated revision effort: {Light / Moderate / Significant}
```

### 6.2: Return Summary for Orchestrator

When called by `/build-knowledge`, return a structured summary:

```markdown
## Review Result: {phase}

**Status: {PASS / NEEDS_REVISION / FAIL}**

**Issues Found:**
- High priority: {n}
- Medium priority: {n}
- Low priority: {n}

**Top 3 Issues:**
1. {issue_1}
2. {issue_2}
3. {issue_3}

**Recommendation:** {Proceed to next phase / Revise before continuing / Manual review needed}
```

---

## Integration with /build-knowledge

The orchestrator calls review after each phase:

```
Phase 1: /read-paper → concept.md
         ↓
         /review-knowledge {method} --phase=concept
         ↓
         Review says: PASS → Proceed
                      NEEDS_REVISION → Show issues, ask user
                      FAIL → Must fix before continuing
```

### Pass Criteria

| Status | Criteria | Action |
|--------|----------|--------|
| PASS | No high-priority issues, completeness ≥ 8/10 | Auto-proceed |
| NEEDS_REVISION | 1-2 high-priority issues OR completeness 6-7/10 | User decides |
| FAIL | 3+ high-priority issues OR completeness < 6/10 | Must revise |

---

## Standalone Usage

### Review Existing Knowledge Base
```
/review-knowledge ADTnorm
```
Produces full review report for manual inspection.

### Review Before Using in Project
```
/review-knowledge ADTnorm --phase=all
```
Ensures knowledge base is ready before `/evaluate-fit` or `/adapt-method`.

---

## Tips

- Run review after any manual edits to catch inconsistencies
- Use the review report to guide refinement passes
- High-priority issues should block progression
- Low-priority issues can be deferred to harmonization phase
- The review agent is conservative - some "issues" may be false positives

---

*This skill ensures knowledge base quality through systematic automated review.*
