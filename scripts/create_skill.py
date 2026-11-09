"""Create an agent-library skill, its manifest, and its intent in one command.

Default: every agent sees the skill. Only pass --ignore / --variant when an
agent really needs an exception. The catalog is the single source; never copy
the skill into an agent's native skill directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# agent-library 根目录的解析顺序：
#   1. 环境变量 AGLIB_STORE（推荐；换机器/换目录时只改它）
#   2. 本机习惯路径 D:\agent-library
#   3. 按脚本位置推导：catalog/<id>/scripts/create_skill.py -> 上溯 3 层
# 也可以在命令行用 --store 直接指定。
STORE = Path(os.environ.get("AGLIB_STORE") or r"D:\agent-library").expanduser()
if not os.environ.get("AGLIB_STORE") and not (STORE / "catalog").is_dir():
    STORE = Path(__file__).resolve().parents[3]
CATALOG = STORE / "catalog"
AGENTS_FILE = CATALOG / "agents.json"
INTENTS_FILE = CATALOG / "intents.json"
DEFAULT_REQUIRES = ["filesystem-read"]
ALLOWED_REQUIRES = {"filesystem-read", "filesystem-write", "shell", "network", "secrets"}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})")


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def load_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        fail(f"{path} 不是 JSON 对象")
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def frontmatter(name: str, description: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        "description: >-\n"
        f"  {description}\n"
        "---\n\n"
    )


def body_template(skill_id: str, description: str, when: str) -> str:
    return (
        f"# {skill_id}\n\n"
        f"{description}\n\n"
        "## 何时使用\n\n"
        f"{when}\n\n"
        "## 步骤\n\n"
        "1. 先确认输入、输出和不能碰的边界。\n"
        "2. 按最小步骤完成；能脚本化就放 `scripts/`。\n"
        "3. 交付后写一句验证证据，不要只说“已完成”。\n"
    )


def parse_list(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        out.extend(part.strip() for part in str(value).split(",") if part.strip())
    return out


def parse_variants(values: list[str] | None) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for value in values or []:
        if "=" not in value:
            fail(f"--variant 需要 agent=path：{value}")
        agent, raw = value.split("=", 1)
        path = Path(raw).expanduser()
        if not path.is_file():
            fail(f"特殊版本文件不存在：{path}")
        out.append((agent.strip(), path))
    return out


def agents() -> set[str]:
    data = load_json(AGENTS_FILE, {"agents": {}})
    return set((data.get("agents") or {}).keys())


def update_intent(
    data: dict,
    intent_id: str,
    skill_id: str,
    description: str,
    category: str,
    patterns: list[str],
    keywords: list[str],
    examples: list[str],
) -> None:
    intents = data.setdefault("intents", [])
    found = None
    for intent in intents:
        if str(intent.get("id")) == intent_id:
            found = intent
            break
    if found is None:
        found = {
            "id": intent_id,
            "category": category,
            "description": description,
            "patterns": patterns or [re.escape(skill_id)],
            "keywords": keywords,
            "excludes": [],
            "examples": examples,
            "skills": [skill_id],
        }
        intents.append(found)
    else:
        skills = found.setdefault("skills", [])
        if skill_id not in skills:
            skills.append(skill_id)
        if not found.get("patterns"):
            found["patterns"] = patterns or [re.escape(skill_id)]
        if keywords:
            found["keywords"] = list(dict.fromkeys(list(found.get("keywords") or []) + keywords))
        if examples:
            found["examples"] = list(dict.fromkeys(list(found.get("examples") or []) + examples))
    categories = data.setdefault("categories", {})
    categories.setdefault(category, [])
    if intent_id not in categories[category]:
        categories[category].append(intent_id)


def main(argv: list[str] | None = None) -> int:
    global STORE, CATALOG, AGENTS_FILE, INTENTS_FILE
    parser = argparse.ArgumentParser(description="Create an agent-library skill in one command")
    parser.add_argument(
        "--store",
        default=str(STORE),
        help="agent-library 根目录；默认 $env:AGLIB_STORE，其次 D:\\agent-library，"
        "最后按脚本位置推导（需要该目录下存在 catalog/）",
    )
    parser.add_argument("--id", required=True, dest="skill_id")
    parser.add_argument("--description", required=True)
    parser.add_argument("--when", action="append", help="触发场景；可重复")
    parser.add_argument("--when-not", action="append", default=[])
    parser.add_argument("--category", default="general")
    parser.add_argument("--tags", action="append", help="manifest tags；可重复或逗号分隔")
    parser.add_argument("--local-only", action="store_true", help="等价于 --tags 限本机")
    parser.add_argument("--mode", choices=["on-demand", "resident"], default="on-demand")
    parser.add_argument("--intent", help="复用已有 intent；默认与 skill id 同名")
    parser.add_argument("--pattern", action="append", help="intent 正则；可重复")
    parser.add_argument("--keyword", action="append", help="intent 关键词；可重复")
    parser.add_argument("--example", action="append", help="intent 例子；可重复")
    parser.add_argument("--requires", action="append", help="默认 filesystem-read")
    parser.add_argument("--body", default="")
    parser.add_argument("--body-file")
    parser.add_argument("--ignore", action="append", help="agent，可重复或逗号分隔")
    parser.add_argument("--variant", action="append", help="agent=文件，可重复")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    STORE = Path(args.store).expanduser().resolve()
    CATALOG = STORE / "catalog"
    AGENTS_FILE = CATALOG / "agents.json"
    INTENTS_FILE = CATALOG / "intents.json"
    if not CATALOG.is_dir():
        fail(f"catalog 不存在：{CATALOG}")
    if not ID_RE.fullmatch(args.skill_id):
        fail("--id 必须是小写 kebab-case")
    if not args.description.strip():
        fail("--description 不能空")
    if not ID_RE.fullmatch(args.category):
        fail("--category 必须是小写 kebab-case")

    when = [str(x).strip() for x in (args.when or []) if str(x).strip()]
    if not when:
        when = [args.description.strip()]
    when_not = [str(x).strip() for x in args.when_not if str(x).strip()]
    requires = parse_list(args.requires) or list(DEFAULT_REQUIRES)
    bad_requires = [x for x in requires if x not in ALLOWED_REQUIRES]
    if bad_requires:
        fail("未知 requires：" + ", ".join(bad_requires))
    tags = parse_list(args.tags)
    if args.local_only and "限本机" not in tags:
        tags.append("限本机")
    ignore = parse_list(args.ignore)
    variants = parse_variants(args.variant)
    for _agent, source in variants:
        if SECRET_RE.search(source.read_text(encoding="utf-8")):
            fail(f"特殊版本里看起来有密钥：{source}")
    known_agents = agents()
    bad_agents = [a for a in ignore + [a for a, _ in variants] if a not in known_agents]
    if bad_agents:
        fail("未知 agent：" + ", ".join(sorted(set(bad_agents))))

    body = args.body
    if args.body_file:
        body = Path(args.body_file).expanduser().read_text(encoding="utf-8")
    if not body.strip():
        body = body_template(args.skill_id, args.description.strip(), when[0])
    if not body.startswith("---"):
        body = frontmatter(args.skill_id, args.description.strip()) + body
    if SECRET_RE.search(body):
        fail("正文里看起来有密钥，拒绝写入")

    folder = CATALOG / args.skill_id
    if folder.exists() and not args.force:
        fail(f"skill 目录已存在：{folder}（用 --force 覆盖正文/manifest）")
    intent_id = args.intent or args.skill_id
    if not ID_RE.fullmatch(intent_id):
        fail("--intent 必须是小写 kebab-case")

    patterns = parse_list(args.pattern) or [re.escape(args.skill_id)]
    keywords = parse_list(args.keyword)
    examples = parse_list(args.example)
    manifest = {
        "schemaVersion": 1,
        "id": args.skill_id,
        "kind": "skill",
        "mode": args.mode,
        "when": when,
        "whenNot": when_not,
        "requires": requires,
        "merge": "shared",
        "category": args.category,
        "intents": [intent_id],
        "keywords": keywords,
        "examples": examples,
        "notes": {},
    }
    if tags:
        manifest["tags"] = tags
    intents_data = load_json(INTENTS_FILE, {"schemaVersion": 1, "categories": {}, "intents": []})
    update_intent(
        intents_data, intent_id, args.skill_id, args.description.strip(),
        args.category, patterns, keywords, examples,
    )

    plan = {
        "skill": str(folder),
        "skill_file": str(folder / "SKILL.md"),
        "manifest": str(folder / "manifest.json"),
        "intent": intent_id,
        "tags": tags,
        "ignore": ignore,
        "variants": [{"agent": a, "source": str(p)} for a, p in variants],
        "dry_run": bool(args.dry_run),
    }
    if args.dry_run:
        print(json.dumps({"ok": True, **plan}, ensure_ascii=False, indent=2))
        return 0

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
    write_json(folder / "manifest.json", manifest)
    write_json(INTENTS_FILE, intents_data)
    for agent in ignore:
        (folder / f"SKILL.{agent}.ignore").write_text("", encoding="utf-8")
    for agent, source in variants:
        (folder / f"SKILL.{agent}.md").write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )

    index_output = ""
    if not args.dry_run:
        proc = subprocess.run(
            [sys.executable, str(STORE / "scripts" / "store.py"), "--store", str(STORE)],
            cwd=str(STORE), capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        index_output = (proc.stdout or proc.stderr or "").strip()
        if proc.returncode != 0:
            fail("索引刷新失败：" + index_output)
    result = {"ok": True, **plan, "index": index_output}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"created {args.skill_id}")
        print(f"  intent: {intent_id}")
        print(f"  ignore: {', '.join(ignore) or '-'}")
        print(f"  index: {index_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
