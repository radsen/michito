# Security Audit Report - PR #4

**Branch**: `feature/issue-201`

## SAST Tool Used
Bandit (Python AST-based static analyzer)

## Findings

### Medium Severity

1. **[B310:blacklist] Audit url open for permitted schemes**
   - **Location**: `./apollo_client.py:82:21`
   - **Description**: Allowing use of `file:/` or custom schemes with `urllib.request.urlopen` is often unexpected and could lead to SSRF or local file read vulnerabilities.
   - **CWE**: [CWE-22](https://cwe.mitre.org/data/definitions/22.html)

2. **[B310:blacklist] Audit url open for permitted schemes**
   - **Location**: `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:58:21`
   - **Description**: Same as above. `urllib.request.urlopen` is used without explicitly verifying permitted URL schemes.
   - **CWE**: [CWE-22](https://cwe.mitre.org/data/definitions/22.html)

### Low Severity

1. **[B110:try_except_pass] Try, Except, Pass detected**
   - **Location**: `./apollo_client.py:100:12`
   - **Description**: Silently passing on exceptions masks potential errors and unexpected behavior.
   - **CWE**: [CWE-703](https://cwe.mitre.org/data/definitions/703.html)

2. **[B110:try_except_pass] Try, Except, Pass detected**
   - **Location**: `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:70:12`
   - **Description**: Broad exception caught and silently ignored.
   - **CWE**: [CWE-703](https://cwe.mitre.org/data/definitions/703.html)

## Recommendations
- **Medium Risk**: Ensure that any URLs passed to `urllib.request.urlopen` are strictly validated to start with `http://` or `https://` if dynamic, or consider switching to the `requests` library for safer and more robust HTTP requests.
- **Low Risk**: Avoid using `except Exception: pass`. Catch specific exceptions and consider logging them so that failures are not entirely silent.
