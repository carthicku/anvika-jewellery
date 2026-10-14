// Fails if src/api/schema.d.ts is stale compared with ../backend/openapi.json.
// Usage: npm run check:api   (regenerate with: npm run gen:api)
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';

mkdirSync('node_modules/.tmp', { recursive: true });
const tmp = 'node_modules/.tmp/schema.check.d.ts';
execFileSync(
  process.execPath,
  ['node_modules/openapi-typescript/bin/cli.js', '../backend/openapi.json', '-o', tmp],
  {
    stdio: 'ignore',
  },
);
if (readFileSync(tmp, 'utf8') !== readFileSync('src/api/schema.d.ts', 'utf8')) {
  console.error('src/api/schema.d.ts is out of date. Run: npm run gen:api');
  process.exit(1);
}
console.log('API types are up to date.');
