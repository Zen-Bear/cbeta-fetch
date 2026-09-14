# CHANGELOG

## 0.1.0
- 首版：work id（`is_work_id`/`parse_work_id`/`canonical_work_id`，canon 大写、no 原样）、
  `catalog_lookup`（大小写不敏感、原大小写返回）、`DEFAULT_DOWNLOADS`（含 `pdf`）、
  `REMOTE_URLS` 元数据单源、`download`（原子/可解压）、`unzip_flat`、
  `fetch_if_changed`、`probe`；纯标准库；`tools/sync_into.py` vendor 同步。
