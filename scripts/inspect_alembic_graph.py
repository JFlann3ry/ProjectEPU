import glob
import re

files=glob.glob('e:/ProjectEPU/alembic/versions/*.py')
info=[]
for f in sorted(files):
    s=open(f,'r',encoding='utf-8').read()
    rev=re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]",s,flags=re.M)
    down=re.search(r"^down_revision\s*=\s*(.+)$",s,flags=re.M)
    revv=rev.group(1) if rev else None
    downv=None
    if down:
        dv=down.group(1).strip()
        if dv.startswith('('):
            parts=re.findall(r"['\"]([^'\"]+)['\"]",dv)
            downv=parts
        else:
            m=re.search(r"['\"]([^'\"]+)['\"]",dv)
            downv=[m.group(1)] if m else [dv]
    info.append((f,revv,downv))
for f,rev,downs in info:
    print(rev, '->', downs, '  ', f.split('alembic\\versions\\')[-1])
