# Calendar Cutoff

An Intelligent Contract primitive for reproducible UK working-day cutoffs. A support desk, operations team, or scheduling integration can certify the date reached after a specified number of working days. The returned certificate explains which days counted and identifies the government holiday observations used by the calculation.

## Contract behavior

| Method | Behavior |
| --- | --- |
| `certify(key, region, start_date, working_days)` | Write one immutable certificate under the caller's address. |
| `read_certificate(owner, key)` | Read the finalized certificate as JSON, or an empty string if absent. |

Choose `england-and-wales`, `scotland`, or `northern-ireland`. Supply an ISO calendar date and 1–20 working days. Counting starts on the day after the input date. Saturdays, Sundays, and dates listed by GOV.UK are excluded. The certificate stores the deadline, an ordered daily trace, and the observed holiday dates in the next 45 days. A bank holiday on a weekend is labeled `bank_holiday` and excluded once.

### Consensus and state

Each validator independently fetches the [GOV.UK bank holiday feed](https://www.gov.uk/bank-holidays.json). The equivalence check compares the exact sorted, deduplicated dates for the selected jurisdiction and bounded interval. The contract checks that each calendar year touched by the observation window is represented in the feed. Missing coverage, unavailable or invalid data, and duplicate certificate keys prevent writes. A separate key is required to take a new snapshot after data changes.

The rule uses published holidays and a fixed Monday–Friday workweek. It is suitable for operational planning and does not determine statutory deadlines or account for time zones, local closures, alternative workweeks, or working hours. Feed-year coverage is based on the presence of at least one holiday in each required year.

## Actual call example

The testnet example calls:

```js
await client.writeContract({
  address,
  functionName: 'certify',
  args: ['christmas-cutoff', 'england-and-wales', '2026-12-24', 2],
  leaderOnly: false,
  value: 0n,
})
```

After finality, read the certificate with the submitting address and key. The result is 30 December 2026: Christmas Day, the weekend, and the Boxing Day substitute holiday are excluded.

## Test and reproduce

Use Node.js 24 and Python 3.

```sh
npm ci
npm test
npm run verify
```

[Deployment](deployment.json) and [testnet evidence](evidence.json) target Stable Studionet, chain 61999, at `https://studio.genlayer.com/api` with `genlayer-js@1.1.8`. The read-only verifier checks the deployed source, deployment receipt, business receipts and finalized state. Local Python tests use isolated response fixtures.

Run `npm run deploy` to deploy with a temporary testnet signer. Run `npm run check` to execute the real acceptance sequence using fresh temporary signers and refresh the local evidence file. Both commands require zero gas price and submit zero value.
