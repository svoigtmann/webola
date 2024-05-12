#!/usr/bin/env python

from pathlib import Path
from datetime import date
import re
import subprocess

today   = date.today()
version = f"{today.year}.{today.month}.{today.day}" 

def changed(file):
    changed = subprocess.run(['git', 'diff', file], capture_output=True).stdout.decode()
    return file if changed else None

def commit(msg, files):
    for file in files:
        cmd = ['git', 'add', file]
        print(" ".join(cmd))
        subprocess.run(cmd)
    cmd = ['git', 'commit', '-m', msg]
    print(" ".join(cmd))
    subprocess.run(cmd)

def prepare_version(file):
    with Path(file).open('w') as f:
        f.write(f"__version__ = '{version}'\n")
    return changed(file)

def prepare_readme(file):
    with Path(file).open() as f:
        readme = f.read()
    readme = re.sub(r'\# Webola -- \*We\*rderaner \*Bo\*gen\*la\*uf     \(.*\)'   , f'# Webola -- *We*rderaner *Bo*gen*la*uf     ({version})', readme)
    readme = re.sub(r'Copyright 2019-\d\d\d\d', f'Copyright 2019-{today.year}', readme)
    with Path(file).open('w') as f:
        f.write(readme)
    return changed(file)

def prepare_requirements():
    with Path('requirements.txt').open() as f:
        need   = lambda l: f"'{l.strip()}'"
        needed = ", ".join(map(need, f.readlines()))
    with Path('setup.py').open() as f:
        setup = f.read()
    setup = re.sub(r'install_requires\s*= .*\n', f'install_requires = [{needed}],\n', setup) 
    with Path('setup.py').open('w') as f:
        f.write(setup)
    return 'requirements.txt'

def collect(*files):
    return list(filter(None, files))

files = collect(prepare_version('webola/__init__.py'),
                prepare_readme ('README.md'             ))
if files:
    commit(f"new version number {version}", files)

if changed('requirements.txt'):
    files = collect(prepare_requirements(),
                    changed('setup.py'))
    commit("requirements.txt changed", files)
