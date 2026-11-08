# Security Audit Report

**PR ID:** 13
**PR Title:** feat(frontend): integrate Wompi checkout widget (Issue #404)
**Target Branch:** dev
**Tool Used:** Bandit

## Findings Summary
A SAST scan was performed on the `src/` directory using Bandit. 

### 1. Hardcoded Secret (CWE-259)
- **Severity:** Low (Contextually High as it's a hardcoded API secret)
- **File:** `src/entrypoints/api/main.py:299`
- **Issue:** `[B105:hardcoded_password_string]` Possible hardcoded password: `'test_events_wmhM2301jwX2c9q8u4SofthtnAKUO7aK'`
- **Description:** A Wompi events secret `WOMPI_EVENTS_SECRET` is hardcoded directly into the `wompi_webhook` route logic. 
- **Remediation:** Remove the hardcoded secret. Load it from environment variables or a secure secret management service (e.g., `os.getenv("WOMPI_EVENTS_SECRET")`).

### 2. Unsafe URL Open Schemes (CWE-22)
- **Severity:** Medium
- **Files Affected:**
  - `src/adapters/enrichment/apollo_enrichment_adapter.py:82`
  - `src/adapters/registries/colombia/secop_contracts_adapter.py:47`
  - `src/adapters/registries/colombia/secop_harvester_adapter.py:90`
  - `src/adapters/registries/colombia/supersociedades_soda_adapter.py:58`
  - `src/adapters/registries/dominican_republic/dgcp_dr_adapter.py:34`
  - `src/adapters/verifiers/website_auditor.py:96`
- **Issue:** `[B310:blacklist]` Audit url open for permitted schemes. Allowing use of `file:/` or custom schemes is often unexpected.
- **Description:** Use of `urllib.request.urlopen` with dynamically constructed URLs can be vulnerable to SSRF or local file read attacks if schemas are not validated.
- **Remediation:** Validate URLs to ensure they use `http` or `https` before calling `urlopen`, or use a library like `requests`.

### 3. Try, Except, Pass (CWE-703)
- **Severity:** Low
- **Files Affected:** Multiple files (e.g., `apollo_enrichment_adapter.py`, `gcs_storage_adapter.py`, `config.py`).
- **Issue:** `[B110:try_except_pass]` Try, Except, Pass detected.
- **Description:** Silently dropping exceptions can hide errors and potentially lead to unexpected application states or bypasses.
- **Remediation:** Properly log exceptions or handle them appropriately.

## Conclusion
The hardcoded secret must be fixed immediately before this branch is merged into `dev`. The other findings should be addressed or ticketed as technical debt.
