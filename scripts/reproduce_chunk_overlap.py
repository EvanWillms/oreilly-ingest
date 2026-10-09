"""Print chunk counts and offset progression for the overlap regression fixture."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugins.chunking import ChunkingPlugin


def main():
    fixture_path = Path(__file__).resolve().parents[1] / 'tests/fixtures/chunk_overlap.json'
    fixture = json.loads(fixture_path.read_text())
    text = fixture['text_unit'] * fixture['repetitions']
    chunks = ChunkingPlugin().chunk_text(
        text, fixture['chunk_size'], fixture['overlap'], fixture['respect_boundaries']
    )
    print(json.dumps({
        'input_characters': len(text),
        'chunk_count': len(chunks),
        'total_content_characters': sum(len(c['content']) for c in chunks),
        'first_start_offsets': [c['start_offset'] for c in chunks[:10]],
        'first_end_offsets': [c['end_offset'] for c in chunks[:10]],
        'first_overlaps_characters': [a['end_offset'] - b['start_offset'] for a, b in zip(chunks[:10], chunks[1:11])],
    }, indent=2))


if __name__ == '__main__':
    main()
