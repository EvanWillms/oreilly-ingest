const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../web/static/app.js'), 'utf8');

for (const [value, expected] of [['0', 0], ['25', 25], ['', 200], ['invalid', 200], [undefined, 200]]) {
    test(`download request preserves/defaults overlap ${JSON.stringify(value)}`, async () => {
        let request;
        const context = vm.createContext({
            document: { addEventListener() {} },
            fetch: async (_url, options) => {
                request = JSON.parse(options.body);
                return { json: async () => ({ error: 'Stop before progress polling' }) };
            },
        });
        vm.runInContext(source, context);
        const elements = new Map();
        const card = {
            dataset: { bookId: 'fixture' },
            querySelector(selector) {
                if (selector === 'input[name="format"]:checked') return { value: 'chunks' };
                if (selector === 'input[name="chapters-scope"]:checked') return null;
                if (selector === 'input[name="output-style"]:checked') return null;
                if (selector === '.chunk-overlap-input') return { value };
                if (selector === '.chunk-size-input') return { value: '4000' };
                if (selector === '.output-dir-input') return { value: '' };
                if (selector === '.skip-images') return { checked: false };
                if (!elements.has(selector)) elements.set(selector, { classList: { add() {}, remove() {} }, style: {} });
                return elements.get(selector);
            },
        };
        await context.download(card);
        assert.ok(request, 'Actual download handler sends a request');
        assert.equal(request.chunking.overlap, expected);
        assert.equal(request.chunking.chunk_size, 4000);
    });
}
