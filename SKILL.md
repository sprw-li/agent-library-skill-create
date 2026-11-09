---
name: agent-library-skill-create
description: >-
  一条命令创建/入库 agent-library skill：生成 SKILL.md、manifest、intent，
  默认所有 Agent 可见；只有确实需要时才加 ignore 或特殊版本。用户说“做一个 skill”、
  “把它入库”、“新建技能/意图”时使用，不要先走 skill-creator 的长评估流程。
---

# agent-library skill create

这是 aglib 的**最短创建路径**。目标是让新 skill 一次成型，而不是先手写 intent、再复制到各 Agent 目录、再补 ignore。

## 最短路径

在 agent-library 根目录（下称 `<AGLIB_STORE>`）的任意位置运行本仓库的脚本；
如果本 skill 已放进 catalog，路径是 `catalog/agent-library-skill-create/scripts/create_skill.py`。

```powershell
python scripts/create_skill.py `
  --id my-skill `
  --description "一句话说明它做什么、什么时候用" `
  --when "用户说 X 时使用" `
  --category general `
  --pattern "X|Y" `
  --keyword "关键词" `
  --body-file path\to\my-skill.md
```

脚本用环境变量 `AGLIB_STORE` 或参数 `--store` 定位 agent-library 根目录；
两者都没给时先试约定位置 `~/.agent-library`，再回退到按脚本位置推导。
换机器时只设环境变量即可：

```powershell
$env:AGLIB_STORE = '<AGLIB_STORE>'   # 例如 ~/.agent-library；也可用 --store <AGLIB_STORE>
```

不传 `--body-file` 会生成正文骨架，之后再编辑：

```text
<AGLIB_STORE>\catalog\my-skill\SKILL.md
```

脚本同时写：

```text
catalog/my-skill/manifest.json
catalog/intents.json
catalog/index.json（调用 store.py）
```

## 默认值

- 默认 `intent` 与 skill id 同名；已有 intent 用 `--intent create-skill` 复用；
- 默认所有 Agent 可见，不写任何 `SKILL.<agent>.md`/`.ignore`；
- 默认 `requires=["filesystem-read"]`；
- 默认 `mode=on-demand`；
- 默认不写 `tags`；只在本机验证过时加 `--local-only`（等价 `--tags 限本机`）；
- 不复制到 `~/.cursor/skills`、`~/.dsh/skills` 等 Agent 目录，单一来源始终是 `catalog/`。

## 只有这几种情况才加特例

### 某个 Agent 不该看到

```powershell
--ignore dsh,qoder-cn
```

生成空的 `SKILL.dsh.ignore`、`SKILL.qoder-cn.ignore`；不要复制整个 skill。

### 某个 Agent 需要不同正文

```powershell
--variant cursor=path\to\cursor-version.md
```

生成 `SKILL.cursor.md`；原版仍是 `SKILL.md`。

### 想先看要写什么

```powershell
--dry-run
```

只打印计划，不写文件、不刷索引。

## 创建后

```powershell
# 若你的库带校验脚本，用它检查新条目（路径以你的库为准）
python <AGLIB_STORE>\scripts\check_skill.py <AGLIB_STORE>\catalog\my-skill
python <AGLIB_STORE>\scripts\eval_router.py
```

再在可视前端确认：

```powershell
python <AGLIB_STORE>\scripts\manage_ui.py
```

## 不要做

- 不要为了“让 Agent 看到”把 skill 复制到各 Agent 目录；
- 不要先手改 `intents.json` 再补 skill；
- 不要把 ignore 当成隐藏正文的替代品；
- 不要在 skill 里写登录 token、cookie、密钥。

字段和覆盖文件规则见 `references/schema.md`。
