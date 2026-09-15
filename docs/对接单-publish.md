# publish（`cbeta_publish`）对接单 —— 复用 `cbeta-fetch`

> **状态：已实施（2026-09-14 核对）**。publish 侧已完成本单全部要点：具名包
> `cbeta_publish`、`cbeta_publish/_vendor/{cbeta_fetch.py,SOURCE.txt,__init__.py}`
> （v0.1.1、`commit=50de57e…`、`sha256=04b322d6…`）、`official_ebook_source.py`
> 用 `cf.DEFAULT_DOWNLOADS`+`cf.probe_info`（size/存在性）、`remote_manager.py`/
> `remote_sources.py`（URL 单源 `cf.REMOTE_URLS`）/`catalog/work_id.py`
> （`cf.canonical_work_id`）均走 `_vendor`、`requirements.txt` 已去 `requests`、
> `tests/test_vendor_sync.py` 已守 `sha256`+`probe_info`。本单保留作档案与后续同步说明。

> 目标：把 publish 的「官方电子书下载 + 元数据更新」改为复用共享层 `cbeta-fetch`
> （纯标准库、URL 单源、大小写规范化、zip 解压、条件更新），并**保留 publish 自己的
> 目录布局与业务**。本单供 publish 会话逐条实施；xml2pdf 侧已完成同款改造。

## 0. 先做两件事

1. **源码目录具名包**：`src/` → **`cbeta_publish/`**（`src` 是坏包名）。
   - 全量替换 import 前缀：`from src.xxx` → `from cbeta_publish.xxx`（约 40 处，
     含 `cbeta_publish/books/*`、`cbeta_publish/gui/*`、`cbeta_publish/catalog/*`、
     `cbeta_publish/collection/*`、`cbeta_publish/creators/*`、`tests/*`）。
   - 入口：`python -m cbeta_publish.app`（`app.py` 顶部 `sys.path.insert(parents[1])` 可删）。
2. **vendor 共享层**：
   ```bash
   python <cbeta-fetch>/tools/sync_into.py E:\dev\cbeta\publish\cbeta_publish\_vendor
   ```
   生成 `_vendor/{__init__.py,cbeta_fetch.py,SOURCE.txt}`（SOURCE 记 repo/commit/version/sha256）。
   加一条 sha256+版本校验测试防手改（见 §4）。

## 1. 共享层 API 速查（`from cbeta_publish._vendor import cbeta_fetch as cf`）

| 用途 | API |
|---|---|
| 校验/拆分/规范化 id | `cf.is_work_id` / `cf.parse_work_id`（canon 大写、no **原大小写**）/ `cf.canonical_work_id(work_id, catalog)` |
| catalog 查表 | `cf.catalog_lookup(catalog, canon, no)`（大小写不敏感、原大小写返回） |
| 作品 URL（含 `pdf`） | `cf.DEFAULT_DOWNLOADS`（`pdf/html/epub/docx/odt/txt_notes/xml`） |
| 元数据 URL（单源） | `cf.REMOTE_URLS`（`sutra_mapping/bulei/sutralist_json/category_json/dynasty_works/creators_by_strokes/all_creators/gaiji/sanskrit/supplement_ttf`） |
| 下载（原子/可解压） | `cf.download(url, dest, unzip=False)` |
| 平展解压 | `cf.unzip_flat(zip_path, dest_dir)` |
| 条件更新 / 探针 | `cf.fetch_if_changed(url, dest, etag=, last_modified=)` / `cf.probe(url, etag=, last_modified=)` |

> `cf.is_work_id` 只认**作品编号**（`T0349/TXa001/T0128a/JB005`），不认 `T01n0001`
> 这类**文件名**式。publish 若需后者，保留一条自己的 basename 正则（如现有
> `_is_work_id` 的第二段），与 `cf.is_work_id` 取「或」。

## 2. 逐文件改动

### 2.1 `cbeta_publish/books/official_ebook_source.py`
- 去 `requests`，改共享层。
- `canon` 解析后，id 用 **`cf.canonical_work_id(work, catalog)`**（`catalog` 传
  `mulu/sutra_mapping.txt` 路径）；否则 `TXa001/T0128a` 会 404。
- `ebook_url(fmt, canon, work)`：改为 `cf.DEFAULT_DOWNLOADS[fmt].format(canon=canon, id=work)`
  （`fmt ∈ {pdf,epub,docx,odt}`；`pdf` 现已在共享表）。
- `dest_path(work, fmt, dest_dir)`：**布局不变** `…/{fmt}/{canon}/{work}.{fmt}`。
- `download_ebook(work, fmt, dest_dir)`：
  - `pdf/epub`：`cf.download(url, dest)`。
  - `docx/odt`（端点是 zip，含 `xxx_001.docx`）：`cf.download(url, <dir>, unzip=True)`
    解压到 `…/{fmt}/{canon}/{work}/`（当前把 zip 存成 `.docx` 是坏档；UI 目前只暴露
    pdf/epub，接 docx/odt 时再定是否用目录布局）。
- `remote_info` / `is_unchanged`：可保留（HEAD+size/mtime 的「跳过」策略），或整体
  改走 `cf.fetch_if_changed`（见 2.2）；二选一，避免两套条件逻辑。

### 2.2 `cbeta_publish/books/remote_manager.py`（去 requests）
- `fetch(url, dest)` → `status, etag, lm = cf.fetch_if_changed(url, dest, etag=meta.get(url,{}).get("etag"), last_modified=meta.get(url,{}).get("last_modified"))`；
  `downloaded` 更新 `self.meta[url]={etag,last_modified}` 并 `_save_meta()`；`not-modified` 返回 False。
- `check(url)` → `cf.probe(url, etag=...)`；`changed` → True，`not-modified` → False，`failed` → False（打印）。
- 保留：`meta_path`（`cache/meta.json`）结构、`backup_dir/last/` 快照、`check_all/update_all`
  的返回与 `progress` 回调签名不变。

### 2.3 `cbeta_publish/books/remote_sources.py`（URL 单源）
- `SOURCES` 不再写 URL 字面量，改为引用共享 key；可保持现有 `(key, category, rel)` 结构，
  新增一个解析函数：
  ```python
  from cbeta_publish._vendor import cbeta_fetch as cf
  _URL_KEY = {"category": "category_json", "dynasty": "dynasty_works",
              "creators_strokes": "creators_by_strokes", "creators_alias": "all_creators",
              "bulei_txt": "bulei", "sutralist": "sutralist_json",
              "sutra_mapping": "sutra_mapping"}
  def url_of(key): return cf.REMOTE_URLS[_URL_KEY[key]]
  ```
  （`remote_manager` 调用处由 `url` 改成 `url_of(key)`；或把 `SOURCES` 改成运行时展开成
  现有 4 元组，改动最小。）

### 2.4 `cbeta_publish/gui/main_window.py`（id 大小写）
- `_normalize_work(w)`：改为 `cf.canonical_work_id(w.strip(), <catalog路径>)`
  （否则 `TXa001` 被抬成 `TXA001`、且 `MappingService.work_exists` 大小写敏感查不到 `a001`）。
- `_is_work_id(w)`：`cf.is_work_id(w) or <原 basename 正则>`（保留 `T01n0001` 形态）。
- 集合键/显示随之使用规范 id；如需兼容既有集合 JSON，可做一次迁移（读入时 canonical 化）。

### 2.5 其它
- `requirements.txt`：删除 `requests`（迁移后 publish 不再使用）。
- `tests/test_download.py`：`import src...` → `import cbeta_publish...`；新增
  id 规范化（`txa001/TXA001→TXa001`）与 `docx zip 解压`用例。
- 新增 `tests/test_remote_manager.py`：304（`probe not-modified`）免下载、200 更新、备份。
- 新增 `tests/test_vendor_sync.py`：`_vendor/cbeta_fetch.py` 的 sha256/version 与
  `SOURCE.txt` 一致。
- `docs/链路B-设计契约.md`：补「下载/元数据复用 cbeta-fetch；URL 单源；id 规范大小写」。

## 3. 注意 / 边界
- **不共享**：目录布局、`RemoteManager` 的 meta/备份/报告、`ebook_merger`、GUI。
- 元数据**文件内容**仍各自下载（同一上游 URL）；只是 URL 定义单源。
- `cf.download(unzip=True)` 的 `dest` 是**目录**；`unzip=False` 的 `dest` 是**文件**。
- 条件更新：`fetch_if_changed` 返回 `downloaded/not-modified/failed`；`probe` 返回
  `changed/not-modified/failed`。落盘为原子替换。

## 4. 验收
- `pytest`/`unittest` 全绿；**在 `sys.path` 不含 xml2pdf 的情况下**跑
  `test_download`/`test_remote_manager`（证明 publish 自包含）。
- 网络冒烟（默认 skip）：`TXa001/T0128a` 的 `pdf/epub`；`T0099` 的 `docx`（zip 解压）；
  元数据 `probe` 304/200。

## 5. 之后每次上游变化
```bash
python <cbeta-fetch>/tools/sync_into.py E:\dev\cbeta\publish\cbeta_publish\_vendor
# 跑 test_vendor_sync.py 对账后再提交
```
