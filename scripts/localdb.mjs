// Starts a local PostgreSQL 17 server for development and tests — no Docker or admin rights needed.
//
//   npm run db:start          (from the repository root; leave it running, Ctrl+C to stop)
//
// Data lives in ./.localdb (git-ignored). Creates the databases listed in DATABASES if missing.
// Development only: the password below is not a secret and must never be used anywhere else.
import EmbeddedPostgres from 'embedded-postgres';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA_DIR = path.join(ROOT, '.localdb', 'data');
const PORT = Number(process.env.LOCALDB_PORT ?? 54329);
const DATABASES = ['anvika_dev', 'anvika_test'];

const pg = new EmbeddedPostgres({
  databaseDir: DATA_DIR,
  user: 'postgres',
  password: 'postgres',
  port: PORT,
  // persistent: true keeps data between runs (and avoids a Windows rmdir race on shutdown).
  persistent: true,
  // UTF-8 like Supabase. Without this, Windows initialises the cluster as WIN1252, which cannot
  // store characters such as ₹ or Indian-language text. Locale C = byte-order collation.
  initdbFlags: ['--encoding=UTF8', '--locale=C'],
  onLog: () => {},
  onError: (message) => console.error(String(message).trim()),
});

async function main() {
  if (!existsSync(path.join(DATA_DIR, 'PG_VERSION'))) {
    console.log(`Initialising a new PostgreSQL data directory in ${DATA_DIR} ...`);
    await pg.initialise();
  }
  await pg.start();

  const client = pg.getPgClient();
  await client.connect();
  const encoding = (await client.query('SHOW server_encoding')).rows[0].server_encoding;
  if (encoding !== 'UTF8') {
    await client.end();
    throw new Error(
      `The data directory uses ${encoding}, not UTF8. Stop this script, delete the .localdb ` +
        'folder (it only holds local development data) and run npm run db:start again.',
    );
  }
  const { rows } = await client.query('SELECT datname FROM pg_database');
  const existing = new Set(rows.map((r) => r.datname));
  for (const db of DATABASES) {
    if (!existing.has(db)) {
      await client.query(`CREATE DATABASE "${db}" ENCODING 'UTF8' TEMPLATE template0`);
      console.log(`Created database ${db}`);
    }
  }
  const version = (await client.query('SHOW server_version')).rows[0].server_version;
  await client.end();

  console.log(`PostgreSQL ${version} is running on 127.0.0.1:${PORT} (databases: ${DATABASES.join(', ')}).`);
  console.log('Press Ctrl+C to stop.');
}

let stopping = false;
async function shutdown() {
  if (stopping) return;
  stopping = true;
  console.log('\nStopping PostgreSQL ...');
  try {
    await pg.stop();
  } finally {
    process.exit(0);
  }
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

main().catch(async (err) => {
  console.error('Failed to start the local database:', err?.message ?? err);
  try {
    await pg.stop();
  } catch {
    /* already stopped */
  }
  process.exit(1);
});
