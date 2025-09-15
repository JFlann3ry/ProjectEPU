import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'alembic' / 'versions'
rev_re = re.compile(r"^revision\s*=\s*['\"]([\w_\-]+)['\"]", re.M)
down_re = re.compile(r"^down_revision\s*=\s*['\"]([\w_\-]+)['\"]", re.M)

revisions = {}
down_revs = set()

for f in sorted(p.glob('*.py')):
    text = f.read_text()
    revm = rev_re.search(text)
    drm = down_re.search(text)
    rev = revm.group(1) if revm else None
    dr = drm.group(1) if drm else None
    if rev:
        revisions[rev] = f.name
    if dr:
        # down_revision can be comma-separated list; handle simple comma
        for part in [x.strip().strip('\"\'') for x in dr.replace('\n','').split(',') if x.strip()]:
            down_revs.add(part)

heads = set(revisions.keys()) - set(down_revs)

print('Total revisions:', len(revisions))
print('Total referenced down_revisions:', len(down_revs))
print('\nHeads:')
for h in sorted(heads):
    print(h, '->', revisions[h])

# Find down_revisions that don't match any revision
orphan_downs = [d for d in down_revs if d not in revisions]
if orphan_downs:
    print('\nOrphan down_revisions (referenced but missing):')
    for d in orphan_downs:
        print(d)
else:
    print('\nNo orphan down_revisions found.')
