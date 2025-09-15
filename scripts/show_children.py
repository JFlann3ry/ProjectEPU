import subprocess

from alembic.config import Config
from alembic.script import ScriptDirectory

cfg=Config('alembic.ini')
script=ScriptDirectory.from_config(cfg)
# get current
p=subprocess.run([r'e:\ProjectEPU\venv\Scripts\python.exe','-m','alembic','current'],capture_output=True,text=True)
out=p.stdout.strip() or p.stderr.strip()
lines=out.splitlines()
cur=None
if lines:
    cur=lines[-1].split()[-1]
print('current=',cur)
children={}
for rev in script.walk_revisions(base='base', head='heads'):
    dr=rev.down_revision
    if dr is None:
        drs=[]
    elif isinstance(dr, tuple):
        drs=list(dr)
    else:
        drs=[dr]
    for p in drs:
        children.setdefault(p,[]).append(rev.revision)
print('\nchildren of current:')
for c in children.get(cur,[]):
    print(' -',c)
