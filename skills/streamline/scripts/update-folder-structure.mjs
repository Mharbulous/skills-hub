#!/usr/bin/env node
/**
 * Update Folder-Structure.md with current line counts.
 *
 * Usage: node update-folder-structure.mjs [--check-only] [--date YYYY-MM-DD]
 *
 * --check-only   Only check if the file is outdated (exit 0=outdated, 1=current)
 * --date         Override today's date (for testing)
 *
 * Outputs JSON to stdout:
 * {
 *   "action": "updated" | "current" | "check",
 *   "oldFile": "2026-02-13-Folder-Structure.md",
 *   "newFile": "2026-03-07-Folder-Structure.md",
 *   "fileDate": "2026-02-13",
 *   "today": "2026-03-07",
 *   "totalFiles": 372,
 *   "filesOver300": 82,
 *   "totalLines": 81726,
 *   "changedFiles": [ { "path": "src/...", "oldCount": 513, "newCount": 293 }, ... ]
 * }
 */

import { readFileSync, writeFileSync, unlinkSync, rmdirSync, readdirSync, existsSync, statSync } from 'fs';
import { resolve, extname, join } from 'path';

// Parse args
const args = process.argv.slice(2);
const checkOnly = args.includes('--check-only');
const dateIdx = args.indexOf('--date');
const today = dateIdx !== -1 ? args[dateIdx + 1] : new Date().toISOString().slice(0, 10);

const MISC_DIR = 'docs/Miscellaneous';

// --- Project auto-detection ---
function detectProject() {
  if (existsSync('dotnet/src')) {
    return {
      srcDir: 'dotnet/src',
      extensions: new Set(['.cs']),
    };
  }
  return {
    srcDir: 'src',
    extensions: new Set(['.vue', '.js', '.ts', '.jsx', '.tsx', '.css', '.mjs', '.cjs']),
  };
}

// --- Step 1: Find latest Folder-Structure file ---
function findLatestFolderStructure() {
  if (!existsSync(MISC_DIR)) {
    return null;
  }
  const files = readdirSync(MISC_DIR)
    .filter(f => /^\d{4}-\d{2}-\d{2}-Folder-Structure\.md$/.test(f))
    .sort()
    .reverse();
  return files.length > 0 ? files[0] : null;
}

// --- Step 2: Extract date from filename ---
function extractDate(filename) {
  const match = filename.match(/^(\d{4}-\d{2}-\d{2})-Folder-Structure\.md$/);
  return match ? match[1] : null;
}

// --- Step 3: Count non-blank, non-comment lines ---
function countLines(filePath) {
  try {
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');
    const ext = extname(filePath).toLowerCase();

    let count = 0;
    let inBlockComment = false;
    let inHtmlComment = false;

    for (const line of lines) {
      const trimmed = line.trim();

      // Skip blank lines
      if (!trimmed) continue;

      // Handle Vue/JS/TS/CSS files
      if (['.vue', '.js', '.ts', '.jsx', '.tsx', '.css', '.mjs', '.cjs', '.cs'].includes(ext)) {

        // Multi-line HTML comment tracking (Vue files)
        if (ext === '.vue') {
          if (inHtmlComment) {
            if (trimmed.includes('-->')) {
              inHtmlComment = false;
              const after = trimmed.split('-->').pop().trim();
              if (after) count++;
            }
            continue;
          }
          // Single-line HTML comment
          if (trimmed.startsWith('<!--') && trimmed.endsWith('-->')) continue;
          // Start of multi-line HTML comment
          if (trimmed.startsWith('<!--')) {
            inHtmlComment = true;
            continue;
          }
        }

        // Block comment start (without end on same line)
        if (!inBlockComment && trimmed.includes('/*') && !trimmed.includes('*/')) {
          inBlockComment = true;
          const before = trimmed.split('/*')[0].trim();
          if (before) count++;
          continue;
        }

        // Inside block comment
        if (inBlockComment) {
          if (trimmed.includes('*/')) {
            inBlockComment = false;
            const after = trimmed.split('*/').pop().trim();
            if (after && !after.startsWith('//')) count++;
          }
          continue;
        }

        // Single-line block comment
        if (trimmed.startsWith('/*') && trimmed.includes('*/')) continue;

        // Line comment
        if (trimmed.startsWith('//')) continue;

        // Block comment continuation (star-prefixed lines)
        if (trimmed.startsWith('*') && !trimmed.startsWith('*/')) continue;
      }

      count++;
    }

    return count;
  } catch {
    return 0;
  }
}

// --- Step 4: Walk source directory ---
const SKIP_DIRS = new Set(['node_modules', '.git', 'deprecated', 'bin', 'obj']);

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

// --- Step 4b: Clean deprecated directories ---
const SKIP_DIRS_FOR_CLEANUP = new Set(['node_modules', '.git', 'bin', 'obj']);

function cleanDeprecatedDirs(rootDir) {
  const deleted = [];
  function walk(dir) {
    let entries;
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const entry of entries) {
      const full = join(dir, entry.name);
      if (!entry.isDirectory()) continue;
      if (SKIP_DIRS_FOR_CLEANUP.has(entry.name)) continue;
      if (entry.name === 'deprecated') {
        try {
          for (const f of readdirSync(full)) {
            const fp = join(full, f);
            try { unlinkSync(fp); deleted.push(fp.replace(/\\/g, '/')); } catch {}
          }
          rmdirSync(full); // only succeeds if empty (no unexpected subdirs)
        } catch {}
      } else {
        walk(full);
      }
    }
  }
  walk(rootDir);
  return deleted;
}

// --- Step 5: Parse existing file to get old counts ---
function parseOldCounts(content) {
  const counts = new Map();

  // Parse bullet format: - `path/to/file` - NNN lines
  const bulletPattern = /^- `([^`]+)` - (\d+) lines/gm;
  for (const match of content.matchAll(bulletPattern)) {
    counts.set(match[1], parseInt(match[2], 10));
  }

  return counts;
}

// --- Step 6: Generate new document ---
function generateDocument(fileCounts, dateStr, srcDir) {
  const over300 = [];
  let totalLines = 0;

  for (const [filePath, count] of fileCounts.entries()) {
    totalLines += count;
    if (count >= 300) {
      over300.push({ filePath, count });
    }
  }

  // Sort over300 by count descending
  over300.sort((a, b) => b.count - a.count);

  let doc = `# Folder Structure - Source Code Directory

**Date**: ${dateStr}
**Reconciled up to**: ${dateStr}
**Purpose**: Track source file sizes for the /streamline command
**Total**: ${totalLines.toLocaleString()} lines across ${fileCounts.size} files

---

## Key Files

This document is a **generated tracking file** that tracks files exceeding 300 lines in the \`${srcDir}/\` directory. It is periodically regenerated for the \`/streamline\` command.

**No specific source files are referenced** - this IS the reference listing.

---

## Files Exceeding 300 Lines (Streamlining Candidates)

### Components & Views
`;

  if (over300.length > 0) {
    for (const { filePath, count } of over300) {
      doc += `- \`${filePath}\` - ${count} lines\n`;
    }
  } else {
    doc += '(No files exceeding 300 lines)\n';
  }

  return { doc, totalLines };
}

// --- Main ---
const latestFile = findLatestFolderStructure();

if (!latestFile) {
  console.log(JSON.stringify({ action: 'error', message: 'No Folder-Structure file found in ' + MISC_DIR }));
  process.exit(2);
}

const fileDate = extractDate(latestFile);
const isOutdated = fileDate < today;

if (checkOnly) {
  console.log(JSON.stringify({
    action: 'check',
    oldFile: latestFile,
    fileDate,
    today,
    isOutdated
  }));
  process.exit(isOutdated ? 0 : 1);
}

if (!isOutdated) {
  console.log(JSON.stringify({
    action: 'current',
    oldFile: latestFile,
    fileDate,
    today,
    message: 'Folder-Structure is current (date matches or is in the future)'
  }));
  process.exit(0);
}

// File is outdated — update it
const oldPath = join(MISC_DIR, latestFile);
const oldContent = readFileSync(oldPath, 'utf-8');
const oldCounts = parseOldCounts(oldContent);

// Walk source directory and count all files
const project = detectProject();
const srcFiles = walkSrc(project);
const fileCounts = new Map();

for (const filePath of srcFiles) {
  const count = countLines(filePath);
  fileCounts.set(filePath, count);
}

// Identify changes
const changedFiles = [];
for (const [filePath, newCount] of fileCounts.entries()) {
  const oldCount = oldCounts.get(filePath) || 0;
  if (oldCount !== newCount) {
    changedFiles.push({ path: filePath, oldCount, newCount });
  }
}

// Also track removed files (in old but not in new)
for (const [filePath, oldCount] of oldCounts.entries()) {
  if (!fileCounts.has(filePath)) {
    changedFiles.push({ path: filePath, oldCount, newCount: 0, removed: true });
  }
}

// Generate new document
const { doc, totalLines } = generateDocument(fileCounts, today, project.srcDir);

// Write new file
const newFilename = `${today}-Folder-Structure.md`;
const newPath = join(MISC_DIR, newFilename);
writeFileSync(newPath, doc, 'utf-8');

// Delete old file
if (latestFile !== newFilename) {
  unlinkSync(oldPath);
}

// Clean deprecated directories
const deprecatedCleaned = cleanDeprecatedDirs(project.srcDir);

// Sort changes by magnitude of change
changedFiles.sort((a, b) => Math.abs(b.newCount - b.oldCount) - Math.abs(a.newCount - a.oldCount));

const over300 = [...fileCounts.entries()].filter(([, c]) => c >= 300).length;

console.log(JSON.stringify({
  action: 'updated',
  oldFile: latestFile,
  newFile: newFilename,
  fileDate,
  today,
  totalFiles: fileCounts.size,
  filesOver300: over300,
  totalLines,
  changedCount: changedFiles.length,
  changedFiles: changedFiles.slice(0, 20), // Top 20 changes
  deprecatedCleaned
}));
