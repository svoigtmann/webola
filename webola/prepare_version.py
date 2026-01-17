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

def packages(lines):
    name = lambda s: s.split('==')[0]
    return set(map(name, lines)) - {'setuptools'}

def run(cmd):
    return subprocess.run(cmd.split(), stdin=subprocess.DEVNULL, capture_output=True, text=True).stdout.splitlines()

def pipreqs(**kwargs):
    cmd    = Path().home() / 'venv' / 'bin' / 'pipreqs'
    needed = packages(run (f'{cmd} --print'))

    for package, mapping in kwargs.items():
        if package in needed:
            for keyword, needs in mapping.items():
                if found := len(run(f'ack --py -c -l {keyword}'))-1:
                    needed.add(needs)
    return needed

def prepare_requirements():
    require = Path('requirements.txt')
    current = packages(require.read_text().splitlines())
    needed  = pipreqs (PyQt5={'QtWebEngine' : 'PyQtWebEngine', 
                              'QtMultimedia': 'PyQt5-multimedia'})
    
    if needed != current:
        require.write_text("\n".join(needed))
        names = ", ".join(f"'{n}'" for n in needed)
        setup = Path('setup.py')
        text  = re.sub(r'install_requires\s*= .*\n', f'install_requires = [{names}],\n', setup.read_text()) 
        setup.write_text(text)
        return 'requirements.txt'
    else:
        return None

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
