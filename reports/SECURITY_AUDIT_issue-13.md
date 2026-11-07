# Security Audit Report for PR #13

## Summary
A Static Application Security Testing (SAST) scan was performed using `bandit` on the `src/` directory. The scan identified several security concerns that should be addressed before merging this pull request.

## Findings

### High/Medium Severity Issues
1. **[B310:blacklist] Audit url open for permitted schemes.**
   - Multiple instances found where `urllib.request.urlopen` is used without explicitly restricting permitted schemes (e.g., to `http` or `https` only), which could allow unexpected schemes like `file:/`.
   - **Locations:**
     - `src/adapters/enrichment/apollo_enrichment_adapter.py:82:21`
     - `src/adapters/registries/colombia/secop_contracts_adapter.py:47:17`
     - `src/adapters/registries/colombia/secop_harvester_adapter.py:90:17`
     - `src/adapters/registries/colombia/supersociedades_soda_adapter.py:58:21`
     - `src/adapters/registries/dominican_republic/dgcp_dr_adapter.py:34:17`
     - `src/adapters/verifiers/website_auditor.py:96:17`
   - **Recommendation:** Validate URLs to ensure they use `http` or `https` schemes before passing them to `urlopen`.

### Low Severity Issues
1. **[B105:hardcoded_password_string] Possible hardcoded password**
   - **Description:** A hardcoded secret was detected for Wompi events. Hardcoding secrets in the source code can lead to unauthorized access and security breaches.
   - **Location:** `src/entrypoints/api/main.py:299:26` - `WOMPI_EVENTS_SECRET = "test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK"`
   - **Recommendation:** Use environment variables or a secure secret management service to store and access secrets.

2. **[B110:try_except_pass] Try, Except, Pass detected.**
   - Multiple instances of bare or silent exceptions were found. This can hide potential errors or security-relevant failures, making debugging difficult and system behavior unpredictable.
   - **Locations:**
     - `src/adapters/enrichment/apollo_enrichment_adapter.py:100:12`
     - `src/adapters/registries/colombia/supersociedades_soda_adapter.py:70:12`
     - `src/adapters/storage/gcs_storage_adapter.py:82:12`, `113:12`
     - `src/config.py:30:4`
   - **Recommendation:** Avoid `pass` in `except` blocks. Log the exceptions appropriately and ensure that failure conditions are handled correctly.

## Conclusion
Please address the hardcoded secret (`WOMPI_EVENTS_SECRET`) in `main.py` immediately as this represents a tangible security risk. Additionally, address the `urlopen` schemes and exception handling practices.
