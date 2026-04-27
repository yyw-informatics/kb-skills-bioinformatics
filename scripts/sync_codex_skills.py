#!/usr/bin/env python3
"""Generate Codex skill adapters from the Claude-facing skills tree."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILLS = ROOT / "skills"
CODEX_SKILLS = ROOT / "codex" / "skills"


DEFAULT_PROMPTS = {
    "adapt-method": "Apply a selected KB method to my data with $adapt-method.",
    "build-knowledge": "Build a method knowledge base from a paper with $build-knowledge.",
    "design-analysis": "Create an integrated analysis plan with $design-analysis.",
    "evaluate-fit": "Evaluate which KB methods fit this project with $evaluate-fit.",
    "extract-figures": "Document figures from a method paper with $extract-figures.",
    "harmonize": "Harmonize the KB documents for this method with $harmonize.",
    "index-docs": "Index a package documentation site with $index-docs.",
    "learn-code": "Map a method's implementation to its theory with $learn-code.",
    "mine-paper": "Mine biology papers for project-specific intel with $mine-paper.",
    "read-paper": "Extract a method paper concept summary with $read-paper.",
    "review-knowledge": "Review a method KB entry with $review-knowledge.",
    "run-pipeline": "Run the end-to-end project pipeline with $run-pipeline.",
    "split-supplement": "Process a large supplementary PDF with $split-supplement.",
    "synthesize-literature": "Synthesize mined biology papers with $synthesize-literature.",
    "understand-theory": "Extract a method's mathematical theory with $understand-theory.",
}


SHORT_DESCRIPTIONS = {
    "adapt-method": "Apply a selected method to real project data.",
    "build-knowledge": "Build a reusable method knowledge base entry from a paper.",
    "design-analysis": "Produce an integrated, code-ready analysis plan.",
    "evaluate-fit": "Score KB methods against project data and goals.",
    "extract-figures": "Document paper figures for reproducibility.",
    "harmonize": "Align terminology and cross-references across a method KB entry.",
    "index-docs": "Index package docs into an agent-friendly navigation layer.",
    "learn-code": "Map a method's theory to its implementation.",
    "mine-paper": "Extract project-specific intel from biology papers.",
    "read-paper": "Extract concepts and metadata from a method paper.",
    "review-knowledge": "Review a method KB entry for quality and consistency.",
    "run-pipeline": "Run the per-project literature-to-analysis pipeline end to end.",
    "split-supplement": "Split and process large supplementary PDFs.",
    "synthesize-literature": "Synthesize mined paper intel into consensus hypotheses.",
    "understand-theory": "Extract mathematical and statistical foundations from a paper.",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if checked-in Codex adapters differ from generated output.",
    )
    return parser.parse_args()


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing opening frontmatter marker")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"{path}: missing closing frontmatter marker")

    raw_frontmatter = text[4:end]
    body = text[end + len("\n---\n") :]
    frontmatter: dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"{path}: unsupported frontmatter line: {line!r}")
        key, value = stripped.split(":", 1)
        frontmatter[key.strip()] = unquote_scalar(value.strip())
    return frontmatter, body


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def display_name(skill_name: str) -> str:
    return " ".join(part.capitalize() for part in skill_name.split("-"))


def short_description(description: str, limit: int = 140) -> str:
    if len(description) <= limit:
        return description
    truncated = description[: limit - 1].rsplit(" ", 1)[0]
    return truncated.rstrip(".,;:") + "."


def source_skill_dirs() -> list[Path]:
    return sorted(
        path
        for path in SOURCE_SKILLS.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def codex_preamble(source_relpath: str) -> str:
    return f"""# Codex Adapter

This adapter is generated from `{source_relpath}`. Edit the source Claude skill, then run `python3 scripts/sync_codex_skills.py` to refresh the Codex mirror.

Preserve the shared workflow contract: `knowledge_base/`, `projects/<name>/literature/`, `fitness_summary.md`, `analysis_plan.md`, audit files, and progress files remain the expected outputs.

## Claude-to-Codex Term Map

- `/skill-name` examples mean `$skill-name` or explicit plugin/skill invocation in Codex.
- `Task` / `TaskOutput` mean delegated/fresh-agent execution when available; otherwise run phases sequentially and verify files.
- `AskUserQuestion` means ask the user directly when required.
- `WebFetch` / `WebSearch` mean Codex web/search tools when available.

## Source Skill Instructions

"""


def build_skill_md(source_path: Path) -> str:
    text = source_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text, source_path)
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not name or not description:
        raise ValueError(f"{source_path}: frontmatter must include name and description")

    source_relpath = source_path.relative_to(ROOT).as_posix()
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {json.dumps(description)}\n"
        "---\n\n"
        + codex_preamble(source_relpath)
        + body.lstrip("\n")
    )


def build_openai_yaml(source_path: Path) -> str:
    text = source_path.read_text(encoding="utf-8")
    frontmatter, _ = parse_frontmatter(text, source_path)
    name = frontmatter["name"]
    description = frontmatter["description"]
    prompt = DEFAULT_PROMPTS.get(
        name, f"Use ${name} for this bioinformatics workflow step."
    )
    return "\n".join(
        [
            "# Generated by scripts/sync_codex_skills.py; edit the source skill instead.",
            f"display_name: {json.dumps(display_name(name))}",
            "short_description: "
            f"{json.dumps(SHORT_DESCRIPTIONS.get(name, short_description(description)))}",
            f"default_prompt: {json.dumps(prompt)}",
            "allow_implicit_invocation: true",
            "",
        ]
    )


def expected_files() -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    for source_dir in source_skill_dirs():
        source_path = source_dir / "SKILL.md"
        target_dir = CODEX_SKILLS / source_dir.name
        outputs[target_dir / "SKILL.md"] = build_skill_md(source_path)
        outputs[target_dir / "agents" / "openai.yaml"] = build_openai_yaml(source_path)
    return outputs


def write_files(outputs: dict[Path, str]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_files(outputs: dict[Path, str]) -> int:
    stale: list[str] = []
    for path, expected in outputs.items():
        if not path.exists():
            stale.append(f"missing: {path.relative_to(ROOT).as_posix()}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            stale.append(f"stale: {path.relative_to(ROOT).as_posix()}")

    if CODEX_SKILLS.exists():
        expected_paths = set(outputs)
        for path in sorted(p for p in CODEX_SKILLS.rglob("*") if p.is_file()):
            if path not in expected_paths:
                stale.append(f"unexpected: {path.relative_to(ROOT).as_posix()}")

    if stale:
        print("Codex adapters are out of sync:", file=sys.stderr)
        for item in stale:
            print(f"  {item}", file=sys.stderr)
        print("Run: python3 scripts/sync_codex_skills.py", file=sys.stderr)
        return 1

    print(f"Codex adapters are in sync ({len(outputs) // 2} skills).")
    return 0


def main() -> int:
    args = parse_args()
    outputs = expected_files()
    if not outputs:
        print("No source skills found under skills/*/SKILL.md", file=sys.stderr)
        return 1
    if args.check:
        return check_files(outputs)

    write_files(outputs)
    print(f"Wrote Codex adapters for {len(outputs) // 2} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
