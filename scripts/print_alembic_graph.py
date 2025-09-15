from alembic.config import Config
from alembic.script import ScriptDirectory

cfg = Config('alembic.ini')
script = ScriptDirectory.from_config(cfg)

print("Alembic revision graph dump:\n")
for rev in script.walk_revisions(base='base', head='heads'):
    # rev.down_revision may be a tuple or a string or None
    print(f"revision: {rev.revision}\n  down_revision: {rev.down_revision}\n  message: {rev.doc}\n  path: {getattr(rev, 'path', None)}\n")

# Also produce a mapping of which revisions reference the problematic ones
targets = ['20250911_0020_add_custom_event_type', '20250911_0022_add_theme_isactive']
print('\nReferences to problem revisions:')
for rev in script.walk_revisions(base='base', head='heads'):
    dr = rev.down_revision
    if isinstance(dr, tuple):
        drs = list(dr)
    else:
        drs = [dr]
    for t in targets:
        if t in drs:
            print(f"{rev.revision} -> {dr}")
