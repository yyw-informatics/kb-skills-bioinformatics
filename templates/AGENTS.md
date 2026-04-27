# {Project Name}

> Drop this file at the root of a project directory after installing kb-skills-bioinformatics in Codex.
> It tells Codex about the workflow conventions used here.

## Workflow

This project uses the kb-skills-bioinformatics Codex plugin for literature review, method evaluation, and analysis design.

Key entry points:
- `$build-knowledge <paper.pdf>` - turn a method paper into structured KB entry
- `$mine-paper --all projects/{name}/context.md --project={name}` - extract intel from biology papers
- `$synthesize-literature projects/{name}/context.md --project={name}` - cross-paper synthesis
- `$evaluate-fit --all projects/{name}/context.md --project={name}` - score methods against the project
- `$design-analysis projects/{name}/literature/0_synthesis_literature.md projects/{name}/context.md --project={name}` - produce ordered analysis plan
- `$run-pipeline projects/{name}/context.md --project={name}` - run the per-project workflow end to end
- `$adapt-method <method-name>` - generate preliminary run on real data

Each skill's `SKILL.md` documents its prerequisites, arguments, and outputs. If a skill body shows Claude-style `/skill-name` examples, use the equivalent Codex `$skill-name` invocation.

## Directory layout

```
.
├── *.pdf                            # method papers
├── papers/                          # biology papers
├── knowledge_base/                  # built by $read-paper, $build-knowledge, $index-docs
│   ├── <method>/{concept,theory,code,figures}.md
│   └── ecosystems/<package>/
└── projects/<project_name>/
    ├── context.md                   # required input - describes data, panel, comparisons
    ├── literature/                  # built by $mine-paper, $synthesize-literature
    ├── bioinformatics/              # built by $evaluate-fit
    ├── analysis_plan.md             # built by $design-analysis
    └── <method>_adaptation/         # built by $adapt-method
```

## Project-specific notes

{Replace this section with anything Codex should know about this specific project, such as conventions, data paths, environment names, or things to avoid.}
