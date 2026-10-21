# CHANGELOG

## 0.2.0
- TLS：所有主机默认校验证书；cbdata 只清 `VERIFY_X509_STRICT` 这一个附加检查位
  （`verify_mode=CERT_REQUIRED`、`check_hostname=True` 保持开启），
  不再使用 `ssl._create_unverified_context()`；其它主机严格。
- 下载改分块流式：`download`/`fetch_if_changed` 用 1 MiB 分块写 `.part`，
  成功后 `os.replace`；失败清理；`.part` 名加随机后缀，避免同进程并发撞名。
- 响应带 `Content-Length` 时校验实际写入字节数；短读视为失败并重试
  （`shutil.copyfileobj` 遇到短响应不会抛异常，必须显式校验）。
- `unzip=True`：先落临时 zip，再 `unzip_flat` 平展解压；解压错误直接失败、不重试。
  解压原子性与同名策略延后到第二批（本版保持后者覆盖）。
- 新增 `probe_status(url, timeout=20) -> int|None`（HEAD 状态码；共用同一套 TLS 上下文），
  供宿主做 404/410 快判。
- `_ctx()` 保留为兼容函数，返回默认校验上下文（不再全局 unverified）。

## 0.1.2
- `REMOTE_URLS` 新增 `vol_json`（`scope-selector/vol.json`：刊本→册→经）。

## 0.1.1
- 新增 `probe_info(url, ...) -> dict`（HEAD + 条件头，返回
  `{status, etag, last_modified, size}`；`size` 取 `Content-Length`）。
  `probe` 保持三元组签名、改为其薄封装（向后兼容）。

## 0.1.0
- 首版：work id（`is_work_id`/`parse_work_id`/`canonical_work_id`，canon 大写、no 原样）、
  `catalog_lookup`（大小写不敏感、原大小写返回）、`DEFAULT_DOWNLOADS`（含 `pdf`）、
  `REMOTE_URLS` 元数据单源、`download`（原子/可解压）、`unzip_flat`、
  `fetch_if_changed`、`probe`；纯标准库；`tools/sync_into.py` vendor 同步。
