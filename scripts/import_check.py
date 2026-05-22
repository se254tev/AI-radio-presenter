import sys, glob, importlib, traceback
sys.path.insert(0, '.')
failed = []
all_mods = []
for p in glob.glob('app/**/*.py', recursive=True):
    if p.endswith('__init__.py'):
        continue
    mod = p[:-3].replace('/', '.').replace('\\', '.')
    all_mods.append(mod)

for mod in all_mods:
    try:
        importlib.import_module(mod)
        print('OK', mod)
    except Exception as e:
        print('FAIL', mod, type(e).__name__, e)
        failed.append((mod, type(e).__name__, str(e)))

print('\nSUMMARY: %d failed, %d ok' % (len(failed), len(all_mods)-len(failed)))
if failed:
    for m in failed:
        print(m)
