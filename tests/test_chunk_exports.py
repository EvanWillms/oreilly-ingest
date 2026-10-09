import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from plugins.chunking import ChunkConfig, ChunkingPlugin


class ChunkExportTests(unittest.TestCase):
    def setUp(self):
        fixture_path = Path(__file__).parent / 'fixtures/chunk_export.json'
        self.fixture = json.loads(fixture_path.read_text())
        self.plugin = ChunkingPlugin()
        chapters = [(chapter['filename'], chapter['title'], chapter['html'])
                    for chapter in self.fixture['chapters']]
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        # Fail if chunk exports start requiring an available tokenizer.
        with patch.dict(sys.modules, {'tiktoken': None}):
            output = self.plugin.generate(
                Path(directory.name), {'title': self.fixture['title']}, chapters,
                ChunkConfig(**self.fixture['config']),
            )
        self.chunks = [json.loads(line) for line in output.read_text().splitlines()]

    def test_jsonl_schema_and_global_ids(self):
        expected_keys = {'content', 'token_count', 'start_offset', 'end_offset', 'chunk_id',
                         'chapter_index', 'chapter_title', 'chapter_filename'}
        self.assertTrue(self.chunks)
        self.assertEqual([chunk['chunk_id'] for chunk in self.chunks], list(range(len(self.chunks))))
        for chunk in self.chunks:
            self.assertEqual(set(chunk), expected_keys)
            for field in ('token_count', 'start_offset', 'end_offset', 'chunk_id', 'chapter_index'):
                self.assertIsInstance(chunk[field], int)
                self.assertGreaterEqual(chunk[field], 0)
            for field in ('content', 'chapter_title', 'chapter_filename'):
                self.assertIsInstance(chunk[field], str)

    def test_chapter_metadata_and_isolation(self):
        self.assertEqual({chunk['chapter_index'] for chunk in self.chunks}, {0, 1})
        self.assertEqual([chunk['chapter_index'] for chunk in self.chunks],
                         sorted(chunk['chapter_index'] for chunk in self.chunks))
        for index, chapter in enumerate(self.fixture['chapters']):
            chunks = [chunk for chunk in self.chunks if chunk['chapter_index'] == index]
            self.assertGreater(len(chunks), 1)
            self.assertEqual(chunks[0]['start_offset'], 0)
            for chunk in chunks:
                self.assertEqual(chunk['chapter_title'], chapter['title'])
                self.assertEqual(chunk['chapter_filename'], chapter['filename'])
                self.assertNotIn('Beta' if index == 0 else 'Alpha', chunk['content'])

    def test_offsets_and_complete_coverage_match_explicit_fixture_text(self):
        for index, chapter in enumerate(self.fixture['chapters']):
            text = chapter['expected_text']
            covered_end = 0
            for chunk in (chunk for chunk in self.chunks if chunk['chapter_index'] == index):
                start, end = chunk['start_offset'], chunk['end_offset']
                self.assertLessEqual(start, covered_end)
                self.assertGreater(end, covered_end)
                self.assertLessEqual(end, len(text))
                self.assertEqual(chunk['content'], text[start:end].strip())
                covered_end = end
            self.assertEqual(covered_end, len(text))


if __name__ == '__main__':
    unittest.main()
