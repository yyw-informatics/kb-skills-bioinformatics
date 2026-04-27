# Directory Layout Convention

The skills assume a project directory with this structure. You don't need to create it all up-front — most directories are created by the skills as needed. The exceptions (which YOU create) are marked **(create)**.

```
<project-root>/                        # working directory when you invoke skills
│
├── *.pdf                              # (create) method papers in root, picked up by /read-paper, /build-knowledge
├── papers/                            # (optional, create) biology papers, picked up by /mine-paper --dir=papers/
│
├── knowledge_base/                    # (auto) built by KB skills
│   ├── <method-name>/                 # one directory per bioinformatics method
│   │   ├── concept.md                 # /read-paper
│   │   ├── theory.md                  # /understand-theory
│   │   ├── code.md                    # /learn-code
│   │   ├── figures.md                 # /extract-figures
│   │   ├── repo/                      # /learn-code (cloned source)
│   │   └── .build_progress.md         # /build-knowledge state tracker
│   │
│   └── ecosystems/                    # /index-docs
│       └── <package-name>/            # e.g., scanpy, scvi-tools, seurat
│           ├── navigation.md
│           ├── capabilities.yaml
│           ├── function_index.yaml
│           ├── workflows.yaml
│           └── sync_metadata.yaml
│
└── projects/                          # (auto) per-project assessments and plans
    └── <project-name>/                # e.g., my_aging_study
        ├── context.md                 # (create) YOU write this, using templates/project-context.md
        │
        ├── literature/                # /mine-paper, /synthesize-literature
        │   ├── <paper-slug>_intel.md  # one per paper
        │   ├── 0_synthesis_literature.md
        │   ├── literature_summary.md
        │   └── .mining_progress.md
        │
        ├── bioinformatics/            # /evaluate-fit
        │   ├── <method>_fitness_assessment.md
        │   ├── fitness_summary.md
        │   └── .evaluation_progress.md
        │
        ├── analysis_plan.md           # /design-analysis (the integrated output)
        │
        └── <method>_adaptation/       # /adapt-method
            ├── 01_data_discovery.md
            ├── 02_eda_report.md
            ├── 03_preliminary_results.md
            ├── 04_adaptation_summary.md
            ├── scripts/               # generated R or Python scripts
            └── results/               # script outputs
```

## What lives where, and why

- **Method papers in root, biology papers in `papers/`** — keeps the two literature streams separate. Method papers (totalVI, dsb, ADTnorm, etc.) feed the *knowledge_base/* layer; biology papers (your domain literature) feed the *projects/{name}/literature/* layer.
- **`knowledge_base/` is shared** across projects on the same machine. Build a method KB once, evaluate it against many projects.
- **`projects/<name>/` is project-specific.** Everything here is filtered through that project's `context.md`.
- **The `context.md` you write is the most important file.** It's how the skills know what's relevant to your study. Use [templates/project-context.md](project-context.md) as a starting point.

## File naming conventions

- Method directories: lowercase or paper's preferred capitalization (e.g., `totalVI/`, `dsb/`, `ADTnorm/`)
- Project directories: `snake_case` (e.g., `cite_seq_aging`, `mouse_brain_atlas`)
- Paper intel slugs: `<first-author-lastname>_<2-3-keywords>` (e.g., `hazenberg_human_ilcs`)

## What's NOT versioned (when committing to Git)

If you're version-controlling a project that uses these skills, consider gitignoring:
- `*.pdf` — copyright concerns; PDFs aren't artifacts you should redistribute
- `**/repo/` — `/learn-code` clones source repos; reference them by URL instead
- `**/.build_progress.md`, `**/.evaluation_progress.md`, `**/.mining_progress.md` — local state trackers
