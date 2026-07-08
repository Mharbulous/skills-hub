#!/usr/bin/env node
/**
 * Deterministic promoter for the determinize skill's "promote" mode.
 *
 * Replaces an original skill directory with its `-hardened` sibling:
 *   1. validates the hardened directory argument
 *   2. rewrites the hardened directory's name inside its own text files
 *   3. deletes the original directory
 *   4. renames the hardened directory to the original's name
 *   5. emits a single JSON object describing what happened
 *
 * No git operations are performed here — this script only touches the
 * filesystem. It intentionally does not wrap the fs mutations in try/catch:
 * permission errors and other filesystem failures should crash loudly
 * rather than being swallowed.
 */
import { readdirSync, writeFileSync, readFileSync, rmSync, renameSync, existsSync, statSync } from 'fs';
import { resolve, join, basename, dirname } from 'path';

const TEXT_EXTENSIONS = new Set(['md', 'js', 'mjs', 'cjs', 'ts', 'py', 'sh', 'yaml', 'yml', 'json']);

function toPosix(p) {
  return p.split('\\').join('/');
}

function fail(message) {
  console.log(JSON.stringify({ action: 'error', message }));
  process.exit(1);
}

function walkDir(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      results.push(...walkDir(full));
    } else {
      results.push(full);
    }
  }
  return results;
}

function main() {
  const arg = process.argv[2];
  if (!arg) {
    fail('Usage: node promote-skill.mjs <hardened-skill-dir>');
  }

  const resolvedHardened = resolve(arg);
  const hardenedName = basename(resolvedHardened);
  if (!hardenedName.endsWith('-hardened')) {
    fail(`Directory must end with '-hardened', got: ${hardenedName}`);
  }

  const originalName = hardenedName.replace(/-hardened$/, '');
  const parentDir = dirname(resolvedHardened);
  const resolvedOriginal = join(parentDir, originalName);

  if (!existsSync(resolvedHardened) || !statSync(resolvedHardened).isDirectory()) {
    fail(`Hardened directory not found: ${resolvedHardened}`);
  }
  if (!existsSync(resolvedOriginal) || !statSync(resolvedOriginal).isDirectory()) {
    fail(`Original directory not found: ${resolvedOriginal}`);
  }

  const originalFiles = walkDir(resolvedOriginal).map(toPosix);

  const hardenedFiles = walkDir(resolvedHardened);
  const filesUpdated = [];
  for (const filePath of hardenedFiles) {
    const dotIndex = filePath.lastIndexOf('.');
    const ext = dotIndex === -1 ? '' : filePath.slice(dotIndex + 1).toLowerCase();
    if (!TEXT_EXTENSIONS.has(ext)) continue;
    const content = readFileSync(filePath, 'utf8');
    const updated = content.replaceAll(hardenedName, originalName);
    if (updated !== content) {
      writeFileSync(filePath, updated, 'utf8');
      const relPath = toPosix(filePath.slice(resolvedHardened.length)).replace(/^\/*/, '/');
      filesUpdated.push(relPath);
    }
  }

  rmSync(resolvedOriginal, { recursive: true, force: true });
  renameSync(resolvedHardened, resolvedOriginal);

  console.log(JSON.stringify({
    action: 'promoted',
    original: toPosix(resolvedOriginal),
    hardened: toPosix(resolvedHardened),
    filesUpdated,
    filesDeleted: originalFiles,
    message: `Promoted ${hardenedName} -> ${originalName}`,
  }));
}

main();
