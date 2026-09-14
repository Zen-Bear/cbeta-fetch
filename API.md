# cbeta-fetch API（v0.1.0）

纯标准库；无宿主依赖。所有函数不打印、不假设目录布局。

## work id

### `is_work_id(s) -> bool`
接受任意大小写。语法：`CANON + (\d{4}[a-zA-Z]? | [ABa]\d{3})`。
例：`T0349` `A1057` `T0128a` `TXa001` `JB005`。

### `parse_work_id(work_id) -> (canon, no)`
`canon` 转大写、`no` **保留原大小写**；非法抛 `ValueError`。
例：`parse_work_id("txa001") == ("TX", "a001")`；`parse_work_id("T0128A") == ("T", "0128A")`。

### `canonical_work_id(work_id, catalog=None) -> str`
按 catalog 原始大小写规范化（`canon` 大写 + `no` 原样）；catalog 未命中 → 原样返回。
例：`canonical_work_id("TXA001", cat) == "TXa001"`。

## catalog

### `catalog_lookup(catalog, canon, no) -> list[dict]`
读 `sutra_mapping.txt`（8 列 `canon,vol,no,juan,first_juan,first_lb,name,byline`）。
canon/no **大小写不敏感**；返回项保留 catalog 原始大小写：
`{"vol","no","file","title"}`（`file = {canon}{vol}n{no}.xml`）。文件缺失 → `[]`。

## URL

- `DEFAULT_DOWNLOADS`：`xml/html/docx/epub/odt/txt_notes/pdf`
  - `xml`：`{canon}/{canon}{vol}/{file}`（配合 catalog 的 `vol/file`）
  - `html|txt_notes`：`{id}`；`docx|epub|odt|pdf`：`{canon}/{id}`
- `REMOTE_URLS`：元数据/字库更新源（**单源**，宿主 source 表只引用 key）
  `sutra_mapping, bulei, sutralist_json, sutralist_txt, category_json,
   dynasty_works, creators_by_strokes, all_creators, gaiji, sanskrit, supplement_ttf`
- `ALL_FORMATS = ("xml","html","docx","epub","txt_notes","odt")`

## HTTP

### `download(url, dest, *, timeout=90, retries=2, unzip=False, headers=None) -> bool`
- `unzip=False`：`dest` 为文件，父目录自建，写入为 `.part` → `os.replace` **原子替换**。
- `unzip=True`：`dest` 为目录，下载 zip 后平展解压（zip 不留）。
- 使用 **unverified SSL**（cbdata 证书缺 SKI）+ 重试；失败返回 `False`。

### `unzip_flat(zip_path, dest_dir) -> None`
忽略 zip 内目录层次，按 basename 平展解压（防 zip-slip）。

### `fetch_if_changed(url, dest, *, etag=None, last_modified=None, timeout=90, retries=1) -> (status, etag, last_modified)`
条件 GET → `dest`（原子）。`status ∈ {"downloaded","not-modified","failed"}`。

### `probe(url, *, etag=None, last_modified=None, timeout=20) -> (status, etag, last_modified)`
HEAD + 条件头，不落盘。`status ∈ {"changed","not-modified","failed"}`。

## 同步

`tools/sync_into.py <vendor_dir>`：复制 `cbeta_fetch.py` + 写 `SOURCE.txt`
（`repo/commit/version/sha256`）。宿主项目以 sha256 校验测试防手改。
