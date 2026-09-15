# -*- coding: utf-8 -*-
import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

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
                          if p.endswith(".part" + str(os.getpid()))])

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
