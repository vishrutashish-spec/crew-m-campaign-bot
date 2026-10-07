# Known Issues

Load-bearing problems the next engineer must know about before building against
CleverTap.

## 1. CleverTap single-value `equals` filter silently returns the whole base

A narrow segment definition using an `equals` filter on a profile property has
been observed to return reach equal to the full user base, in both the API and
the dashboard UI.

### Evidence

- **Dashboard**: a 3-rule segment combining `Email equals <one specific address>
  AND warehouse_production_removed not equals true AND is_in_DND_CT not equals
  true` returned a reach estimate of **680,449** profiles. For comparison, an
  empty-where API call returns 680,445. The filters were functionally ignored.
- **API**: a `profile_fields` filter with `operator: equals, field_name: Email`
  returned HTTP 400 "Invalid profile field: null" for every field name tried
  (Email, identity). The server-side bug surfaces differently via the two paths,
  same root cause.

### Impact for automated campaigns

An automated bot that trusts CleverTap's reported reach to validate a segment
before sending can send a 12-recipient campaign to the entire base. This is the
single highest-severity issue standing between us and production.

### Mandatory mitigations until CleverTap resolves this

1. Open and track a support ticket with the CleverTap CSM, with the evidence
   above attached.
2. **Never rely on a one-shot API segment definition.** Build and name segments
   in the CleverTap dashboard by hand, verify the reach there, and reference
   those saved segments by ID from the API.
3. **Every campaign creation call must first call `estimate_only` with the
   same segment, compare the reach to a sanity bound derived from the
   organisation's known headcount, and refuse to proceed on more than a 2x
   deviation.**
4. **Hard cap per campaign type**, enforced in code: HR nudges cap at 10,000;
   welcomes at 50,000; anything beyond requires explicit PMM override with a
   logged reason.

Nothing automated goes anywhere near the publish button until all four
mitigations are in place.
