# ipad-agent

iPad 本地 AI agent：DeepSeek/Qwen/Grok/OpenAI/Claude 等 provider + 文件/表格/搜索/视频/跨-App 工具 + skill + 权限门控 + 会话持久化。纯 Python，可在 Windows 开发、拷入 iPad a-Shell 运行。

## 本机运行

```
pip install -r requirements.txt
cp .env.example .env   # 填入 PROVIDER 与 LLM_API_KEY
python agent.py                       # 交互模式
python agent.py "列出 workspace 里的表格"        # 单次模式（只读，写/删/shell 默认拒绝）
python agent.py "整理台账" --yes                 # 单次模式并自动确认所有操作
```

## 部署到 iPad（a-Shell）

```
pip install requests openpyxl python-dotenv     # 视频功能再加 Pillow（首次需现场编译几分钟）
# 放入 agent 目录，运行 python3 agent.py
# SSL 报错时：export SSL_CERT_FILE=$(python3 -c "import certifi;print(certifi.where())")
```

若 a-Shell 交互输入异常（键盘无响应），先跑 `python3 diag_input.py` 分诊，或改用单次模式。

## 安装 GitHub 上的 skill（只装指令，不下载/执行远程代码）

```
python3 agent.py --install-skill https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md
python3 agent.py --install-skill <raw或blob链接> --force        # 覆盖已存在的同名 skill
```

- 支持 raw 直链、blob 页面链接（自动转 raw）、以及仓库根目录的 SKILL.md。
- 只下载单个 SKILL.md；若正文引用了配套文件（脚本、REFERENCE.md 等），安装后会提示缺失。
- 内置 skill（spreadsheet/video）不允许被远程覆盖。

## 跨 App 自动化

`run_shortcut` / `open_url` 通过 iOS「捷径」与 URL scheme 触发其它 App 的动作（发消息、存相册、驱动第三方 App 已暴露的动作）。这是经系统公开通道「请求」，不是控制进程——沙盒完好。
边界：只能触发对方已暴露的动作；多数会切前台、需对方 App 在场；无法定时自醒（定时靠「捷径」App 的自动化触发器）。

## 安全模型（务必了解）

- **文件工具**：所有读写限沙盒根目录（默认 `workspace/`），密钥文件（`.env`/`.pem`/`.key`/`id_rsa`/`credentials` 等）不可读写。
- **写/删/执行**：写需确认、覆盖/删除需强确认、shell 与 Python 代码需确认并展示原文。
- **`run_shell` / `run_python` 的沙盒是「知情同意 + 防手滑」，不是硬隔离。** 二者靠启发式拦截密钥访问、`..` 穿越与绝对路径，并把命令/代码原文交给你确认后才执行；动态拼接的路径仍可能绕过启发式。真正的防线是执行前的确认——不要对不理解的命令点确认。iOS/a-Shell 无 OS 级进程隔离，Windows 开发机同理。

## 测试

```
python -m unittest discover -s tests
```
