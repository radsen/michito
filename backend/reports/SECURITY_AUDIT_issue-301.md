# Security Audit Report - issue-301

**Tool:** Bandit
**Target:** Branch `feature/issue-301`

## Summary
The static application security testing (SAST) was performed using Bandit.

- **Total Issues:** 4
- **High Severity:** 0
- **Medium Severity:** 2
- **Low Severity:** 2

## Findings

### Medium Severity
1. **[B310:blacklist] Audit url open for permitted schemes**
   - **File:** `./apollo_client.py:82:21`
   - **Details:** Allowing use of `file:/` or custom schemes is often unexpected.
2. **[B310:blacklist] Audit url open for permitted schemes**
   - **File:** `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:58:21`
   - **Details:** Allowing use of `file:/` or custom schemes is often unexpected.

### Low Severity
1. **[B110:try_except_pass] Try, Except, Pass detected.**
   - **File:** `./apollo_client.py:100:12`
   - **Details:** Silently ignoring exceptions can hide bugs.
2. **[B110:try_except_pass] Try, Except, Pass detected.**
   - **File:** `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:70:12`
   - **Details:** Silently ignoring exceptions can hide bugs.

## Recommendations
- **B310:** Ensure that URLs passed to `urllib.request.urlopen` are validated to only use standard HTTP/HTTPS schemes. Avoid accepting user-controlled input as a URL without proper sanitization.
- **B110:** Avoid silently catching exceptions. At a minimum, log the exception to aid in debugging and monitoring potential failure cases.
