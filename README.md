# ipad-agent

iPad 本地 AI agent：DeepSeek/Qwen/Grok/OpenAI/Claude 等 provider + 文件/表格/搜索工具 + skill + 权限门控 + 会话持久化。纯 Python，可在 Windows 开发、拷入 iPad a-Shell 运行。

## 本机运行
pip install -r requirements.txt
cp .env.example .env   # 填入 PROVIDER 与 LLM_API_KEY
python agent.py

## 部署到 iPad（a-Shell）
pip install requests openpyxl rich python-dotenv
# 放入 agent 目录，运行 python agent.py；SSL 报错时 export SSL_CERT_FILE=$(python -c "import certifi;print(certifi.where())")
