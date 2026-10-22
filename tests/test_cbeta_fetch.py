# -*- coding: utf-8 -*-
import io
import os
import ssl
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cbeta_fetch import (is_work_id, parse_work_id, canonical_work_id,
                         catalog_lookup, DEFAULT_DOWNLOADS, REMOTE_URLS,
                         ALL_FORMATS, download, unzip_flat, fetch_if_changed,
                         probe, probe_info)
import cbeta_fetch


CAT = ("TX,00,a001,2,1,a001a01,太虛大師全書．編纂說明,釋太虛\n"
       "T,02,0128a,1,1,0835c13,須摩提女經,支謙\n"
       "J,15,B005,3,1,0001a01,某經,某\n")


def _tmp_dir():
    return tempfile.mkdtemp(prefix="cbeta-fetch-test-")


class TestWorkId(unittest.TestCase):
    def test_is_work_id(self):
        for ok in ("T0349", "A1057", "X1271", "T0128a", "TXa001", "jb005",
                   "t0128a"):
            self.assertTrue(is_work_id(ok), ok)
        for bad in ("", "T", "T12", "阿含經", "T01 阿含部"):
            self.assertFalse(is_work_id(bad), bad)

    def test_parse_keeps_no_case(self):
        self.assertEqual(parse_work_id("txa001"), ("TX", "a001"))
        self.assertEqual(parse_work_id("T0128A"), ("T", "0128A"))
        self.assertEqual(parse_work_id("JB005"), ("J", "B005"))
        with self.assertRaises(ValueError):
            parse_work_id("阿含")


class TestCatalogCanonical(unittest.TestCase):
    def setUp(self):
        self.cat = os.path.join(_tmp_dir(), "mapping.txt")
        with io.open(self.cat, "w", encoding="utf-8") as f:
            f.write(CAT)

    def test_lookup_case_insensitive_keeps_case(self):
        r = catalog_lookup(self.cat, "TX", "A001")[0]
        self.assertEqual((r["vol"], r["no"], r["file"]),
                         ("00", "a001", "TX00na001.xml"))
        self.assertEqual(catalog_lookup(self.cat, "t", "0128A")[0]["file"],
                         "T02n0128a.xml")
        self.assertEqual(catalog_lookup(self.cat, "J", "b005")[0]["file"],
                         "J15nB005.xml")

    def test_missing_catalog(self):
        self.assertEqual(catalog_lookup("", "T", "0349"), [])
        self.assertEqual(catalog_lookup(os.path.join(_tmp_dir(), "x.txt"),
                                        "T", "0349"), [])

    def test_canonical(self):
        for uid, want in (("txa001", "TXa001"), ("TXA001", "TXa001"),
                          ("T0128A", "T0128a"), ("JB005", "JB005"),
                          ("ZZ9999", "ZZ9999")):
            self.assertEqual(canonical_work_id(uid, self.cat), want, uid)


class TestUrls(unittest.TestCase):
    def test_templates(self):
        self.assertTrue(DEFAULT_DOWNLOADS["pdf"].format(canon="TX", id="TXa001")
                        .endswith("/pdf/TX/TXa001.pdf"))
        self.assertTrue(DEFAULT_DOWNLOADS["html"].format(id="TXa001")
                        .endswith("/html/TXa001.html.zip"))
        self.assertTrue(DEFAULT_DOWNLOADS["epub"].format(canon="TX", id="TXa001")
                        .endswith("/epub/TX/TXa001.epub"))
        self.assertTrue(DEFAULT_DOWNLOADS["txt_notes"].format(id="TXa001")
                        .endswith("/text-with-notes/TXa001.txt.zip"))
        self.assertTrue(DEFAULT_DOWNLOADS["xml"].format(
            canon="TX", vol="00", file="TX00na001.xml")
            .endswith("/TX/TX00/TX00na001.xml"))

    def test_remote_urls_keys(self):
        for k in ("sutra_mapping", "bulei", "sutralist_json", "category_json",
                  "dynasty_works", "vol_json", "creators_by_strokes", "all_creators",
                  "gaiji", "sanskrit", "supplement_ttf"):
            self.assertTrue(REMOTE_URLS.get(k, "").startswith("http"), k)
        self.assertIn("pdf", DEFAULT_DOWNLOADS)
        self.assertNotIn("pdf", ALL_FORMATS)

    def test_version(self):
        self.assertTrue(cbeta_fetch.__version__)


class TestDownload(unittest.TestCase):
    def test_download_file_and_atomic(self):
        d = _tmp_dir()
        src = os.path.join(d, "src.txt")
        with io.open(src, "w", encoding="utf-8") as f:
            f.write("hello 佛")
        dest = os.path.join(d, "sub", "out.txt")
        ok = download(Path(src).as_uri(), dest)
        self.assertTrue(ok)
        with io.open(dest, encoding="utf-8") as f:
            self.assertEqual(f.read(), "hello 佛")
        self.assertFalse([p for p in os.listdir(os.path.dirname(dest))
                          if ".part" in p])

    def test_download_unzip(self):
        d = _tmp_dir()
        z = os.path.join(d, "a.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("nested/T0099_001.docx", b"docx")
            zf.writestr("nested/readme.txt", b"x")
        out = os.path.join(d, "out")
        self.assertTrue(download(Path(z).as_uri(), out, unzip=True))
        self.assertTrue(os.path.isfile(os.path.join(out, "T0099_001.docx")))
        self.assertTrue(os.path.isfile(os.path.join(out, "readme.txt")))

    def test_download_fail(self):
        d = _tmp_dir()
        self.assertFalse(download("not-a-url", os.path.join(d, "x"),
                                  retries=0, timeout=2))

    def test_unzip_flat(self):
        d = _tmp_dir()
        z = os.path.join(d, "b.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("a/b.txt", "1")
        out = os.path.join(d, "o")
        unzip_flat(z, out)
        self.assertEqual(sorted(os.listdir(out)), ["b.txt"])

    def test_fetch_if_changed_downloaded(self):
        d = _tmp_dir()
        src = os.path.join(d, "s.json")
        with io.open(src, "w", encoding="utf-8") as f:
            f.write("{}")
        dest = os.path.join(d, "d.json")
        status, _etag, _lm = fetch_if_changed(Path(src).as_uri(), dest)
        self.assertEqual(status, "downloaded")
        self.assertTrue(os.path.isfile(dest))

    def test_download_streams_in_chunks(self):
        class _Resp:
            headers = {}

            def __init__(self, data):
                self._data = data
                self.calls = []

            def read(self, n=-1):
                self.calls.append(n)
                if not self._data:
                    return b""
                out = self._data[:n]
                self._data = self._data[n:]
                return out

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        d = _tmp_dir()
        data = b"x" * (cbeta_fetch.CHUNK + 10)
        resp = _Resp(data)
        resp.headers = {"Content-Length": str(len(data))}
        with mock.patch.object(cbeta_fetch, "_open", return_value=resp):
            self.assertTrue(download("http://example.test/x",
                                     os.path.join(d, "out.bin")))
        self.assertTrue(all(n == cbeta_fetch.CHUNK for n in resp.calls),
                        resp.calls)
        self.assertFalse([p for p in os.listdir(d) if ".part" in p])

    def test_download_rejects_short_body(self):
        class _Resp:
            headers = {"Content-Length": "100"}

            def __init__(self):
                self._done = False

            def read(self, n=-1):
                if self._done:
                    return b""
                self._done = True
                return b"x" * 10

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        d = _tmp_dir()
        dest = os.path.join(d, "out.bin")
        with mock.patch.object(cbeta_fetch, "_open", return_value=_Resp()):
            self.assertFalse(download("http://example.test/x", dest,
                                      retries=0))
        self.assertFalse(os.path.exists(dest))
        self.assertFalse([p for p in os.listdir(d) if ".part" in p])

    def test_part_names_are_unique(self):
        self.assertNotEqual(cbeta_fetch._part_path("x"),
                            cbeta_fetch._part_path("x"))

    def test_download_duplicate_zip_fails_atomic(self):
        # 同名 basename 整单失败：目标目录保持原样，不留下半成品
        d = _tmp_dir()
        z = os.path.join(d, "dup.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("a/x.txt", b"1")
            zf.writestr("b/x.txt", b"2")
        out = os.path.join(d, "out")
        os.makedirs(out)
        Path(out, "keep.txt").write_bytes(b"old")
        self.assertFalse(download(Path(z).as_uri(), out, unzip=True,
                                  retries=0))
        self.assertEqual(Path(out, "keep.txt").read_bytes(), b"old")
        self.assertEqual(sorted(os.listdir(out)), ["keep.txt"])
        self.assertFalse([p for p in os.listdir(d)
                          if ".part" in p or ".unzip" in p])

    def test_unzip_flat_replaces_and_keeps_others(self):
        d = _tmp_dir()
        z = os.path.join(d, "z.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("nested/x.txt", b"new")
        out = os.path.join(d, "o")
        os.makedirs(out)
        Path(out, "x.txt").write_bytes(b"old")
        Path(out, "other.txt").write_bytes(b"stay")
        unzip_flat(z, out)
        self.assertEqual(Path(out, "x.txt").read_bytes(), b"new")
        self.assertEqual(Path(out, "other.txt").read_bytes(), b"stay")

    def test_unzip_flat_bad_zip_leaves_dest_untouched(self):
        d = _tmp_dir()
        z = os.path.join(d, "bad.zip")
        Path(z).write_bytes(b"not a zip")
        out = os.path.join(d, "o")
        os.makedirs(out)
        Path(out, "keep.txt").write_bytes(b"old")
        with self.assertRaises(zipfile.BadZipFile):
            unzip_flat(z, out)
        self.assertEqual(Path(out, "keep.txt").read_bytes(), b"old")
        self.assertFalse([p for p in os.listdir(d)
                          if ".part" in p or ".unzip" in p])

    def test_unzip_flat_dest_is_file_fails_cleanly(self):
        d = _tmp_dir()
        z = os.path.join(d, "z.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("a.txt", b"x")
        target = os.path.join(d, "file")
        Path(target).write_bytes(b"old")
        with self.assertRaises(OSError):
            unzip_flat(z, target)
        self.assertEqual(Path(target).read_bytes(), b"old")
        self.assertFalse([p for p in os.listdir(d)
                          if ".part" in p or ".unzip" in p])

    def test_unzip_flat_rejects_dotdot(self):
        d = _tmp_dir()
        z = os.path.join(d, "dotdot.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("..", b"x")
        with self.assertRaises(zipfile.BadZipFile):
            unzip_flat(z, os.path.join(d, "o"))

    @unittest.skipUnless(os.name == "nt", "Windows 文件系统不分大小写")
    def test_unzip_flat_duplicate_case_insensitive(self):
        d = _tmp_dir()
        z = os.path.join(d, "dupcase.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("a/X.txt", b"1")
            zf.writestr("b/x.txt", b"2")
        with self.assertRaises(zipfile.BadZipFile):
            unzip_flat(z, os.path.join(d, "o"))


class TestTls(unittest.TestCase):
    @unittest.skipUnless(getattr(ssl, "VERIFY_X509_STRICT", 0),
                         "Python 3.13+ 才有 VERIFY_X509_STRICT")
    def test_cbdata_relaxes_strict_only(self):
        ctx = cbeta_fetch._context_for("https://cbdata.dila.edu.tw/x")
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertFalse(ctx.verify_flags & ssl.VERIFY_X509_STRICT)

    @unittest.skipUnless(getattr(ssl, "VERIFY_X509_STRICT", 0),
                         "Python 3.13+ 才有 VERIFY_X509_STRICT")
    def test_github_keeps_strict(self):
        ctx = cbeta_fetch._context_for("https://raw.githubusercontent.com/x")
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertTrue(ctx.verify_flags & ssl.VERIFY_X509_STRICT)

    def test_ctx_is_verified(self):
        ctx = cbeta_fetch._ctx()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_probe_status(self):
        d = _tmp_dir()
        src = os.path.join(d, "a.txt")
        Path(src).write_text("x", encoding="utf-8")
        self.assertEqual(cbeta_fetch.probe_status(Path(src).as_uri()), 200)
        self.assertIsNone(cbeta_fetch.probe_status("not-a-url"))


class TestProbeInfo(unittest.TestCase):
    def setUp(self):
        self.d = _tmp_dir()
        self.src = os.path.join(self.d, "a.txt")
        with io.open(self.src, "w", encoding="utf-8") as f:
            f.write("hello 佛")
        self.uri = Path(self.src).as_uri()

    def test_probe_info_returns_size(self):
        r = probe_info(self.uri)
        self.assertEqual(r["status"], "changed")
        self.assertEqual(r["size"], os.path.getsize(self.src))
        # 三元组 probe 向后兼容
        self.assertEqual(probe(self.uri)[0], "changed")

    def test_probe_info_failed(self):
        r = probe_info("not-a-url")
        self.assertEqual(r["status"], "failed")
        self.assertIsNone(r["size"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
