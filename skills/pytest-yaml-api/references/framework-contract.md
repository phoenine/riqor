# Framework contract

The generated project is a thin pytest adapter. Reusable execution behavior
lives in the independently versioned `rigorpath-api-test` runtime.

Generated repositories contain:

- `pyproject.toml` with a pinned compatible runtime dependency;
- `testcases/*.yaml` as the source of executable cases;
- `tests/conftest.py` for strict collection and environment gating;
- `tests/test_api.py` for runtime execution;
- `.env.example` containing names only, never credentials;
- `README.md` with validation and execution commands.

Bootstrap rules:

- The destination must be absent or empty.
- Existing framework repositories are supplemented, not replaced.
- No branch, URL, token, certificate bypass, or product authentication scheme is
  inferred.
- Static validation must work without contacting an API.
- Missing execution environment causes an explicit pytest skip; malformed cases
  fail collection.
