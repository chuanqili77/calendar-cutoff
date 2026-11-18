import assert from 'node:assert/strict'
import {readFile, writeFile} from 'node:fs/promises'
import {createAccount} from 'genlayer-js'
import {read} from '../chain.js'
import {acceptance} from './acceptance.mjs'

const {address} = JSON.parse(await readFile(new URL('../deployment.json', import.meta.url)))
const account = createAccount()
const outsider = createAccount()
const key = 'christmas-cutoff'
const args = [key, 'england-and-wales', '2026-12-24', 2]
const {submit, transactions} = await acceptance(address)
await Promise.all([
  submit('certified', account, 'certify', args),
  submit('unsupported_year', outsider, 'certify', ['future-cutoff', 'scotland', '2099-01-01', 2], 'OUTSIDE_PUBLISHED_YEARS'),
])
await submit('duplicate', account, 'certify', args, 'CERTIFICATE_ALREADY_EXISTS')
const owner = account.address.toLowerCase()
const record = await read(address, 'read_certificate', [owner, key])
assert.equal(record.deadline, '2026-12-30')
assert.deepEqual(record.trace.map(row => row.kind), ['bank_holiday', 'weekend', 'weekend', 'bank_holiday', 'workday', 'workday'])
assert.equal(await read(address, 'read_certificate', [outsider.address, 'future-cutoff']), null)
await writeFile(new URL('../evidence.json', import.meta.url), JSON.stringify({
  address, owner, key, record, transactions,
}, null, 2) + '\n')
