from collections import deque

from alembic.config import Config
from alembic.script import ScriptDirectory

cfg = Config('alembic.ini')
script = ScriptDirectory.from_config(cfg)

# build parent mapping: revision -> list of parents
parents = {}
for rev in script.walk_revisions(base='base', head='heads'):
    dr = rev.down_revision
    if dr is None:
        parents[rev.revision] = []
    elif isinstance(dr, tuple):
        parents[rev.revision] = list(dr)
    else:
        parents[rev.revision] = [dr]


def is_ancestor(x, y):
    # BFS from y up to base; see if we encounter x
    seen = set()
    q = deque([y])
    while q:
        cur = q.popleft()
        if cur == x:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        for p in parents.get(cur, []):
            if p is not None:
                q.append(p)
    return False

# find merges with tuple down_revision
print('Detecting overlapping merge down_revision tuples...\n')
for rev in script.walk_revisions(base='base', head='heads'):
    dr = rev.down_revision
    if isinstance(dr, tuple):
        drs = list(dr)
        # check pairwise
        for i in range(len(drs)):
            for j in range(i+1, len(drs)):
                a = drs[i]
                b = drs[j]
                if a is None or b is None:
                    continue
                if is_ancestor(a, b):
                    print(
                        f"{rev.revision}: {a} is ancestor of {b} "
                        "-> recommend down_revision = '" + b + "'"
                    )
                elif is_ancestor(b, a):
                    print(
                        f"{rev.revision}: {b} is ancestor of {a} "
                        "-> recommend down_revision = '" + a + "'"
                    )

print('\nDone')
