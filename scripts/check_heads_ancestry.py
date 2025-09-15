from alembic.config import Config
from alembic.script import ScriptDirectory

cfg=Config('alembic.ini')
script=ScriptDirectory.from_config(cfg)
heads=script.get_heads()
print('heads=',heads)
# build parents mapping
parents={}
for rev in script.walk_revisions(base='base', head='heads'):
    dr=rev.down_revision
    if dr is None:
        parents[rev.revision]=[]
    elif isinstance(dr, tuple):
        parents[rev.revision]=list(dr)
    else:
        parents[rev.revision]=[dr]
from collections import deque


def is_ancestor(a,b):
    q=deque([b]); seen=set()
    while q:
        cur=q.popleft()
        if cur==a: return True
        if cur in seen: continue
        seen.add(cur)
        for p in parents.get(cur,[]):
            if p is not None: q.append(p)
    return False

for i in range(len(heads)):
    for j in range(i+1,len(heads)):
        a=heads[i]; b=heads[j]
        print(f"{a} ancestor of {b}?", is_ancestor(a,b))
        print(f"{b} ancestor of {a}?", is_ancestor(b,a))
