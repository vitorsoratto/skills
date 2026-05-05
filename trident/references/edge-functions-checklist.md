# Edge Functions Checklist

Use this for the `edge-functions` module. The goal is to break changed functions in realistic ways so new features and bug fixes are robust.

## Essential Path

Check the essential path once:

- valid minimal input
- expected caller context
- expected dependency response
- expected output shape or state transition

Do not spend the whole review here. Essential-path validation exists to prevent false positives and catch obvious regressions.

## Extraordinary Cases

For each changed function, handler, validator, mapper, or branch, test mentally or with focused tests across:

- absent values: `null`, `undefined`, missing key, omitted optional field
- empty values: empty string, whitespace-only, empty array/map/object
- numeric limits: `0`, `-1`, one-past-limit, max safe integer, `NaN`, `Infinity`, rounding, division by zero
- collections: duplicate items, unsorted input, single element, huge list, exactly-at-limit page size
- strings: unicode, emoji, RTL, combining characters, casing, trimming, very long values
- time/order: DST, timezone mismatch, stale timestamp, reordered events, duplicate webhook, retry after success
- failure paths: timeout, partial response, parse failure, cancelled request/context, dependency succeeds after partial write
- concurrency: double submit, interleaved writes, shared mutable state, read-modify-write, idempotency collision
- identity: anonymous, expired token, wrong tenant, permission revoked mid-flow, role escalation attempt
- trust: malformed payload, type coercion, injected control characters, path traversal, user-controlled URL

## Quick Mode

- Pick the top 3 extraordinary classes that best match the changed code.
- Emit at most 4 findings.
- If no concrete bug is found, summarize the highest-risk unchecked class in `areas_not_covered`.

## Deep Mode

- Build a small matrix of changed unit x extraordinary class.
- Prioritize classes that cross boundaries: user input, auth, persistence, queues, clocks, retries, and external calls.
- Prefer table-driven or property-style test recommendations when the bug would otherwise recur.
- Report only when the trigger reaches a wrong outcome; otherwise keep the case as a test recommendation or coverage gap.
