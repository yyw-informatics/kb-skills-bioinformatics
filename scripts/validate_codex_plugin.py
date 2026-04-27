#!/usr/bin/env python3
"""Validate the Codex plugin manifest, marketplace, and generated adapters."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_JSON = ROOT / ".codex-plugin" / "plugin.json"
CODEX_PACKAGE_JSON = ROOT / "codex" / ".codex-plugin" / "plugin.json"
MARKETPLACE_JSON = ROOT / ".agents" / "plugins" / "marketplace.json"
SOURCE_SKILLS = ROOT / "skills"
CODEX_SKILLS = ROOT / "codex" / "skills"

PLUGIN_NAME = "kb-skills-bioinformatics"
PLUGIN_DISPLAY_NAME = "KB Skills Bioinformatics"
DEVELOPER_NAME = "Yuanyuan Wang"
MARKETPLACE_NAME = "kb-skills-bioinformatics-local"
DEFAULT_PROMPTS = [
    "Build a method knowledge base from this paper with $build-knowledge.",
    "Run the project pipeline with $run-pipeline for my context file.",
    "Evaluate which methods fit this project with $evaluate-fit --all.",
]
CODEX_PACKAGE_DEFAULT_PROMPTS = [
    "Build a method KB with $build-knowledge.",
    "Run the project pipeline with $run-pipeline.",
    "Evaluate method fit with $evaluate-fit --all.",
]


def load_json(path: Path, errors: list[str]) -> object | None:
    if not path.is_file():
        errors.append(f"Missing file: {rel(path)}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{rel(path)} is not valid JSON: {exc}")
        return None


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_frontmatter(text: str, path: Path, errors: list[str]) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        errors.append(f"{rel(path)}: missing opening frontmatter marker")
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        errors.append(f"{rel(path)}: missing closing frontmatter marker")
        return {}, text

    raw_frontmatter = text[4:end]
    body = text[end + len("\n---\n") :]
    frontmatter: dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            errors.append(f"{rel(path)}: unsupported frontmatter line: {line!r}")
            continue
        key, value = stripped.split(":", 1)
        frontmatter[key.strip()] = unquote_scalar(value.strip())
    return frontmatter, body


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        try:
            if value[0] == '"':
                return json.loads(value)
        except json.JSONDecodeError:
            pass
        return value[1:-1]
    return value


def parse_simple_yaml(path: Path, errors: list[str]) -> dict[str, object]:
    if not path.is_file():
        errors.append(f"Missing file: {rel(path)}")
        return {}

    parsed: dict[str, object] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            errors.append(f"{rel(path)}:{line_number}: unsupported YAML line: {line!r}")
            continue
        key, raw_value = stripped.split(":", 1)
        value = raw_value.strip()
        if value == "true":
            parsed[key.strip()] = True
        elif value == "false":
            parsed[key.strip()] = False
        elif len(value) >= 2 and value[0] == value[-1] == '"':
            try:
                parsed[key.strip()] = json.loads(value)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel(path)}:{line_number}: invalid quoted string: {exc}")
        else:
            parsed[key.strip()] = value
    return parsed


def source_skill_dirs() -> list[Path]:
    if not SOURCE_SKILLS.is_dir():
        return []
    return sorted(
        path
        for path in SOURCE_SKILLS.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def validate_plugin_manifest(errors: list[str]) -> None:
    validate_manifest(
        PLUGIN_JSON,
        errors,
        expected_skills="./codex/skills/",
        expected_default_prompts=DEFAULT_PROMPTS,
    )
    validate_manifest(
        CODEX_PACKAGE_JSON,
        errors,
        expected_skills="./skills/",
        expected_default_prompts=CODEX_PACKAGE_DEFAULT_PROMPTS,
    )


def validate_manifest(
    path: Path,
    errors: list[str],
    *,
    expected_skills: str,
    expected_default_prompts: list[str],
) -> None:
    manifest = load_json(path, errors)
    if not isinstance(manifest, dict):
        errors.append(f"{rel(path)} must contain a JSON object")
        return

    expected_fields = {
        "name": PLUGIN_NAME,
        "skills": expected_skills,
        "license": "MIT",
    }
    for key, expected in expected_fields.items():
        if manifest.get(key) != expected:
            errors.append(f"{rel(path)}: expected {key}={expected!r}")

    for forbidden in ("mcpServers", "apps"):
        if forbidden in manifest:
            errors.append(f"{rel(path)}: milestone must not define {forbidden}")

    author = manifest.get("author")
    if not isinstance(author, dict) or author.get("name") != DEVELOPER_NAME:
        errors.append(f"{rel(path)}: expected author.name={DEVELOPER_NAME!r}")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append(f"{rel(path)}: missing interface object")
        return

    checks = {
        "displayName": PLUGIN_DISPLAY_NAME,
        "developerName": DEVELOPER_NAME,
        "category": "Productivity",
        "defaultPrompt": expected_default_prompts,
    }
    for key, expected in checks.items():
        if interface.get(key) != expected:
            errors.append(f"{rel(path)}: expected interface.{key}={expected!r}")


def validate_marketplace(errors: list[str]) -> None:
    marketplace = load_json(MARKETPLACE_JSON, errors)
    if not isinstance(marketplace, dict):
        errors.append(f"{rel(MARKETPLACE_JSON)} must contain a JSON object")
        return

    if marketplace.get("name") != MARKETPLACE_NAME:
        errors.append(f"{rel(MARKETPLACE_JSON)}: expected name={MARKETPLACE_NAME!r}")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        errors.append(f"{rel(MARKETPLACE_JSON)}: plugins must be an array")
        return

    matching = [entry for entry in plugins if isinstance(entry, dict) and entry.get("name") == PLUGIN_NAME]
    if len(matching) != 1:
        errors.append(f"{rel(MARKETPLACE_JSON)}: expected exactly one {PLUGIN_NAME!r} entry")
        return

    entry = matching[0]
    if entry.get("source") != {"source": "local", "path": "./codex"}:
        errors.append(f"{rel(MARKETPLACE_JSON)}: expected local source path './codex'")
    if entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        errors.append(f"{rel(MARKETPLACE_JSON)}: expected AVAILABLE/ON_INSTALL policy")
    if entry.get("category") != "Productivity":
        errors.append(f"{rel(MARKETPLACE_JSON)}: expected category='Productivity'")


def validate_codex_adapters(errors: list[str]) -> int:
    source_dirs = source_skill_dirs()
    if not source_dirs:
        errors.append("No source skills found under skills/*/SKILL.md")
        return 0

    expected_names = {path.name for path in source_dirs}
    if not CODEX_SKILLS.is_dir():
        errors.append(f"Missing directory: {rel(CODEX_SKILLS)}")
        return len(source_dirs)

    actual_names = {
        path.name for path in CODEX_SKILLS.iterdir() if path.is_dir()
    }
    missing = sorted(expected_names - actual_names)
    extra = sorted(actual_names - expected_names)
    for name in missing:
        errors.append(f"Missing Codex adapter directory: codex/skills/{name}")
    for name in extra:
        errors.append(f"Unexpected Codex adapter directory: codex/skills/{name}")

    for source_dir in source_dirs:
        source_skill = source_dir / "SKILL.md"
        codex_skill = CODEX_SKILLS / source_dir.name / "SKILL.md"
        agent_yaml = CODEX_SKILLS / source_dir.name / "agents" / "openai.yaml"

        source_fm, _ = parse_frontmatter(
            source_skill.read_text(encoding="utf-8"), source_skill, errors
        )

        if not codex_skill.is_file():
            errors.append(f"Missing file: {rel(codex_skill)}")
            continue

        codex_fm, _ = parse_frontmatter(
            codex_skill.read_text(encoding="utf-8"), codex_skill, errors
        )
        keys = set(codex_fm)
        if keys != {"name", "description"}:
            errors.append(
                f"{rel(codex_skill)}: frontmatter keys must be only name and description"
            )
        if codex_fm.get("name") != source_fm.get("name"):
            errors.append(f"{rel(codex_skill)}: name does not match source skill")
        if codex_fm.get("description") != source_fm.get("description"):
            errors.append(f"{rel(codex_skill)}: description does not match source skill")

        agent = parse_simple_yaml(agent_yaml, errors)
        for key in ("display_name", "short_description", "default_prompt"):
            value = agent.get(key)
            if not isinstance(value, str) or not value:
                errors.append(f"{rel(agent_yaml)}: missing string field {key}")
        if agent.get("allow_implicit_invocation") is not True:
            errors.append(f"{rel(agent_yaml)}: allow_implicit_invocation must be true")

    return len(source_dirs)


def main() -> int:
    errors: list[str] = []
    validate_plugin_manifest(errors)
    validate_marketplace(errors)
    skill_count = validate_codex_adapters(errors)

    if errors:
        print("Codex plugin validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Codex plugin validation passed: {skill_count} adapters checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
