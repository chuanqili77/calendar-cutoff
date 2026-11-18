import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {read, reader, waitForFinality} from '../chain.js'
import {validateReceipt} from './acceptance.mjs'

const load = path => readFile(new URL(path, import.meta.url), 'utf8')
const [deployment, proof, source] = await Promise.all([
  load('../deployment.json').then(JSON.parse),
  load('../evidence.json').then(JSON.parse),
  load('../contracts/calendar_cutoff.py'),
])
const {address} = deployment
assert.equal(Number(await reader.getChainId()), 61999)
assert.equal(proof.address, address)
assert.equal(await reader.getContractCode(address), source)
const provision = await waitForFinality(deployment.hash)
assert.equal(provision.data.contract_address.toLowerCase(), address.toLowerCase())
for (const [label, entry] of Object.entries(proof.transactions)) {
  validateReceipt(await reader.getTransaction({hash:entry.hash}), address, entry)
  console.log(label, 'FINALIZED', entry.reason ?? 'SUCCESS')
}

const {owner, key, record, transactions} = proof
const actual = await read(address, 'read_certificate', [owner, key])
assert.deepEqual(actual, record)
assert.equal(actual.deadline, '2026-12-30')
assert.equal(actual.trace.filter(row => row.kind === 'workday').length, 2)
assert.deepEqual(actual.trace.filter(row => row.kind === 'bank_holiday').map(row => row.date), [
  '2026-12-25', '2026-12-28',
])
assert.equal(await read(address, 'read_certificate', [transactions.unsupported_year.sender, 'future-cutoff']), null)
console.log('The certificate and failed-write readback are verified.')
