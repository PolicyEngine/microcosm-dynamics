# Pinned PolicyEngine RET parameter comparison

These four files are exact committed bytes from PolicyEngine US commit
`a03e82e503f8e0285125ee0c5380410a964c8e8a`, captured with `git show` from an
available local checkout. `manifest.json` records each immutable source URL,
retrieval time in UTC, byte length and SHA-256. They provide an independent
implementation comparison without requiring a live checkout or network.

The search found no existing RET parameter implementation under this
repository's `src/`. PolicyEngine US has both these parameter files and an
`ss_earnings_test_reduction` variable; R1 compares the parameter files because
the payment calculation is outside this milestone.

The differential test compares every lower and higher amount over the
table's 2000–2026 window (the modern formula applies from 2003). The captures also
contain 1975–1999 entries; the test verifies that these additional comparator
rows do not extend Track B's supported window. Two comparator limitations are
explicit:

- Before 2000, PolicyEngine's higher-amount file intentionally duplicates
  the lower amounts. These are not a reference for SSA's historical upper
  age-band amounts. Track B does not expose that older age-band regime.
- PolicyEngine represents the higher withholding rate as `0.333333`.
  Track B retains the statutory exact fraction `1/3`; the test verifies
  the known difference of `1/3000000` instead of adopting the truncation.

PolicyEngine US transcribes the same SSA table (`rtea.html`), so agreement
confirms the transcription; it does not independently validate the values,
which the SSA-capture oracle in `test_track_b_ret_params.py` does.

No simulation or population data are involved in this comparison.
