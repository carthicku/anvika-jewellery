import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * Before the E2E run: create/reset a development-only admin with a fresh random password
 * (written to the git-ignored e2e/.auth/admin.json). Refused by the backend in production.
 */
export default function globalSetup() {
  const here = dirname(fileURLToPath(import.meta.url));
  const backend = resolve(here, '../../backend');
  const windowsPython = resolve(backend, '.venv/Scripts/python.exe');
  const python =
    process.env.E2E_PYTHON ??
    (existsSync(windowsPython) ? windowsPython : resolve(backend, '.venv/bin/python'));
  execFileSync(
    python,
    ['-m', 'app.cli', 'e2e-admin', '--output', resolve(here, '.auth/admin.json')],
    { cwd: backend, stdio: 'inherit' },
  );
}
