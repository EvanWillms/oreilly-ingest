import json
from pathlib import Path
import tempfile
import unittest

from toon_format import decode

from core.text_extractor import TextExtractor
from plugins.json_export import JsonExportPlugin
from plugins.markdown import MarkdownPlugin
from plugins.toon_export import ToonExportPlugin


CODE = "def greet(name):\n    return f'Hello, {name}'"


class CodeLanguageTests(unittest.TestCase):
    def assert_language(self, html, language):
        markdown = MarkdownPlugin().convert(html)
        self.assertIn(f"```{language}\n{CODE}\n```", markdown)
        extracted = TextExtractor().extract(html)
        self.assertEqual(len(extracted.code_blocks), 1)
        self.assertEqual(extracted.code_blocks[0].language, language)
        self.assertEqual(extracted.code_blocks[0].code, CODE)

    def test_language_on_outer_pre(self):
        self.assert_language(f'<pre class="language-python">{CODE}</pre>', "python")

    def test_language_on_nested_code(self):
        self.assert_language(f'<pre><code class="language-python">{CODE}</code></pre>', "python")

    def test_nested_lang_prefix(self):
        self.assert_language(f'<pre><code class="lang-python">{CODE}</code></pre>', "python")

    def test_outer_language_takes_precedence(self):
        self.assert_language(
            f'<pre class="language-python"><code class="language-javascript">{CODE}</code></pre>',
            "python",
        )

    def test_unrelated_outer_class_allows_nested_language(self):
        self.assert_language(
            f'<pre class="highlight"><code class="language-python">{CODE}</code></pre>',
            "python",
        )

    def test_unlabeled_block_stays_unlabeled(self):
        self.assert_language(f"<pre><code>{CODE}</code></pre>", "")

    def test_inline_code_stays_inline(self):
        html = '<p>Use <code class="language-python">greet(name)</code> here.</p>'
        self.assertEqual(MarkdownPlugin().convert(html), "Use `greet(name)` here.\n")
        extracted = TextExtractor().extract(html)
        self.assertEqual(extracted.text, "Use `greet(name)` here.")
        self.assertEqual(extracted.code_blocks, [])

    def test_language_does_not_leak_to_next_block(self):
        html = '<pre><code class="language-python">print(1)</code></pre><pre><code>print(2)</code></pre>'
        markdown = MarkdownPlugin().convert(html)
        self.assertIn("```python\nprint(1)\n```", markdown)
        self.assertIn("```\nprint(2)\n```", markdown)
        blocks = TextExtractor().extract(html).code_blocks
        self.assertEqual([(b.language, b.code) for b in blocks], [("python", "print(1)"), ("", "print(2)")])

    def test_json_jsonl_and_toon_preserve_nested_language_and_code(self):
        html = f'<pre><code class="language-python">{CODE}</code></pre>'
        chapters = [("chapter.html", "Example", html)]
        metadata = {"title": "Code Sample"}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            json_file = JsonExportPlugin().generate(directory, metadata, chapters, include_jsonl=True)
            toon_file = ToonExportPlugin().generate(directory, metadata, chapters)
            json_data = json.loads(json_file.read_text())
            toon_data = decode(toon_file.read_text())
            jsonl_chapter = json.loads((directory / "Code Sample.jsonl").read_text())
            for chapter in (json_data["chapters"][0], toon_data["chapters"][0], jsonl_chapter):
                with self.subTest(chapter=chapter):
                    self.assertEqual(chapter["code_blocks"], [{"language": "python", "code": CODE}])


if __name__ == "__main__":
    unittest.main()
