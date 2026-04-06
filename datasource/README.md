# Datasource Layer

该模块负责从 PostgreSQL `news` 表读取新闻，并转换为 `preprocess` 可直接消费的文档结构。

## 结构

- `news_repository.py`：数据库读取（分页/增量/按条件）
- `preprocess_adapter.py`：字段对齐转换（`NewsRecord` -> preprocess document）
- `service.py`：上层服务封装，供主流程直接调用

## 依赖配置

默认读取 `core.config.Settings.database_url`（环境变量 `DATABASE_URL`）。

示例（请在运行环境设置，不要硬编码到代码）：

- `postgresql://news_user:***@8.146.227.206:5432/news_db`

## 输出契约（对齐 preprocess）

每条文档输出字段：

- `doc_id`：`news-{id}`
- `news_id`
- `url`
- `title`
- `raw_text`（来自 `news.content`）
- `source_name`
- `source_type`
- `publish_date`（优先 `news.publish_date`，否则回退 `crawled_at`）
- `author`

这些字段可直接用于句子切分与后续语义分块流程。