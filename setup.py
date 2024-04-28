from setuptools import setup
from pathlib import Path

def get_version(file):
    with Path(file).resolve(strict=True).open() as data:
        for line in data.readlines():
            if line.startswith('__version__'):
                return line.split('=')[1].strip('"\' \n')
    raise RuntimeError("Unable to find version string.")

setup(
    name             = 'webola',
    version          = get_version("webola/__init__.py"),    
    description      = "Software zur Zeitmessung bei Bogenläufen",
    url              = "https://github.com/svoigtmann/webola",
    author           = 'Steffen Voigtmann',
    author_email     = 'steffen.voigtmann@web.de',
    license          = 'GPLv3',
    packages         = ['webola'],
    package_data     = {"webola": ["bogenlauf.sty"]},
    install_requires = ['lxml', 'numexpr', 'PyQt5', 'PyQt5_sip', 'QtAwesome', 'yattag'],
    classifiers      = [],
)
