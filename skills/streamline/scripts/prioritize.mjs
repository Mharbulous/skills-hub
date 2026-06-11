#!/usr/bin/env node
/**
 * Prioritize source files for dead code review based on git churn since last review.
 *
 * Usage: node prioritize.mjs [--limit N]
 *
 * --limit N   Cap output to N files (default 10)
 *
 * Outputs JSON to stdout: sorted array of { path, commitsSince, lastReviewedAt }
 * (highest priority first — never-reviewed files first, then by commit count descending)
 */

import { readFileSync, writeFileSync, existsSync, readdirSync, statSync } from 'fs';
import { join, extname, basename } from 'path';
import { execSync } from 'child_process';

// Parse args
const args = process.argv.slice(2);
const limitIdx = args.indexOf('--limit');
const limit = limitIdx !== -1 ? parseInt(args[limitIdx + 1], 10) : 10;

const LEDGER_PATH = '.claude/data/streamline-ledger.json';
const SKIP_DIRS = new Set(['node_modules', '.git', 'deprecated', 'bin', 'obj']);

// --- Project auto-detection ---
function detectProject() {
  if (existsSync('dotnet/src')) {
    return {
      srcDir: 'dotnet/src',
      extensions: new Set(['.cs']),
      testDir: 'dotnet/tests',
      testPattern: /Tests?\.cs$/,
    };
  }
  return {
    srcDir: 'src',
    extensions: new Set(['.js', '.ts', '.vue', '.jsx', '.tsx']),
    testDir: 'tests',
    testPattern: /\.test\.(js|ts|jsx|tsx)$/,
  };
}

// --- Step 1: Discover all source files ---
function walkSrc(project) {
  const results = [];

  function walk(currentDir) {
    let entries;
    try {
      entries = readdirSync(currentDir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const fullPath = join(currentDir, entry.name);
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) continue;
        walk(fullPath);
      } else if (entry.isFile() && project.extensions.has(extname(entry.name).toLowerCase())) {
        results.push(fullPath.replace(/\\/g, '/'));
      }
    }
  }

  walk(project.srcDir);
  return results.sort();
}

// --- Walk test directory for orphaned test detection ---
function walkTests(project) {
  const results = [];
  function walk(currentDir) {
    let entries;
    try {
      entries = readdirSync(currentDir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const fullPath = join(currentDir, entry.name);
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) continue;
        walk(fullPath);
      } else if (entry.isFile() && project.testPattern.test(entry.name)) {
        results.push(fullPath.replace(/\\/g, '/'));
      }
    }
  }
  walk(project.testDir);
  return results.sort();
}

// --- Step 2: Load or create ledger ---
function loadLedger() {
  if (!existsSync(LEDGER_PATH)) {
    return { files: {} };
  }
  try {
    return JSON.parse(readFileSync(LEDGER_PATH, 'utf-8'));
  } catch {
    return { files: {} };
  }
}

// --- Step 3: Count commits since a given SHA for a file ---
function commitsSince(sha, filePath) {
  try {
    const output = execSync(
      `git rev-list --count ${sha}..HEAD -- "${filePath}"`,
      { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }
    );
    return parseInt(output.trim(), 10);
  } catch {
    // If the SHA is invalid (e.g., force-pushed away), treat as never-reviewed
    return Infinity;
  }
}

// --- Main ---
const project = detectProject();
const sourceFiles = walkSrc(project);
const ledger = loadLedger();

// Orphaned tests: test files whose source file stem no longer exists in source dir
const extPattern = new RegExp(`\\.(${[...project.extensions].map(e => e.slice(1)).join('|')})$`);
const sourceStemSet = new Set(sourceFiles.map(f => basename(f).replace(extPattern, '')));
const allTestFiles = walkTests(project);
const testStemPattern = new RegExp(`\\.test\\.(js|ts|jsx|tsx)$|Tests?\\.cs$`);
const orphanedTests = allTestFiles.filter(testPath => {
  const stem = basename(testPath).replace(testStemPattern, '');
  return !sourceStemSet.has(stem);
});

const prioritized = [];

for (const filePath of sourceFiles) {
  const entry = ledger.files[filePath];

  if (!entry) {
    // Never reviewed — highest priority
    prioritized.push({ path: filePath, commitsSince: Infinity, lastReviewedAt: null });
  } else {
    const count = commitsSince(entry.lastReviewedAt, filePath);
    if (count === 0) continue; // No changes since last review — skip
    prioritized.push({
      path: filePath,
      commitsSince: count,
      lastReviewedAt: entry.lastReviewedAt
    });
  }
}

// Sort: Infinity first (never reviewed), then by commitsSince descending
prioritized.sort((a, b) => {
  if (a.commitsSince === Infinity && b.commitsSince === Infinity) return 0;
  if (a.commitsSince === Infinity) return -1;
  if (b.commitsSince === Infinity) return 1;
  return b.commitsSince - a.commitsSince;
});

const orphanedEntries = orphanedTests.map(path => ({
  path,
  commitsSince: Infinity,
  lastReviewedAt: null,
  orphaned: true,
}));

const output = [...orphanedEntries, ...prioritized].slice(0, limit);

console.log(JSON.stringify({
  meta: {
    totalTestFiles: allTestFiles.length,
    orphanedCount: orphanedTests.length,
  },
  files: output,
}, null, 2));
