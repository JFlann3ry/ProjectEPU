import subprocess
import sys
from collections import deque

from alembic.config import Config
from alembic.script import ScriptDirectory

PYTHON = r"e:\\ProjectEPU\\venv\\Scripts\\python.exe"
ALEMBIC = [PYTHON, '-m', 'alembic']

cfg = Config('alembic.ini')
script = ScriptDirectory.from_config(cfg)


# helper to get current DB revision via alembic current
def get_current():
    p = subprocess.run(ALEMBIC + ['current'], capture_output=True, text=True)
    out = p.stdout.strip() or p.stderr.strip()
    # attempt to parse last token
    lines = out.splitlines()
    if not lines:
        return None
    last = lines[-1].strip()
    # last token likely the revision id
    tokens = last.split()
    return tokens[-1]

# build parent->children mapping
parents = {}
children = {}
for rev in script.walk_revisions(base='base', head='heads'):
    dr = rev.down_revision
    if dr is None:
        drs = []
    elif isinstance(dr, tuple):
        drs = list(dr)
    else:
        drs = [dr]
    parents[rev.revision] = drs
    for p in drs:
        children.setdefault(p, []).append(rev.revision)

# find path from current to target via DFS

def find_path(cur, target):
    # BFS from cur forward using children mapping
    q = deque([[cur]])
    seen = set([cur])
    while q:
        path = q.popleft()
        node = path[-1]
        if node == target:
            return path[1:]  # exclude current
        for c in children.get(node, []):
            if c in seen:
                continue
            seen.add(c)
            q.append(path + [c])
    return None

if __name__ == '__main__':
    targets = [
        '20250912_0021_merge_plan_revision',
        '20250912_0023_merge_11',
        '20250912_0024_final_merge',
    ]
    cur = get_current()
    print('current DB revision:', cur)
    if cur is None:
        print('Could not determine current revision')
        sys.exit(1)
    for t in targets:
        print('\n--- Advancing to target:', t)
        path = find_path(cur, t)
        if not path:
            print('No path found from', cur, 'to', t, '(maybe already ahead or disconnected)')
            # still try single upgrade to t
            cmds = [ALEMBIC + ['upgrade', t]]
        else:
            print('Path:', path)
            cmds = [ALEMBIC + ['upgrade', r] for r in path]
        for cmd in cmds:
            print('Running:', ' '.join(cmd))
            p = subprocess.run(cmd)
            if p.returncode != 0:
                print('Command failed:', ' '.join(cmd))
                sys.exit(p.returncode)
            cur = get_current()
            print('Current is now:', cur)
    print('\nAll targets processed')
