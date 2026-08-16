---
name: docx
description: 处理 Word 文档（.docx）——新建、读取、追加、替换文本。当用户提到"Word 文档 / docx / 报告 / 文档"时使用。
---

操作 Word 文档时使用以下工具：

- `docx_create`：新建文档。`content` 传多行字符串，`# ` 开头是一级标题、`## ` 是二级标题、普通行是段落。
- `docx_read`：读取文档全部文本（含表格）。
- `docx_append`：在末尾追加一段文字。
- `docx_replace`：替换文档里的文本（按段落 run 替换，跨 run 的文本可能替换不到，若失败改用 `docx_create` 重写）。

建议流程：先 `docx_read` 看现状 → 按需 `docx_append`/`docx_replace` 修改；若要全新内容，直接 `docx_create`。
删除文档用文件工具的 `delete_file`。
