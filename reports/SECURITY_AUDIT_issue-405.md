# Security Audit Report

**Issue / PR:** issue-405 (PR #14)
**Tool Used:** Bandit

## Summary
The static application security testing (SAST) was performed using Bandit. The scan identified **12** potential security issues: 
- 0 High Severity
- 6 Medium Severity
- 6 Low Severity

## Findings

### Medium Severity (6 issues)
**[B310:blacklist] Audit url open for permitted schemes.**
- `src/adapters/enrichment/apollo_enrichment_adapter.py:82`
- `src/adapters/registries/colombia/secop_contracts_adapter.py:47`
- `src/adapters/registries/colombia/secop_harvester_adapter.py:90`
- `src/adapters/registries/colombia/supersociedades_soda_adapter.py:58`
- `src/adapters/registries/dominican_republic/dgcp_dr_adapter.py:34`
- `src/adapters/verifiers/website_auditor.py:96`
*Description:* Allowing use of file:/ or custom schemes is often unexpected. Consider enforcing 'http' or 'https' specifically, or using the `requests` library which handles scheme validation.

### Low Severity (6 issues)
**1. [B105:hardcoded_password_string] Possible hardcoded password**
- `src/entrypoints/api/main.py:309` (`WOMPI_EVENTS_SECRET = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"`)
*Description:* Hardcoded credentials found in the API entrypoint. This secret should be moved to environment variables / secret manager.

**2. [B110:try_except_pass] Try, Except, Pass detected.**
- `src/adapters/enrichment/apollo_enrichment_adapter.py:100`
- `src/adapters/registries/colombia/supersociedades_soda_adapter.py:70`
- `src/adapters/storage/gcs_storage_adapter.py:82`, `113`
- `src/config.py:30`
*Description:* Catching an exception silently without logging or handling it can obscure failures and logic errors.

## Recommendations
- **Fix Hardcoded Secret:** Immediately move `WOMPI_EVENTS_SECRET` in `src/entrypoints/api/main.py` to `config.py` using environment variables.
- **Review urllib usage:** Migrate from `urllib.request` to `requests` or add scheme validation before opening URLs to prevent SSRF or local file inclusion.
- **Improve Error Handling:** Replace `pass` blocks in `except` clauses with appropriate error logging.

## Conclusion
The PR introduces a hardcoded secret in `main.py` which must be addressed before merging. The other issues (urllib usage and try/except/pass) should be tracked as technical debt or addressed in this PR.