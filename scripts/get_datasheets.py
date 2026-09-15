#!/usr/bin/env python3
"""Fetch a datasheet for every part in the BOM into ./datasheets/.

Not part of ./make.py and not checked into git: these are other people's
copyrighted documents, downloaded for reference while working on the design.

    python3 scripts/get_datasheets.py [--force]
"""
import json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DEST = os.path.join(ROOT, "datasheets")
API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
UA = "Mozilla/5.0 (X11; Linux x86_64)"

# Documents worth having that are not a single LCSC part.
EXTRA = {
    "Horowitz-lorenz-circuit": "https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm",
}


def fetch(url, binary=True, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": "https://www.lcsc.com/"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read() if binary else r.read().decode("utf-8", "replace")


def lcsc_datasheet_url(code, mpn):
    """Ask JLCPCB for the part, then follow LCSC's redirect page if needed."""
    body = json.dumps({"currentPage": 1, "pageSize": 25, "keyword": code,
                       "searchSource": "search"}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json", "User-Agent": UA})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:
        return None, f"API error: {e}"
    items = (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []
    hit = next((i for i in items if i["componentCode"] == code), None)
    if hit is None:
        return None, "not found in the JLCPCB catalogue"
    url = hit.get("dataManualUrl") or ""
    if not url:
        return None, "no datasheet link published"
    if "www.lcsc.com/datasheet" in url:
        try:
            page = fetch(url, binary=False)
        except Exception as e:
            return None, f"cannot open the LCSC page: {e}"
        m = re.search(r"https://datasheet\.lcsc\.com/[^\"' ]+\.pdf", page)
        if not m:
            return None, "LCSC page carried no PDF link"
        url = m.group(0)
    return url, None


def main():
    force = "--force" in sys.argv
    os.makedirs(DEST, exist_ok=True)
    wanted = {}
    for key, p in parts.PARTS.items():
        if p.get("lcsc"):
            wanted[p["lcsc"]] = p.get("mpn", key)
    for value, p in parts.PASSIVES.items():
        wanted[p["lcsc"]] = p.get("mpn", value)

    have = {f for f in os.listdir(DEST)}
    got = skipped = failed = 0
    for code, mpn in sorted(wanted.items(), key=lambda kv: kv[1]):
        safe = re.sub(r"[^A-Za-z0-9._+-]", "_", mpn)
        name = f"{safe}_{code}.pdf"
        if name in have and not force:
            skipped += 1
            continue
        # a file the user downloaded by hand under another name
        if not force and any(safe.lower()[:8] in h.lower() for h in have):
            skipped += 1
            continue
        url, err = lcsc_datasheet_url(code, mpn)
        if url is None:
            print(f"  -- {mpn} ({code}): {err}")
            failed += 1
            continue
        try:
            blob = fetch(url)
        except Exception as e:
            print(f"  -- {mpn} ({code}): download failed: {e}")
            failed += 1
            continue
        if not blob.startswith(b"%PDF"):
            print(f"  -- {mpn} ({code}): server did not return a PDF")
            failed += 1
            continue
        with open(os.path.join(DEST, name), "wb") as fh:
            fh.write(blob)
        print(f"  {name}  ({len(blob)//1024} kB)")
        got += 1
        time.sleep(0.3)

    for name, url in EXTRA.items():
        ext = ".htm" if url.endswith((".htm", ".html")) else ".pdf"
        path = os.path.join(DEST, name + ext)
        if os.path.exists(path) and not force:
            skipped += 1
            continue
        try:
            with open(path, "wb") as fh:
                fh.write(fetch(url))
            print(f"  {name}{ext}")
            got += 1
        except Exception as e:
            print(f"  -- {name}: {e}")
            failed += 1

    print(f"\n{got} downloaded, {skipped} already present, {failed} unavailable"
          f"\ninto {os.path.relpath(DEST, ROOT)}/ (not tracked by git)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
