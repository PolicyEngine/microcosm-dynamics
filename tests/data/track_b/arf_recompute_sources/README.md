# ARF and recomputation (Track B milestone R3) captures

Verification class: statutory conformance. These sources admit ARF credits
and recomputation mechanics for supported cases only. They contain published
rules and invented or SSA worked cases, with no population, behavioral or
forecast claim.

`manifest.json` preserves the orchestrator's URL, UTC retrieval time, byte
count and SHA-256 for each capture. POMS entries also preserve the transmittal
and page date. The two `_new_*_20261011.json` staging logs were folded into
this manifest without modifying any captured source bytes. The excerpt
entries receive their own byte counts and SHA-256 in addition to the supplied
full response provenance in `served_bodies`.

`http_body` captures are complete POMS HTML and eCFR section XML; the eCFR
snapshot is dated 2026-10-07. `http_text_excerpt` is the supplied verbatim LII
text for 42 U.S.C. 402(q) and 415(f), with complete response hashes.
`browser_text` is the supplied SSA Publication 05-10069 (2026) excerpt from
`pdftotext -layout`, with the complete PDF's hash. R3 made no network requests.

| Source | Rule or supported/refused case |
| --- | --- |
| RS 00615.003, .004, .010, .015 | FRA, age attainment, cohort boundaries and kinds of reduction |
| RS 00615.480, .482, .490 | Crediting months, full and partial final work deductions, single-entitlement ARF |
| RS 00615.491, .500 | Reentitled spouses and spouse dual entitlement |
| RS 00615.580, .582, .585 | Widow adjustments at age 62 and FRA, RIB-LIM variants |
| RS 00615.590, .595, .598 | Disability-widow variants and deceased worker adjustment |
| RS 00605.005, .401, .405, .407 | Eligibility basis, recomputation/recalculation distinction, administrative finality and family-effect limit |
| RS 00605.501, .560, .570, .580 | $1 test after COLAs, AERO, processing and recalculation refusals |
| 20 CFR 404.280-.288 | Preserved formula, earnings cutoff, next January/death effective dates, exceptional methods |
| 20 CFR 404.409-.412 | FRA, exact reduction arithmetic and adjusted reduction periods |
| 42 U.S.C. 402(q), 415(f) | Excluded months, rounded reductions, original formula and computation years, minimum increase |
| SSA Publication 05-10069 | $910/$975/$1,300 ARF example; annual recomputation timing |

`tests/test_track_b_r3_sources.py` recomputes every capture's SHA-256 and
checks substantive rule quotations and every source-derived worked figure
verbatim. Refused configurations also have explicit source quotations.
Sources reused from G and R1 remain in their existing folders and manifests:
G's exact reduction and rounding rules (RS 00615.101, .201, .301), PIA bend
points (RS 00605.900), 415(i) COLAs, and R1's published NAWI and COLA history.
No capture is duplicated.
