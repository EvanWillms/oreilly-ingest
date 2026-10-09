# Chunk overlap regression fixture

`chunk_overlap.json` describes a deterministic 20,000-character chapter: `"word "` repeated 4,000 times. It uses the unchanged defaults of 4,000 estimated tokens per chunk, 200 estimated tokens of overlap, and preferred paragraph/sentence boundaries.

Reproduce from the checkout root:

```bash
.venv/bin/python -m unittest tests.test_chunking.ChunkingTests.test_volume_regression -v
.venv/bin/python -m unittest discover -v
node --test tests/test_chunk_overlap_ui.cjs
```

The fixture is loaded by `ChunkingTests` in `tests/test_chunking.py`, using its declared chunk size, overlap and boundary preference. The targeted volume regression above asserts bounded amplification relative to non-overlapping chunks and reports chunk counts, total content characters, and first offsets on failure. Defaults are tested independently. All Python tests use standard `unittest` discovery; no standalone test runner lives in `scripts/`.

`chunk_export.json` supplies two independent HTML chapters and explicit expected text for `tests/test_chunk_exports.py`. JSONL expectations do not call the production text extractor. See `tests/README.md` for the test layout and CI commands.

Measured against the original implementation and the corrected implementation:

| Measurement | Original | Corrected |
| --- | ---: | ---: |
| Chunks | 19,999 | 2 |
| First start offsets | 0, 1, 2, 3, 4 | 0, 15,250 |
| First overlap (characters) | 16,049 | 800 |
| Total content characters | 192,174,876 | 20,798 |

The original caller subtracts an absolute character offset as though it were a relative overlap length. The correction uses a lightweight four-characters-per-token overlap estimate, capped at half the actual chunk span. This cap gives substantial forward progress even when overlap equals or exceeds the chunk size. It stops after reaching the end of the input rather than emitting repeated suffixes. Paragraph/sentence endpoint selection and JSONL fields remain unchanged.

The Python tests cover normal and zero overlap, offset progression, volume, short text, small chunks with large overlap, boundary selection, exact source slices, and chapter isolation/schema preservation. The JavaScript tests invoke the real download handler with a minimal browser stub and inspect its request body, including explicit zero and invalid/missing values.

Token counts remain approximate (word count multiplied by 1.3); overlap is approximate in characters. Large requested overlaps are deliberately clamped. No tokenizer or network access is needed for chunk generation. Tiny chunk sizes inherently require many chunks, but overlap amplification is bounded relative to their non-overlapping output.
