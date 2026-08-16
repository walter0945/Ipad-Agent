# ipad-agent（a-Shell 版）

运行在 iPad 本地的 AI agent：纯 Python，无第三方框架依赖。支持 DeepSeek/Qwen/Grok/OpenAI/OpenRouter/自定义等多模型，内置文件、表格、Word、视频、搜索、代码执行、跨 App 等工具，带权限门控、skill 系统、混合路由与会话持久化。可在 Windows 开发、部署到 iPad 的 [a-Shell](https://holzschu.github.io/a-Shell_iOS/) 运行。

> 姊妹项目：[`ipad-agent-web`](../ipad-agent-web) 是它的网页版（后端复用本仓库代码，iPad Safari 当界面）。两者能力一致，本版是"iPad 本地独立跑"，web 版是"电脑/服务器跑、iPad 当界面"。

---

## 一、能力范围（能做什么）

| 类别 | 工具 / 能力 |
|---|---|
| **表格** xlsx/csv | `sheet_list` `sheet_read` `sheet_write_cell` `sheet_add_row` `sheet_summary` `sheet_delete`（读/写/追加/删工作表/结构概览+类型推断） |
| **Word** .docx | `docx_read` `docx_create` `docx_append` `docx_replace` |
| **文件** | `read_file` `write_file` `edit_file` `list_dir` `grep` `glob` `file_index` `delete_file` |
| **视频** | `render_video`（分镜 JSON → Pillow 逐帧 → ffmpeg 合成 mp4） |
| **搜索** | `web_search`（DuckDuckGo）`read_url`（网页→文本） |
| **代码/命令** | `run_shell`（白名单 `ls/python3/ffmpeg/cat/git` + 确认）`run_python`（写临时文件运行，返回 stdout/stderr） |
| **跨 App 桥接** | `run_shortcut` `open_url`（经 iOS 捷径/URL scheme，仅 iOS/a-Shell 有效） |
| **skill** | 内置 `spreadsheet`/`video`/`docx`；`--install-skill <url>` 从 GitHub 装指令型技能 |
| **模型** | 多 Provider，默认 `deepseek-v4-flash`，推理模型 `deepseek-v4-pro` |
| **混合路由** | 推理类提示（分析/为什么/对比…）自动切推理模型 |
| **会话** | JSONL 持久化、自动摘要压缩、发送前序列校验（根治 400） |

## 二、运行模式

```bash
python3 agent.py                        # 交互模式：连续对话，/clear 清空，/quit 退出
python3 agent.py "列出表格"              # 单次模式：跑完即退，写/删/执行默认拒绝
python3 agent.py "整理台账" --yes        # 单次并自动放行所有操作
python3 agent.py --install-skill <url>   # 从 GitHub 装 skill
```

交互模式下，写/删/执行会弹**三选项确认**：
`[1] 确认本次` `[2] 确认所有(后续自动执行)` `[3] 拒绝`——选 2 后本会话不再询问（适合 vibe coding 放手跑）。

## 三、行为边界（不能做什么 / 受什么限制）

1. **不直接控制第三方 App**：iOS 沙盒禁止，只能经捷径/URL scheme 请求对方已暴露的动作（多数会切前台、需对方 App 在场）。
2. **文件只限沙盒目录** `workspace/`：越界（`../`、绝对路径、盘符）被拒；密钥文件（`.env`/`.pem`/`.key`/`.p12`/`id_rsa`/`credentials`）不可读写。
3. **权限门控**：读免确认；写确认；覆盖/删除/执行 Python 强确认；shell 白名单+确认。
4. **后台会被挂起**：iOS 切走 a-Shell 前台即暂停，长任务需保持前台/亮屏；定时自醒要靠"捷径"App 的自动化。
5. **不支持**：Remotion（需 Node+Chromium）、剪映等 GUI 自动化、Apple Numbers 的 `.numbers`（需先导出 xlsx/csv）。
6. **工具轮数上限**：单次任务最多 20 轮工具循环。

## 四、部署方法

### 4.1 在 Windows 本机开发/验证

```powershell
pip install -r requirements.txt
copy .env.example .env      # 填入 LLM_API_KEY（见 §六）
python agent.py             # 交互模式
python -m unittest discover -s tests   # 跑测试
```

### 4.2 部署到 iPad（a-Shell）

**① 装 a-Shell**：App Store 搜 a-Shell。

**② 获取代码**（二选一）：

```bash
# 方式 A：git clone（a-Shell 需先 pkg install git，其 git 是 lg2 简化版）
cd ~/Documents
git clone https://github.com/walter0945/Ipad-Agent.git

# 方式 B：curl 下载（无需 git，一条一行，别用 && 串）
cd ~/Documents
curl -L -o t.tar.gz https://github.com/walter0945/Ipad-Agent/archive/refs/heads/master.tar.gz
tar -xzf t.tar.gz
```

**③ 装依赖**：

```bash
cd Ipad-Agent   # 或你 clone 出来的目录名
python3 -m pip install requests openpyxl python-dotenv
# 视频功能加 Pillow，Word 加 python-docx（两者在 a-Shell 首次安装需现场编译几分钟）
python3 -m pip install Pillow python-docx
```

**④ 配置**：在项目目录建 `.env`（不要用 heredoc，用 echo 逐行写）：

```bash
echo "PROVIDER=deepseek" > .env
echo "LLM_API_KEY=sk-你的key" >> .env
```

**⑤ 运行**：

```bash
python3 agent.py
```

**⑥ 常见问题**：
- SSL 报错：`export SSL_CERT_FILE=$(python3 -c "import certifi;print(certifi.where())")`（llm.py 也内置了自动回退）。
- 交互输入无响应：先跑 `python3 diag_input.py` 分诊，或改用单次模式 `python3 agent.py "问题"`。
- 更新代码：`git pull`（或重跑 curl+tar 覆盖）。

### 4.3 把表格放进来

agent 操作的是项目下 `workspace/`。把 `.xlsx`/`.csv` 复制进去，或从"文件"App 的 a-Shell 目录导入；写出的文件也在 `workspace/`，可在"文件"App 里查看/导出。

## 五、风险情况（务必读）

| 风险 | 说明 | 缓解 |
|---|---|---|
| **API key 泄露** | key 明文存 `.env` | 已 gitignore；别提交/分享 |
| **任意代码执行** | `run_python`/`run_shell` 真会执行代码/命令 | 每次确认并展示原文；沙盒+密钥/越界扫描 |
| **不是硬隔离** | shell/Python 的沙盒是"知情同意+防手滑"，非 OS 级进程隔离；动态拼接路径可能绕过启发式 | **不要对不理解的命令点确认**；真正的防线是执行前的确认 |
| **LLM 无护栏** | 模型可能幻觉/给错内容 | 它做的删除/覆盖有强确认；人工把关 |
| **文件误删/误改** | 覆盖、删除动真实文件 | 强确认；重要文件先备份 |
| **网络请求** | `web_search`/`read_url` 会访问外部地址 | 正常用途即可 |
| **依赖编译** | Pillow、python-docx→lxml 首次安装需现场编译几分钟 | 一次性成本 |

## 六、配置（.env）

| 变量 | 默认 | 说明 |
|---|---|---|
| `PROVIDER` | `deepseek` | deepseek / qwen / grok / openai / openrouter / anthropic / custom |
| `LLM_BASE_URL` | 空 | 自定义时填；留空用预设 |
| `LLM_API_KEY` | （必填） | 模型 API key |
| `LLM_MODEL` | 空 | 留空用预设默认模型 |
| `LLM_REASONER_MODEL` | 空 | 留空用预设推理模型 |

## 七、目录结构

```
ipad-agent/
├─ agent.py           # 编排循环 + CLI 入口
├─ llm.py             # Provider 抽象客户端（重试/401/SSL/错误正文透传）
├─ config.py          # Provider 预设 + .env
├─ permissions.py     # 权限门控（沙盒/密钥过滤/越界扫描）
├─ session.py         # 会话持久化 + 压缩 + 序列校验
├─ router.py          # 混合路由（chat/reasoner）
├─ index.py           # 本地文件索引
├─ skill_install.py   # GitHub 安装 skill
├─ skills/            # 内置 skill（spreadsheet/video/docx）
├─ tools/             # 文件/表格/docx/视频/搜索/shell/跨App 工具
├─ tests/             # 单元测试
├─ requirements.txt
└─ .env.example
```

## 八、测试

```bash
python -m unittest discover -s tests
```
