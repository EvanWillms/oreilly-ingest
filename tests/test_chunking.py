import json
from pathlib import Path
import unittest

from plugins.chunking import ChunkConfig, ChunkingPlugin


class ChunkingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads((Path(__file__).parent / 'fixtures/chunk_overlap.json').read_text())
        cls.long_text = fixture['text_unit'] * fixture['repetitions']
        cls.fixture_config = ChunkConfig(
            chunk_size=fixture['chunk_size'],
            overlap=fixture['overlap'],
            respect_boundaries=fixture['respect_boundaries'],
        )
        cls.fixture_chunks = ChunkingPlugin().chunk_text(
            cls.long_text, cls.fixture_config.chunk_size, cls.fixture_config.overlap,
            cls.fixture_config.respect_boundaries,
        )

    def setUp(self):
        self.plugin = ChunkingPlugin()

    def test_defaults_unchanged(self):
        self.assertEqual(ChunkConfig(), ChunkConfig(4000, 200, True))
        text = 'word ' * 4000
        self.assertEqual(self.plugin.chunk_text(text), self.plugin.chunk_text(text, 4000, 200, True))

    def test_normal_overlap_is_modest(self):
        self.assertGreater(len(self.fixture_chunks), 1)
        for previous, current in zip(self.fixture_chunks, self.fixture_chunks[1:]):
            overlap = previous['end_offset'] - current['start_offset']
            self.assertGreater(overlap, 0)
            self.assertLessEqual(overlap, 1200)  # Roughly 200 tokens at four characters each.
            self.assertLess(overlap, (previous['end_offset'] - previous['start_offset']) / 2)

    def test_no_overlap_is_contiguous_and_ordered(self):
        chunks = self.plugin.chunk_text(self.long_text, overlap=0)
        self.assertEqual(chunks[0]['start_offset'], 0)
        for previous, current in zip(chunks, chunks[1:]):
            self.assertEqual(previous['end_offset'], current['start_offset'])
        self.assertEqual(chunks[-1]['end_offset'], len(self.long_text))

    def test_forward_progress(self):
        for previous, current in zip(self.fixture_chunks, self.fixture_chunks[1:]):
            span = previous['end_offset'] - previous['start_offset']
            self.assertGreaterEqual(current['start_offset'] - previous['start_offset'], span / 2)
        self.assertEqual(self.fixture_chunks[-1]['end_offset'], len(self.long_text))

    def test_volume_regression(self):
        metrics = {
            'input_characters': len(self.long_text),
            'chunk_count': len(self.fixture_chunks),
            'total_content_characters': sum(len(c['content']) for c in self.fixture_chunks),
            'first_start_offsets': [c['start_offset'] for c in self.fixture_chunks[:10]],
            'first_end_offsets': [c['end_offset'] for c in self.fixture_chunks[:10]],
        }
        diagnostic = json.dumps(metrics, indent=2)
        without_overlap = self.plugin.chunk_text(
            self.long_text, self.fixture_config.chunk_size, 0, self.fixture_config.respect_boundaries
        )
        self.assertLessEqual(metrics['chunk_count'], 2 * len(without_overlap), diagnostic)
        self.assertLess(metrics['total_content_characters'], 2 * len(self.long_text), diagnostic)

    def test_paragraph_break_is_preferred(self):
        text = 'word ' * 78 + '\n\n' + 'end. ' + 'word ' * 120
        chunks = self.plugin.chunk_text(text, chunk_size=100, overlap=0)
        self.assertEqual(chunks[0]['end_offset'], 392)

    def test_sentence_break_is_preferred(self):
        text = 'word ' * 79 + 'end. ' + 'word ' * 120
        chunks = self.plugin.chunk_text(text, chunk_size=100, overlap=0)
        self.assertEqual(chunks[0]['end_offset'], 400)

    def test_short_text_is_one_chunk_even_with_large_overlap(self):
        for overlap in (0, 200, 10000):
            with self.subTest(overlap=overlap):
                chunks = self.plugin.chunk_text('Short chapter.', overlap=overlap)
                self.assertEqual(len(chunks), 1)
                self.assertEqual(chunks[0]['content'], 'Short chapter.')

    def test_small_chunks_large_overlap_have_bounded_volume(self):
        text = 'word ' * 600
        for size, overlap in ((1, 200), (64, 63), (64, 64), (64, 128)):
            with self.subTest(size=size, overlap=overlap):
                chunks = self.plugin.chunk_text(text, size, overlap, respect_boundaries=False)
                without_overlap = self.plugin.chunk_text(text, size, 0, respect_boundaries=False)
                self.assertLessEqual(len(chunks), 2 * len(without_overlap))
                self.assertLessEqual(sum(len(c['content']) for c in chunks), 2 * len(text))
                for previous, current in zip(chunks, chunks[1:]):
                    self.assertGreaterEqual(current['start_offset'] - previous['start_offset'],
                                            (previous['end_offset'] - previous['start_offset']) / 2)

    def test_offsets_match_original_slices(self):
        for text, chunks in ((self.long_text, self.fixture_chunks),
                             ('  A paragraph.\n\nAnother paragraph.  ', self.plugin.chunk_text('  A paragraph.\n\nAnother paragraph.  ', 3, 1))):
            for chunk in chunks:
                self.assertEqual(chunk['content'], text[chunk['start_offset']:chunk['end_offset']].strip())
                self.assertGreaterEqual(chunk['start_offset'], 0)
                self.assertGreater(chunk['end_offset'], chunk['start_offset'])
                self.assertLessEqual(chunk['end_offset'], len(text))

    def test_chunks_cover_every_source_character_without_gaps(self):
        texts = (self.long_text, '  A paragraph.\n\nAnother paragraph.  ', 'café 日本語 ' * 100)
        for text in texts:
            for overlap in (0, 1, 200):
                for boundaries in (False, True):
                    with self.subTest(text=text[:30], overlap=overlap, boundaries=boundaries):
                        chunks = self.plugin.chunk_text(text, 64, overlap, boundaries)
                        self.assertTrue(chunks)
                        self.assertEqual(chunks[0]['start_offset'], 0)
                        covered_end = 0
                        for chunk in chunks:
                            self.assertLessEqual(chunk['start_offset'], covered_end)
                            self.assertGreater(chunk['end_offset'], covered_end)
                            self.assertEqual(chunk['content'], text[chunk['start_offset']:chunk['end_offset']].strip())
                            covered_end = chunk['end_offset']
                        self.assertEqual(covered_end, len(text))

    def test_empty_text(self):
        self.assertEqual(self.plugin.chunk_text(''), [])

    def test_invalid_sizes_and_negative_overlap_are_rejected(self):
        for size, overlap in ((0, 0), (-1, 0), (10, -1)):
            with self.subTest(size=size, overlap=overlap):
                with self.assertRaises(ValueError):
                    self.plugin.chunk_text('word ' * 10, size, overlap)


if __name__ == '__main__':
    unittest.main()
