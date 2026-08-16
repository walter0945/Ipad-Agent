# iPad 本地 AI Agent 设计文档（Spec）

> 状态：待用户评审
> 日期：2026-08-15
> 方法论：superpowers（brainstorming）→ grilling 访谈收敛 → 本文档

## 1. 目标（Goal）

构建一个运行在 iPad（a-Shell 宿主）内的**本地 AI agent**：调用主流 LLM API（DeepSeek/Qwen/Grok/OpenAI/Claude 等），能读写本地文件与表格、调用声明式 skill、通过分级权限门控执行操作，并支持会话持久化。定位为"个人/商家效率型 FDE 助手"——以表格处理、内容生成、数据整理为最高频价值点。

## 2. 非目标（Non-goals，明确不做）

- 不在 v1 实现视频生成（放 v1.1）。
- 不尝试驱动剪映等第三方 App（iOS 沙盒不可行）。
- 不在 iPad 本地跑 Remotion（依赖 Node.js + Chromium，iPad 不可行）。
- 不做定时/后台常驻自动化（iOS 挂起限制，放 v2 云端组件）。
- 不"包装 Claude Code / Codex CLI 产品"（那是调用外部 CLI agent 的另一方案，放 v2 讨论）；v1 只接**模型 API**。

## 3. 技术栈与运行时（已核实，锁定）

| 项 | 决定 | 依据 |
|---|---|---|
| 运行时 | **a-Shell** | 原生 CPython 3 + 内置 ffmpeg；iSH 文件互通弱（无法挂 iCloud）+ x86 模拟慢 5–20 倍，已排除 |
| 语言/框架 | **纯 Python 手写工具循环** | 不用 LangChain/LangGraph，保证 a-Shell 可 pip 部署、依赖最小、可移植 |
| 模型默认 | **deepseek-chat** | 工具调用稳定、便宜、快 |
| 依赖（v1） | 仅纯 Python 包：`requests`、`openpyxl`、`rich`、`python-dotenv` | openpyxl/requests/rich 为纯 Python；Pillow 留到 v1.1 再编译一次 |
| 开发/验证 | Windows 本机（Python 3.12）+ pytest | 纯 Python 全平台一致，先本机跑通再拷入 a-Shell |

## 4. Provider 抽象层（LLM 客户端）

### 4.1 分类原则

所有主流模型 API 只分两种协议，抽象层只需两个适配器：

- **OpenAICompatAdapter**：覆盖 `deepseek / qwen / grok / openai(codex) / kimi / glm / minimax / ollama / openrouter` 等一切 OpenAI 兼容服务。
- **AnthropicAdapter**（可选）：原生 Anthropic `/v1/messages`。默认不启用——Claude 建议走 OpenRouter 或 Anthropic 的 OpenAI 兼容层，以复用同一套工具协议。

### 4.2 预设表（config 内置）

| Provider | base_url | 默认模型 |
|---|---|---|
| deepseek | `https://api.deepseek.com` | `deepseek-chat` |
| qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| grok | `https://api.x.ai/v1` | `grok-4` |
| openai | `https://api.openai.com/v1` | `gpt-5-codex` |
| openrouter | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4-5` |
| anthropic | `https://api.anthropic.com` | `claude-sonnet-4-5` |

### 4.3 配置（.env）

```dotenv
PROVIDER=deepseek            # 预设键；未列出的 OpenAI 兼容服务用下面三项覆盖
LLM_BASE_URL=                # 留空用预设默认
LLM_API_KEY=sk-...           # 手动粘贴，绝不写进代码
LLM_MODEL=                   # 留空用预设默认模型
```

`config.py` 内置预设表 + 三项覆盖。换模型只改 `PROVIDER` 或三项覆盖，零代码改动。`.env` 进 `.gitignore`。

### 4.4 工具调用协议

统一走 OpenAI function-calling JSON（`tools`/`tool_calls`）。Claude 原生走 `tool_use` 块格式不同，故默认经 OpenAI 兼容层进入，保证所有 provider 共用同一套工具协议。

## 5. 架构（分层，参考 Apple Intelligence 四层）

```
┌ 用户 ──────────────────────────────┐
│  a-Shell 终端（v1）/ 本地 WebUI（v1.1）│
└──────────────┬────────────────────┘
┌──────────────▼────────────────────┐
│ agent.py      编排循环（ReAct/工具调用）│
│ llm.py        Provider 抽象客户端     │
│ permissions.py 分级权限门控           │
│ session.py    会话持久化 + 80% 压缩   │
│ config.py     provider 预设 + .env    │
└──────────────┬────────────────────┘
   tools/  ← 意图注册表（启动扫描注入）
   ├─ files.py       read/write/edit/list/grep/glob
   ├─ spreadsheet.py openpyxl 读写 xlsx/csv
   ├─ shell.py       a-Shell 安全 shell
   └─ search.py      web_search / read_url
   skills/  ← 声明式技能（SKILL.md + 工具模块）
```

## 6. 数据流

```
用户输入
  → 组装 system prompt（基础规则 + skills 注册表 + 权限说明 + provider 上下文）
  → LLM 返回 content 或 tool_calls
  → 有 tool_calls：过 permissions 门控 → 执行工具 → 结果回填 → 再调 LLM
  → 无 tool_calls：输出最终答复 → 写入 session 持久化
```

## 7. 工具集（v1）

### 7.1 文件
- `read_file`（支持行区间）、`write_file`、`edit_file`（精确查找替换）、`list_dir`、`grep`、`glob`

### 7.2 表格（核心价值点）
- `sheet_list`（列出 xlsx/csv 文件）、`sheet_read`（读区域/表头）、`sheet_write_cell`、`sheet_add_row`、`sheet_summary`（行数/列名/类型推断）

### 7.3 Shell
- `run_shell`：a-Shell 安全化——拦截 `|`、`$()`、反引号、`&`（会卡死 a-Shell），把 `&&`/`||`/`;` 拆开顺序执行

### 7.4 搜索
- `web_search`（DuckDuckGo）、`read_url`（网页 → Markdown）

## 8. Skill 机制（superpowers 格式）

每个 skill 一个目录：`SKILL.md`（frontmatter：`name`/`description`/`when-to-use`，正文写"何时用、怎么用"）+ 对应工具。agent 启动时扫描 `skills/`，把每个 SKILL.md 声明注入系统提示，模型"识别场景 → 选择调用对应工具"。

## 9. 权限门控（a-agent 缺失、Apple 式补齐）

| 操作 | 门控 |
|---|---|
| 读（文件/表格/列表） | 免确认 |
| 写/修改 | 确认 |
| 删除/覆盖/清空 | 强确认 |
| run_shell | 命令白名单（允许的前缀/模式列表，如 `ls`/`python3`/`ffmpeg`）+ 确认 |
| 所有文件操作 | 限沙盒根目录内 |
| 密钥文件 | `.env`/`.pem`/`.key` 等过滤 |

## 10. 会话持久化与上下文压缩

- 会话历史落盘（JSONL），支持断点恢复。
- 历史接近模型上限 80% 时自动总结压缩，保留关键事实。

## 11. 错误处理

- LLM：`429/5xx` 指数退避重试、`timeout`。
- `401`（key 无效/余额不足）与 `429/5xx` 分开提示，不同 provider 的 key 问题一眼可见。
- SSL 报错时回退 `SSL_CERT_FILE` 指向 certifi（a-Shell 直连 api.deepseek.com 的已知兜底）。

## 12. 目录结构

```
D:\Agent\ipad-agent\
├─ agent.py            # 主循环入口
├─ llm.py              # Provider 抽象客户端
├─ permissions.py      # 权限门控
├─ session.py          # 会话持久化/压缩
├─ config.py           # provider 预设 + .env
├─ tools\
│  ├─ __init__.py      # registry：扫描注册
│  ├─ files.py
│  ├─ spreadsheet.py
│  ├─ shell.py
│  └─ search.py
├─ skills\
│  └─ spreadsheet\SKILL.md
├─ tests\              # pytest（每工具一个测试文件）
├─ requirements.txt
├─ .env.example
└─ README.md
```

## 13. 测试策略（TDD）

- `pytest`，Windows 本机跑。
- 每个工具**先写失败测试再实现**。
- 每个 provider 一个冒烟测试：问一句 → 调一个工具 → 回填 → 断言最终答复（验证"兼容 ≠ 行为一致"的差异）。

## 14. 分阶段范围

- **v1（本次）**：编排循环 + Provider 抽象 + 文件/表格/搜索工具 + skill 加载器 + 权限门控 + 会话持久化。产出"Windows 可跑 + 可拷进 a-Shell"的 agent。
- **v1.1**：视频工具（Pillow 编译一次 + 原生 ffmpeg）、本地文件索引、混合路由（chat/reasoner 分流）、Web UI。
- **v2**：云端调度/连接器（FDE 定时自动化 + 平台 API）、多端同步。

## 15. 部署路径

1. Windows 本机 `pip install -r requirements.txt` → 填 `.env` → `pytest` 全绿 → `python agent.py` 对话验证。
2. 拷入 a-Shell：`pip install requests openpyxl rich python-dotenv` → 放文件 → 用 `SSL_CERT_FILE` 兜底 → 在 Documents/iCloud 目录读写表格。

## 16. 假设（Assumptions）

- 用户已有（或能创建）DeepSeek/Qwen 等任一 provider 的 API key。
- 表格格式为 `.xlsx`/`.csv`（Apple Numbers 的 `.numbers` 私有格式不支持，需先导出）。
- v1 交互为 a-Shell 终端（rich 流式输出 + Thinking 显示）。
