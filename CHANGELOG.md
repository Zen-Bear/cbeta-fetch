# CHANGELOG

## 0.1.1
- 新增 `probe_info(url, ...) -> dict`（HEAD + 条件头，返回
  `{status, etag, last_modified, size}`；`size` 取 `Content-Length`）。
  `probe` 保持三元组签名、改为其薄封装（向后兼容）。

## 0.1.0
- 首版：work id（`is_work_id`/`parse_work_id`/`canonical_work_id`，canon 大写、no 原样）、
  `catalog_lookup`（大小写不敏感、原大小写返回）、`DEFAULT_DOWNLOADS`（含 `pdf`）、
  `REMOTE_URLS` 元数据单源、`download`（原子/可解压）、`unzip_flat`、
  `fetch_if_changed`、`probe`；纯标准库；`tools/sync_into.py` vendor 同步。
