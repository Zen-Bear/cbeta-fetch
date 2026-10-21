# cbeta-fetch

CBETA 官方资源**下载共享层**（纯标准库，无第三方依赖）。被两个项目以 **vendored**
方式复用：

- [`xml2pdf`](https://github.com/cbeta-org/xml-p5)（`pycbeta`）——单经转换/校验；
- `publish`（`cbeta_publish`）——藏经库管理/官方电子书下载与合并。

## 它做什么

| 能力 | 接口 |
|---|---|
| work id 校验/拆分 | `is_work_id` / `parse_work_id`（canon 大写、no **保留原大小写**） |
| 按 catalog 规范化 id | `canonical_work_id`（`txa001/TXA001 → TXa001`、`T0128A → T0128a`） |
| catalog 查表 | `catalog_lookup`（大小写不敏感、返回原始大小写） |
| 官方文件 URL | `DEFAULT_DOWNLOADS`（xml/html/docx/epub/odt/txt_notes/pdf） |
| 元数据 URL（单源） | `REMOTE_URLS` |
| 下载（默认校验/分块/可解压） | `download(url, dest, unzip=False)` |
| 平展解压 | `unzip_flat(zip_path, dest_dir)` |
| 条件更新 | `fetch_if_changed(url, dest, etag=..., last_modified=...)` |
| 更新探针 | `probe(url, ...)` / `probe_info(url, ...)` / `probe_status(url)` |

TLS：默认校验证书；cbdata 只清 `VERIFY_X509_STRICT` 附加位（证书链与主机名仍校验，
因该主机证书缺 Subject Key Identifier），其它主机严格。不使用 unverified 上下文。

## 不做什么（留在宿主项目）

- 目录布局（`xml2pdf` 用 per-work 工作目录；`publish` 用 `cbeta_ebooks/{fmt}/{canon}/`）；
- 打印/日志、GUI、校验、渲染、图片（`figures` 属 xml2pdf 的 CBR2X-figures）；
- 各项目的 source 表 schema、备份、报告。

## 用法

```python
from cbeta_fetch import canonical_work_id, catalog_lookup, DEFAULT_DOWNLOADS, download

wid = canonical_work_id("TXA001", catalog=r"…\sutra_mapping.txt")  # 'TXa001'
canon, no = wid[:2], wid[2:]                                        # ('TX','a001')
rec = catalog_lookup(cat, "TX", "a001")[0]                          # {'vol':'00','file':'TX00na001.xml',…}
xml_url = DEFAULT_DOWNLOADS["xml"].format(canon="TX", vol=rec["vol"], file=rec["file"])
download(xml_url, r"C:\tmp\TX00na001.xml")

# 文档型端点（zip）：解压到目录
download(DEFAULT_DOWNLOADS["docx"].format(canon="T", id="T0099"), r"C:\tmp\T0099", unzip=True)
```

## 在宿主项目里同步（勿手改副本）

```bash
python tools/sync_into.py <宿主项目的 vendor 目录>
# 例：python tools/sync_into.py E:\dev\cbeta\xml2pdf\pycbeta\_vendor
```

会在目标目录写入 `cbeta_fetch.py` 与 `SOURCE.txt`（repo/commit/version/sha256）。
宿主项目各有一条 sha256 校验测试，防止手改导致漂移。

## 版本

见 `CHANGELOG.md` 与 `cbeta_fetch.__version__`。
