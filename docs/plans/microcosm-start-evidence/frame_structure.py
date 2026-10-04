"""Structure-only inspection of cached Microcosm US frame files (no outcome variable is summarized).

For each file: entity row counts, the person column list, source_year and
person_support_channel record counts, the age codes at 80+, the weight share
by support channel, and the Kish effective sample size of persons from
household weights. Written for the microcosm-start plan review, 2026-10-04.
"""
import collections, sys
import h5py, numpy as np

def inspect(tag, path):
    f = h5py.File(path, "r")
    p = f["person"]["table"]
    h = f["household"]["table"][:]
    names = sorted(set(p.dtype.names or []) | set(f["person"]["_i_table"].keys()) - {"index"})
    print(f"===== {tag}\nfile: {path}")
    for ent in ["person", "household", "tax_unit", "family", "spm_unit", "marital_unit"]:
        print(f"  {ent} rows: {f[ent]['table'].shape[0]}")
    print("  person columns (%d): %s" % (len(names), ", ".join(names)))
    edu = [n for n in names if "HGA" in n or "educ" in n.lower() or "attain" in n.lower()]
    print("  education-like columns:", edu)
    cols = p.dtype.names
    hid = p.fields(["person_household_id"])[:]["person_household_id"]
    hw = dict(zip(h["household_id"], h["household_weight"]))
    w = np.array([hw[x] for x in hid])
    print("  kish_effective_n_persons: %.1f  max household weight: %.1f  sum person weight (M): %.1f" % (w.sum()**2 / (w**2).sum(), h["household_weight"].max(), w.sum()/1e6))
    for c in ["source_year", "person_support_channel"]:
        if c in cols:
            v = p.fields([c])[:][c]
            v = np.array([x.decode() if isinstance(x, bytes) else x for x in v])
            cnt = collections.Counter(v.tolist())
            print(f"  {c} record counts:", dict(cnt))
            if c == "person_support_channel":
                for k in cnt:
                    m = v == k
                    print(f"    weight share {k}: {w[m].sum()/w.sum():.3f}")
    if "age" in cols:
        a = p.fields(["age"])[:]["age"]
        print("  age max:", a.max(), " distinct ages >= 80:", sorted(set(a[a >= 80].tolist())))

for tag, path in [(a, b) for a, b in zip(sys.argv[1::2], sys.argv[2::2])]:
    inspect(tag, path)
