# Regression tests

Use the repository's Python dependencies (`pip install -r requirements.txt`) and Node.js 22. From the checkout root, run:

```bash
python -m unittest discover -v
node --test tests/test_*.cjs
```

Python uses standard `unittest` discovery with no additional test framework. JavaScript uses Node's built-in test runner with no npm dependencies.

- `test_chunking.py` tests the public `chunk_text()` behavior: overlap, progress, coverage, source offsets, boundaries and bounded amplification. It reads configuration from `fixtures/chunk_overlap.json`; defaults are checked separately.
- `test_chunk_exports.py` exercises `generate()` and the written JSONL: schema, IDs, chapter metadata, isolation and coverage. `fixtures/chunk_export.json` includes HTML and explicit expected text; expected output is not calculated using private production helpers. Export tests also run with `tiktoken` unavailable.
- `test_code_languages.py` covers code-language preservation and structured exports.
- `test_chunk_overlap_ui.cjs` invokes the browser download handler with DOM/fetch stubs and checks its request body.

Tests use synthetic fixtures, temporary output directories and local stubs. They require no O'Reilly cookies, external service access or tokenizer downloads. They do not exercise live retrieval or PDF rendering.

The GitHub Actions workflow in `.github/workflows/tests.yml` runs both suites on pushes and pull requests, using Python 3.11 and 3.12. Dependency installation uses the network; the tests themselves do not.

Run a focused fixture check with:

```bash
python -m unittest tests.test_chunking.ChunkingTests.test_volume_regression -v
python -m unittest tests.test_chunk_exports -v
```
