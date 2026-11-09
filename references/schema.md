# 字段与覆盖规则

## manifest.json

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `schemaVersion` | 是 | 当前为 1 |
| `id` | 是 | 小写 kebab-case，同时是目录名 |
| `kind` | 是 | `skill` 或 `rule` |
| `mode` | 否 | `on-demand` / `resident` |
| `when` | 是 | 触发场景，一行一条 |
| `whenNot` | 否 | 不触发场景 |
| `requires` | 否 | `filesystem-read/write`、`shell`、`network`、`secrets` |
| `category` | 否 | 小写 kebab-case |
| `tags` | 否 | 标签数组；`限本机` 表示只在作者本机验证过 |
| `intents` | 否 | 绑定的 intent id |
| `keywords` | 否 | 路由辅助词 |
| `examples` | 否 | 真实用户话术样例 |

### 限本机标签

只在本机环境验证过的 skill/rule，manifest 写：

```json
"tags": ["限本机"]
```

正文开头也写一行 `> **限本机**：...`，说明换机器必须重配/重测。后续 distill 会把 `tags` 里的 `限本机` 抽成路由/展示标签；现在先保证每处写法一致，不要用 `local-only`、`local`、`本机限定` 等变体。

## intent

```json
{
  "id": "my-intent",
  "category": "general",
  "description": "什么时候用",
  "patterns": ["正则"],
  "keywords": ["词"],
  "excludes": ["排除正则"],
  "examples": ["用户会怎么说"],
  "skills": ["my-skill"]
}
```

默认 `intent.id == skill.id`；一个 intent 可以挂多个 skill。创建脚本会：
- 新建 intent，或把 skill 追加到已有 intent；
- 新增分类到 `categories`；
- 调用 `store.py` 刷新索引。

## Agent 覆盖

| 文件 | 作用 |
| --- | --- |
| `SKILL.<agent>.md` | 该 Agent 专用的完整正文 |
| `SKILL.<agent>.ignore` | 该 Agent 完全看不到这个 skill（空文件即可） |

`<agent>` 必须存在于 `catalog/agents.json`。默认不生成任何覆盖文件；不要默认复制整套 skill。

## 单一来源

```text
catalog/<id>/  ← 唯一真源
```

Agent 目录里只放 `agentlib-router`。不要再复制 `SKILL.md` 到 `~/.cursor/skills`、`~/.dsh/skills` 等位置；需要差异时用覆盖文件。
