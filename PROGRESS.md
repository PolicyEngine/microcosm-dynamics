# Entry 8 referee round-1 fixes

## State

The official determination-year COLA correction is implemented and under
focused verification. No projection has been run.

## Done

- Read the adversarial implementation review and coordinator adjudication.
- Confirmed that findings 1, 2, 3, 5, 6, and 8 belong to this fix lane.
- Confirmed that finding 7 is limited here to the fixture mechanism and the
  three paraphrase corrections against the current frozen section 10 text.
- Replaced the shifted payment-year COLA anchor with SSA's official
  determination-year values for 1975-2022, ending at 2022=8.7.
- Removed the year-plus-one loader translation, regenerated provenance and
  hashes, and added an independent scattered-year official literal vector.

## Next

- Trace the affected implementation and frozen design requirements.
- Correct stepwise benefit rounding and its worked-example expectation.
- Add the nonpersistent production coordinator and harden publication inputs.
- Add the adjudicated mutation coverage and verbatim gap-block fixture.
- Run formatting, lint, and fast tests; push the branch and write the final
  report to the requested output file.
