---
name: spreadsheet
description: 处理本地 xlsx/csv 表格——读取、改单元格、追加行、看结构。当用户提到"表格/Excel/数据/台账/订单/清单"时使用。
---

调用顺序建议：先 `sheet_list` 找到文件 → `sheet_summary` 看结构 → `sheet_read` 读内容 → 按需 `sheet_write_cell` / `sheet_add_row`。
只处理工作目录内的 `.xlsx` / `.csv`。Apple Numbers 的 `.numbers` 文件不支持，需先导出为 xlsx/csv。
