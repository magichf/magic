# Independent AI Core (IAC) v0.1

A model-agnostic continuity kernel prototype. It separates portable identity,
declarative governance, current state, and a hash-linked event journal.

## Scope
- Portable JSON identity, governance, and state manifests.
- Append-only JSONL journal with SHA-256 hash links.
- State checkpoint cross-check against the journal.
- Corruption detection and verified export to a separate directory.
- No model SDK, API credentials, network dependency, or background worker.

## Run
```bash
python -m unittest discover -s tests -v
python -m iac.cli init ./iac-data
python -m iac.cli append ./iac-data task_started '{"task":"portability"}'
python -m iac.cli verify ./iac-data
python -m iac.cli export ./iac-data ./iac-copy
```

## Explicit limitations
This is not consciousness, self-directed agency, or an autonomous background process.
SHA-256 chaining detects accidental/tampering changes only when the attacker does not
rewrite the complete chain and checkpoint. It does not authenticate authorship.
Governance JSON is descriptive; the host runtime must enforce permissions.
The prototype assumes a single writer; concurrent writers require locking or a
transactional store. Atomic rename/fsync guarantees vary by filesystem.

## Evidence status
The code and tests are a reference prototype. Cross-device portability, hostile
tampering resistance, multi-provider model switching, and autonomous operation
are not claimed as validated.
