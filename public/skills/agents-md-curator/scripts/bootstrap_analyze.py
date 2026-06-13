"""Bootstrap analysis: score first 100 commits against imported lines."""
import sqlite3
import re
import subprocess
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'claude-storage.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Get all lines
lines = cur.execute("SELECT id, content, section FROM lines").fetchall()

# Relevance patterns for each line
line_patterns = {
    1: {  # Delegate linting to beautifier
        'path_patterns': [r'lint', r'prettier', r'eslint'],
        'msg_patterns': [r'lint', r'beautif', r'format'],
    },
    2: {  # Pre-alpha, no migration
        'path_patterns': [r'firebase', r'firestore', r'schema', r'migration'],
        'msg_patterns': [r'schema', r'migration', r'refactor.*data', r'wipe'],
    },
    3: {  # File lifecycle terminology
        'path_patterns': [r'file-lifecycle', r'upload', r'processing'],
        'msg_patterns': [r'file.*lifecycle', r'terminology', r'upload.*process'],
    },
    4: {  # Dedup terminology
        'path_patterns': [r'[Dd]edup', r'duplicate', r'hash'],
        'msg_patterns': [r'dedup', r'duplicate', r'hash', r'redundant', r'existing'],
    },
    5: {  # Tests in /tests folder
        'path_patterns': [r'^tests/'],
        'msg_patterns': [r'test'],
    },
    6: {  # Tech stack
        'path_patterns': [r'\.vue$', r'vite\.config', r'vuetify', r'pinia', r'tailwind'],
        'msg_patterns': [r'vue', r'vite', r'vuetify', r'pinia', r'tailwind'],
    },
    7: {  # Multi-app SSO
        'path_patterns': [r'sso', r'AppSwitcher', r'auth'],
        'msg_patterns': [r'sso', r'auth', r'multi-app'],
    },
    8: {  # Dev server command
        'path_patterns': [r'vite\.config', r'package\.json'],
        'msg_patterns': [r'dev.*server', r'localhost'],
    },
    9: {  # SSO testing commands
        'path_patterns': [r'sso', r'test-sso'],
        'msg_patterns': [r'sso.*test', r'dev:intranet'],
    },
    10: {  # Pre-commit commands
        'path_patterns': [r'package\.json', r'eslint'],
        'msg_patterns': [r'pre-commit', r'lint', r'test:run', r'build'],
    },
    11: {  # Feature-module doc structure
        'path_patterns': [r'docs/.*CLAUDE\.md', r'docs/Features', r'docs/System'],
        'msg_patterns': [r'documentation.*structure', r'CLAUDE\.md.*module'],
    },
    12: {  # Doc pointers
        'path_patterns': [r'docs/System', r'docs/Features'],
        'msg_patterns': [r'doc.*pointer', r'doc.*feature'],
    },
    13: {  # Auth state machine
        'path_patterns': [r'auth', r'authStore', r'stores/auth'],
        'msg_patterns': [r'auth.*state', r'isInitialized', r'isAuthenticated'],
    },
    14: {  # Solo firm architecture
        'path_patterns': [r'firm', r'team', r'stores/auth'],
        'msg_patterns': [r'firm', r'solo.*user', r'team.*one'],
    },
    15: {  # Web worker hashing
        'path_patterns': [r'worker', r'fileHash', r'blake'],
        'msg_patterns': [r'worker', r'hash', r'blake'],
    },
    16: {  # Hash-based dedup
        'path_patterns': [r'dedup', r'hash', r'fileHash'],
        'msg_patterns': [r'dedup', r'hash.*dedup', r'unique.*size'],
    },
    17: {  # Multi-app SSO shared config
        'path_patterns': [r'\.env', r'firebase', r'AppSwitcher'],
        'msg_patterns': [r'sso', r'firebase.*config', r'shared.*auth'],
    },
    18: {  # Edit tool emoji encoding
        'path_patterns': [r'CLAUDE\.md'],
        'msg_patterns': [r'emoji', r'encoding', r'string.*replace'],
    },
    19: {  # Don't modify production branch
        'path_patterns': [r'hosting', r'Promotion'],
        'msg_patterns': [r'production', r'branch', r'deploy'],
    },
    20: {  # Vue 3 ref typing
        'path_patterns': [r'\.vue$', r'\.ts$'],
        'msg_patterns': [r'ref.*type', r'typescript'],
    },
    21: {  # Tailwind directive order
        'path_patterns': [r'tailwind', r'style\.css', r'main\.css'],
        'msg_patterns': [r'tailwind', r'css.*directive'],
    },
    22: {  # Vuetify + Tailwind conflicts
        'path_patterns': [r'vuetify', r'tailwind'],
        'msg_patterns': [r'vuetify.*tailwind', r'specificity'],
    },
    23: {  # Firebase getRedirectResult
        'path_patterns': [r'auth', r'redirect'],
        'msg_patterns': [r'redirect.*result', r'getRedirect'],
    },
    24: {  # Firestore rules not filters
        'path_patterns': [r'firestore\.rules', r'security'],
        'msg_patterns': [r'security.*rule', r'firestore.*rule'],
    },
    25: {  # Web worker self.onmessage
        'path_patterns': [r'worker'],
        'msg_patterns': [r'worker.*test', r'self\.onmessage'],
    },
    26: {  # Vitest jsdom + web worker
        'path_patterns': [r'vitest\.config', r'worker.*test'],
        'msg_patterns': [r'vitest.*jsdom', r'worker.*test'],
    },
    27: {  # Single source of truth docs (global)
        'path_patterns': [r'docs/'],
        'msg_patterns': [r'documentation', r'single.*source'],
    },
    28: {  # Optimize plans for Sonnet (global)
        'path_patterns': [r'plans/'],
        'msg_patterns': [r'plan', r'implementation'],
    },
    29: {  # Windows backslash paths (global)
        'path_patterns': [],
        'msg_patterns': [r'path.*format', r'windows'],
    },
}

# Parse commits
os.chdir('C:/Users/Brahm/Git/Listbot')
result = subprocess.run(
    ['git', 'log', '--reverse', '--format=COMMIT:%H|%s', '--name-only', '-n', '100'],
    capture_output=True, text=True, encoding='utf-8'
)

commits = []
current_commit = None
for line in result.stdout.strip().split('\n'):
    if line.startswith('COMMIT:'):
        if current_commit:
            commits.append(current_commit)
        parts = line[7:].split('|', 1)
        current_commit = {'hash': parts[0], 'msg': parts[1] if len(parts) > 1 else '', 'files': []}
    elif line.strip() and current_commit:
        current_commit['files'].append(line.strip())
if current_commit:
    commits.append(current_commit)

print(f"Parsed {len(commits)} commits")

first_hash = commits[0]['hash'] if commits else None
last_hash = commits[-1]['hash'] if commits else None
commit_range = f"{first_hash[:8]}..{last_hash[:8]}" if first_hash and last_hash else "unknown"

# Score each line
line_scores = {}
for line_id, patterns in line_patterns.items():
    relevant_paths = set()
    event_count = 0

    for commit in commits:
        path_match = False
        msg_match = False
        matched_paths = []

        for fp in commit['files']:
            for pp in patterns['path_patterns']:
                if re.search(pp, fp, re.IGNORECASE):
                    path_match = True
                    matched_paths.append(fp)
                    break

        for mp in patterns['msg_patterns']:
            if re.search(mp, commit['msg'], re.IGNORECASE):
                msg_match = True
                break

        if path_match or msg_match:
            event_count += 1
            relevant_paths.update(matched_paths[:3])

    if event_count > 0:
        line_scores[line_id] = {
            'event_count': event_count,
            'relevant_paths': relevant_paths
        }

# Insert relevance events
events_inserted = 0
for line_id, score in sorted(line_scores.items(), key=lambda x: -x[1]['event_count']):
    paths_str = ','.join(list(score['relevant_paths'])[:10])
    cur.execute(
        "INSERT INTO relevance_events (line_id, repo, relevant_paths, commit_range, event_type, notes) VALUES (?, ?, ?, ?, 'observed', ?)",
        (line_id, 'Listbot', paths_str, commit_range, f"{score['event_count']} matching commits in first 100")
    )
    events_inserted += 1

# Set repo cursor
cur.execute(
    "INSERT OR REPLACE INTO repo_cursors (repo, last_commit_hash, last_commit_timestamp) VALUES (?, ?, datetime('now'))",
    ('Listbot', last_hash)
)

conn.commit()

# Print results
print(f"\nRelevance events created: {events_inserted}")
print(f"Cursor set to: {last_hash[:12]}")
print(f"\nLine scores (by relevance count):")
for line_id, score in sorted(line_scores.items(), key=lambda x: -x[1]['event_count']):
    content = [l for l in lines if l[0] == line_id][0][1][:60]
    print(f"  Line {line_id:2d}: {score['event_count']:3d} events | {content}...")

# Lines with NO relevance
no_relevance = set(range(1, 30)) - set(line_scores.keys())
if no_relevance:
    print(f"\nLines with NO relevance in first 100 commits:")
    for lid in sorted(no_relevance):
        content = [l for l in lines if l[0] == lid][0][1][:60]
        print(f"  Line {lid:2d}: {content}...")

conn.close()
