# agent-library-skill-create

一条命令创建 / 入库一个 [agent-library](#agent-library-是什么) skill：同时生成 `SKILL.md`、
`manifest.json`、intent（以及需要时的 Agent 覆盖文件），并刷新 catalog 索引。
默认所有 Agent 可见，不需要复制任何文件到各 Agent 自己的目录。

这就是一个 skill 的源码仓库：`SKILL.md` 是 skill 本体，`scripts/create_skill.py` 是
它调用的创建脚本，`references/schema.md` 是字段与覆盖规则参考。

## agent-library 是什么

agent-library（下文简称 aglib）是一套把 skill / rule 集中管理的目录约定：

- **单一来源**：所有 skill 只存在于一个 catalog 里，Agent 侧只放一个 `agentlib-router`
  来按意图查找并读取，不再把 `SKILL.md` 复制到 `~/.cursor/skills`、`~/.dsh/skills` 等位置。
- **catalog 结构**：每个 skill 一个目录，外加一份 intent 表用于路由。

```text
<AGLIB_STORE>/
├─ catalog/
│  ├─ agents.json            # 已知 Agent 列表（--ignore / --variant 的名字必须在这里）
│  ├─ intents.json           # 意图表：patterns / keywords / examples -> skills
│  ├─ index.json             # 由 store.py 刷新出来的索引
│  └─ <id>/
│     ├─ SKILL.md            # 正文（含 name/description frontmatter）
│     ├─ manifest.json       # 元数据：kind/mode/when/requires/intents/tags...
│     └─ SKILL.<agent>.md    # 可选：某 Agent 专用正文
│        SKILL.<agent>.ignore # 可选：空文件，表示该 Agent 看不到这个 skill
└─ scripts/
   ├─ store.py               # 刷新 catalog/index.json
   ├─ eval_router.py         # 路由评测
   └─ manage_ui.py           # 可视化管理前端
```

- **默认所有 Agent 可见**：只有某个 Agent 确实需要例外时，才加 `--ignore`（看不到）
  或 `--variant`（不同正文），而不是复制整套 skill。
- **intent 与 skill 解耦**：一个 intent 可以挂多个 skill；默认 `intent.id == skill.id`。

## 这个仓库包含什么

| 路径 | 作用 |
| --- | --- |
| `SKILL.md` | skill 本体：最短创建路径、默认值、何时才加特例、不要做什么 |
| `manifest.json` | 本 skill 自己的 aglib 元数据（`mode=on-demand`、`category=meta` 等） |
| `scripts/create_skill.py` | 一条命令写 `SKILL.md` + `manifest.json` + intent + 刷新索引 |
| `references/schema.md` | `manifest.json` 字段、intent 结构、Agent 覆盖文件与单一来源规则 |
| `README.md` / `LICENSE` / `.gitignore` | 仓库文档与杂项 |

## 快速开始

### 方式一：把本 skill 放进 agent-library（推荐）

把整个仓库放进 catalog，成为 aglib 里的一个 skill：

```text
<AGLIB_STORE>\catalog\agent-library-skill-create\
```

这样 router 就能在“做一个 skill / 把它入库 / 新建技能或意图”时命中它。
skill 的默认调用方式是读取 `SKILL.md`，再执行其中的命令。

### 方式二：直接用脚本

克隆后直接调用脚本即可，不必先装进 catalog：

```powershell
git clone https://github.com/sprw-li/agent-library-skill-create.git
cd agent-library-skill-create
python scripts/create_skill.py --help
```

脚本在 agent-library 内时的路径为
`catalog\agent-library-skill-create\scripts\create_skill.py`。

### 环境要求

- Python 3.9+（脚本无第三方依赖）。
- 需要 `AGLIB_STORE`（或 `--store`）指向一个已存在的 agent-library 根目录，
  且其中 `catalog\` 目录存在；刷新索引还需要 `scripts\store.py`。
  若根目录里还没有 `catalog\`，脚本会直接报 `catalog 不存在`，退出码非 0。

### 建一个 skill

```powershell
# 让脚本自己定位 aglib 根目录（AGLIB_STORE -> ~/.agent-library -> 按脚本位置推导）
python scripts/create_skill.py `
  --id my-skill `
  --description "一句话说明它做什么、什么时候用" `
  --when "用户说 X 时使用" `
  --when-not "只是评估已有 skill 时不要用" `
  --category general `
  --pattern "X|Y" `
  --keyword "关键词" `
  --example "用户会怎么说" `
  --body-file path\to\my-skill.md

# 或者显式指定根目录
python scripts/create_skill.py --store <AGLIB_STORE> --id my-skill --description "..."

# 先看会写什么，不落盘、不刷索引
python scripts/create_skill.py --store <AGLIB_STORE> --id my-skill --description "..." --dry-run
```

不传 `--body-file` / `--body` 时会生成正文骨架，之后编辑
`<AGLIB_STORE>\catalog\my-skill\SKILL.md` 即可。

一个故意使用特例的例子：

```powershell
python scripts/create_skill.py `
  --store <AGLIB_STORE> `
  --id my-local-skill `
  --description "仅在本机验证过的流程" `
  --local-only `
  --ignore dsh `
  --variant cursor=path\to\cursor-version.md
```

## 参数表

| 参数 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--store` | 否 | `$env:AGLIB_STORE` → `~/.agent-library` → 按脚本位置推导 | agent-library 根目录；该目录下必须存在 `catalog/` |
| `--id` | 是 | — | skill id，小写 kebab-case，同时是 `catalog/<id>/` 目录名 |
| `--description` | 是 | — | 一句话说明它做什么、什么时候用；写入 frontmatter 与 manifest |
| `--when` | 否 | `--description` | 触发场景，可重复（`action="append"`） |
| `--when-not` | 否 | 空 | 不触发场景，可重复 |
| `--category` | 否 | `general` | intent 分类，小写 kebab-case |
| `--pattern` | 否 | `re.escape(--id)` | intent 正则，可重复或逗号分隔 |
| `--keyword` | 否 | 空 | intent 关键词，可重复或逗号分隔 |
| `--example` | 否 | 空 | intent 用户话术样例，可重复 |
| `--body-file` | 否 | 空 | 正文文件；读取后作为 `SKILL.md` 正文（没有 frontmatter 会自动补） |
| `--body` | 否 | 空 | 直接传正文；与 `--body-file` 都没给时生成骨架 |
| `--intent` | 否 | 与 `--id` 同名 | 复用已有 intent，把 skill 追加进去；id 必须小写 kebab-case |
| `--ignore` | 否 | 空 | 让某个 Agent 看不到：生成空的 `SKILL.<agent>.ignore`；名字必须在 `catalog/agents.json` |
| `--variant` | 否 | 空 | 某个 Agent 用不同正文：`--variant cursor=文件路径`；名字必须在 `catalog/agents.json` |
| `--tags` | 否 | 空 | manifest `tags`，可重复或逗号分隔 |
| `--local-only` | 否 | 关闭 | 等价 `--tags 限本机`，表示只在本机验证过 |
| `--requires` | 否 | `filesystem-read` | 能力声明，可重复；允许 `filesystem-read` / `filesystem-write` / `shell` / `network` / `secrets` |
| `--mode` | 否 | `on-demand` | `on-demand` 或 `resident` |
| `--dry-run` | 否 | 关闭 | 只打印计划（JSON），不写文件、不刷索引 |
| `--force` | 否 | 关闭 | 允许覆盖已存在的 skill 目录（正文 / manifest） |
| `--json` | 否 | 关闭 | 以 JSON 输出结果（包含 `plan` 与 `index` 输出） |

`--ignore` / `--variant` 的 `<agent>` 必须已登记在 `catalog/agents.json`，否则脚本报
`未知 agent`；`--variant` 的源文件缺失或疑似含密钥（`sk-...`、`ghp_...`、`AKIA...`）也会拒绝。

## 默认值

- `--intent` 默认与 skill id 同名；复用已有 intent 时用 `--intent create-skill` 之类；
- 默认所有 Agent 可见，不写任何 `SKILL.<agent>.md` / `SKILL.<agent>.ignore`；
- 默认 `requires=["filesystem-read"]`；
- 默认 `mode=on-demand`；
- 默认不写 `tags`；只在本机验证过时加 `--local-only`（等价 `--tags 限本机`）；
- 单次提交只写 `catalog/<id>/`、`catalog/intents.json` 与 `catalog/index.json`。

## 创建后自检

```powershell
# 若你的库带校验脚本，用它检查新条目（路径以你的库为准）
python <AGLIB_STORE>\scripts\check_skill.py <AGLIB_STORE>\catalog\my-skill
python <AGLIB_STORE>\scripts\eval_router.py
python <AGLIB_STORE>\scripts\manage_ui.py   # 可视前端确认路由与展示
```

## 不要做什么

- 不要为了“让 Agent 看到”把 skill 复制到各 Agent 目录（`~/.cursor/skills`、`~/.dsh/skills` 等）；
- 不要先手改 `catalog/intents.json` 再补 skill，交给脚本或按 schema 同步改；
- 不要把 `SKILL.<agent>.ignore` 当成隐藏正文的替代品——它只是路由层的可见性开关；
- 不要在 skill 正文、`--body-file`、`--variant` 文件里写登录 token、cookie、密钥
  （脚本会拒绝明显密钥，但不要依赖它兜底）；
- 不要把某个固定路径当作唯一路径写死在流程里，用 `AGLIB_STORE` / `--store`。

## 与 agent-library 的关系

本仓库是 aglib 的一个 skill，不包含 aglib 本体（`store.py`、`eval_router.py`、
`manage_ui.py`、router 等）。没有 aglib 根目录时，脚本可用于 `--dry-run` 以外的
写入会因缺少 `catalog/` 而退出；请先准备好 agent-library 根目录。

## License

[MIT](LICENSE) © 2026 Morrow
