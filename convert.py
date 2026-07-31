"""Converts keiyoushi's new protobuf extension index (index.pb) into the legacy
index.min.json format that older Tachiyomi forks (J2K/Yokai lineage) understand,
and mirrors the APKs/icons so `$repo/apk/<name>` style URLs keep working."""
import gzip
import json
import pathlib
import urllib.request

import index_pb2

SRC = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/index.pb"
LANGS = {"en", "all"}  # languages to mirror; add more codes here if needed


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "keiyoushi-bridge"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    out = pathlib.Path("out")
    (out / "apk").mkdir(parents=True, exist_ok=True)
    (out / "icon").mkdir(parents=True, exist_ok=True)

    idx = index_pb2.Index()
    idx.ParseFromString(gzip.decompress(fetch(SRC)))

    entries = []
    skipped = 0
    for e in idx.extensionList.extensions:
        langs = {s.language for s in e.sources}
        lang = langs.pop() if len(langs) == 1 else "all"
        if lang not in LANGS:
            skipped += 1
            continue
        apk_name = e.resources.apkUrl.rsplit("/", 1)[-1]
        (out / "apk" / apk_name).write_bytes(fetch(e.resources.apkUrl))
        try:
            (out / "icon" / (e.packageName + ".png")).write_bytes(fetch(e.resources.iconUrl))
        except Exception:
            pass
        entries.append({
            "name": "Tachiyomi: " + e.name,
            "pkg": e.packageName,
            "apk": apk_name,
            "lang": lang,
            "code": e.versionCode,
            "version": e.versionName,
            "nsfw": 1 if e.contentWarning in (index_pb2.CONTENT_WARNING_MIXED, index_pb2.CONTENT_WARNING_NSFW) else 0,
            "hasReadme": 0,
            "hasChangelog": 0,
            "sources": [
                {"name": s.name, "lang": s.language, "id": s.id, "baseUrl": s.homeUrl}
                for s in e.sources
            ],
        })

    (out / "index.json").write_text(json.dumps(entries, indent=2))
    (out / "index.min.json").write_text(json.dumps(entries, separators=(",", ":")))
    print(f"Mirrored {len(entries)} extensions ({skipped} skipped by language filter)")


if __name__ == "__main__":
    main()
