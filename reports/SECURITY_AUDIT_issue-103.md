# Security Audit Report for PR #3 (issue-103)

## Static Application Security Testing (SAST)
Tool: `bandit`

### Findings
1. **[Medium] B310:blacklist** - Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected.
   - Location: `./apollo_client.py:82:21`
   - Description: `urllib.request.urlopen` is used without validating the schema. Consider restricting to `http/https` or using the `requests` library.
2. **[Low] B110:try_except_pass** - Try, Except, Pass detected.
   - Location: `./apollo_client.py:100:12`
   - Description: Exception is caught and silently passed.
3. **[Medium] B310:blacklist** - Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected.
   - Location: `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:58:21`
   - Description: `urllib.request.urlopen` is used without validating the schema. Consider restricting to `http/https` or using the `requests` library.
4. **[Low] B110:try_except_pass** - Try, Except, Pass detected.
   - Location: `./src/adapters/registries/colombia/supersociedades_soda_adapter.py:70:12`
   - Description: Exception is caught and silently passed.

## Recommendations
- For B310, consider using the `requests` library or validate that the URL scheme is strictly `https://`.
- For B110, at least log the exceptions instead of passing silently, as they might hide underlying errors during debugging.