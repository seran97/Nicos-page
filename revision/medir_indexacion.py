import re, json, sys, time
from collections import Counter
sys.path.insert(0, ".")
from search_console import inspect_url
urls = re.findall(r"<loc>([^<]+)</loc>", open("docs/sitemap.xml", encoding="utf-8").read())
res = {}
for i, u in enumerate(urls):
    r = None
    for _ in range(3):
        r = inspect_url(u)
        if r: break
        time.sleep(5)
    res[u] = r
    if i % 50 == 0: print(i, flush=True)
json.dump(res, open("indexacion_" + __import__("datetime").date.today().isoformat() + ".json", "w", encoding="utf-8"), indent=1)
ok = {u: r for u, r in res.items() if r}
print("consultadas", len(ok), "/", len(urls))
print("indexadas", sum(1 for r in ok.values() if r.get("indexed")))
print(Counter(r.get("coverage_state") for r in ok.values()).most_common())
