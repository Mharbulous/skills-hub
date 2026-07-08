# JavaScript Extraction Reference

Use this reference when the language selected for a hardening run is JavaScript.

## Substitution table

| Element | Value |
|---|---|
| Runtime command | `node` |
| File extension | `.mjs` |
| Import syntax | `import x from 'x'` |
| Argument parsing | `process.argv.slice(2)` |
| Run instruction | `Run: node scripts/<name>.mjs <args>` |

`.mjs` enables ES-module syntax (`import`/`export`) without needing to set
`"type": "module"` in a `package.json` — there usually isn't one to edit in a
skill directory.

## Template script

```javascript
#!/usr/bin/env node
/**
 * <Brief description of what this script does>.
 */
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('Usage: node <script>.mjs <input>');
  process.exit(1);
}
const inputPath = resolve(args[0]);
const result = process(inputPath);
console.log(result);

function process(filePath) {
  /** <Core processing logic>. */
}
```
