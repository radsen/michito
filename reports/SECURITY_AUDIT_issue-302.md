# Security Audit Report

## Overview
A Static Application Security Testing (SAST) scan was performed using Bandit on the source code for PR #7 (`feature/issue-302`). The scan identified 4 potential issues (2 Medium Severity, 2 Low Severity).

## Findings

### 1. Medium Severity: Audit URL open for permitted schemes
**Issue:** [B310:blacklist] Allowing use of `file:/` or custom schemes is often unexpected and can lead to server-side request forgery (SSRF) or local file inclusion.
**CWE:** CWE-22
* **Location 1:** `./apollo_client.py:82:21` - `with urllib.request.urlopen(req, timeout=10) as resp:`
* **Location 2:** `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:58:21` - `with urllib.request.urlopen(req, timeout=5) as response:`

**Recommendation:** Ensure that the URL passed to `urlopen` is validated and restricted to safe schemes (e.g., `http`, `https`). If possible, switch to the `requests` library and restrict schemas.

### 2. Low Severity: Try, Except, Pass detected
**Issue:** [B110:try_except_pass] Silently ignoring exceptions can hide errors and complicate debugging or conceal failure states in security controls.
**CWE:** CWE-703
* **Location 1:** `./apollo_client.py:100:12`
* **Location 2:** `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:70:12`

**Recommendation:** Consider logging the exception or handling it explicitly instead of using `pass`.

## Scan Metrics
* **Total lines of code:** 3489
* **Total issues:** 4 (High: 0, Medium: 2, Low: 2)
