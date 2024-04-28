#!/usr/bin/env python3

from PyQt5.Qt import QApplication, QMessageBox, QFileDialog, QIcon, QSharedMemory,QStyleFactory
from os.path import sys
import argparse

from pony import orm

from webola.gui import WebolaGui, early_exit, maybe_use_sql_file, check_outfile
from pathlib import Path
from webola.database import db
from webola.utils import is_linux

# stackoverflow.com/questions/8786136/pyqt-how-to-detect-and-close-ui-if-its-already-running
class SingleApplication(QApplication):
    def __init__(self, argv, key):
        super().__init__(argv)
        # cleanup (only needed for unix)
        QSharedMemory(key).attach()
        self._memory = QSharedMemory(self)
        self._memory.setKey(key)
        if self._memory.attach():
            self._running = True
        else:
            self._running = False
            if not self._memory.create(1):
                raise RuntimeError(self._memory.errorString())

    def is_running(self):
        return self._running

def open_file():
    dlg = QFileDialog(None, 'Webola Startliste öffnen ...')
    dlg.setDirectory(str(Path.cwd()))
    dlg.setNameFilters(["XLSX Startliste (*.xlsx)", "SQL Datenbank (*.sql)"])
    dlg.setFileMode(QFileDialog.AnyFile)
    if dlg.exec():
        files = dlg.selectedFiles()
        assert len(files) == 1
        return files[0]
    else:
        sys.exit(1)


def find_files(filename, force, argv):
    
    if filename:
        starter = Path(filename)
    else: 
        box = QMessageBox(
            QMessageBox.Information, 'Webola', 
                    '<u><b>We</b>rderaner <b>Bo</b>gen<b>la</b>uf</u><br><br>'+
                    '<b>webola</b> ist eine Software zur Zeitmessung bei Bogenläufen. '+
                    'Die Informationen über startende Läufer:innen werden aus einer XLSX Datei gelesen (Startliste). Deshalb muss eine Startliste angegeben werden.'+
                    '<br><br>'+
                    '<b>Tipp:</b> Mit Strg-+ und Strg-- kann die Schriftgröße verändert werden.')
        box.setIconPixmap(QIcon(":/webola.png").pixmap(75,75))
        box.setWindowIcon(QIcon(":/webola.png"))
        box.exec()
        
        starter = Path(open_file())
    
    if not starter.is_file(): 
        early_exit("Die angeforderte Datei <b>%s</b> existiert nicht." % starter.name)
        
    if starter.suffix == '.xlsx':
        sql = starter.with_suffix('.sql')
        if sql.is_file():
            xlsx = maybe_use_sql_file(starter, force)
        else:
            xlsx = starter
    elif starter.suffix == '.sql':
        xlsx = None
        sql  = starter
    else:
        early_exit("Als Eingabe wurde <b>%s</b> angegeben, aber nur <b>xlsx</b> oder <b>sql</b> Dateien sind erlaubt." % starter.name)        

    if xlsx and sql.is_file(): sql.unlink()

    return xlsx.resolve() if xlsx else None , sql

def parse_arguments():
    parser = argparse.ArgumentParser(description='webola -- Werderaner Bogenlauf')
    parser.add_argument("input" , nargs='?', metavar= 'name.xlsx' , help="Starterliste entweder als name.xlsx oder name.sql.")
    parser.add_argument("-f", "--force"    , action = 'store_true', help="Überschreibe SQL-Datei ohne Nachfrage.")
    parser.add_argument("-p", "--pfeile"   , metavar= 'n'         , default=4, type=int, help="Anzahl Pfeile")
    parser.add_argument("-s", "--schiessen", metavar= 'n'         , default=3, type=int, help="Anzahl Schießen")
    parser.add_argument("-v", "--vorlaeufe", action = 'store_true', help="Verwende Vor- und Finalläufe (experimental)")
    parser.add_argument("-o", "--output"   , metavar= 'file.xlsx' , help="Ergebnisliste")
    return parser.parse_args()

if __name__ == '__main__':    
    args = parse_arguments()    
    app  = SingleApplication(sys.argv, 'webola')
    if app.is_running():
        box = QMessageBox(QMessageBox.Critical, "Webola", "Eine andere <b>Webola</b> Instanz läuft bereits, aber es ist nur eine Instanz erlaubt ....")
        box.setWindowIcon(QIcon(":/webola.png"))
        box.exec()
        sys.exit(1)
        
    if not is_linux(): QApplication.setStyle(QStyleFactory.create("Fusion"))             
    outfile   = check_outfile(args.output, args.force)        
    xlsx, sql = find_files(args.input, args.force, sys.argv)
                
    db.bind(provider='sqlite', filename=str(sql.resolve()), create_db=True)
    db.generate_mapping(create_tables=True)

    with orm.db_session:
        dlg = WebolaGui(xlsx, sql, str(outfile.resolve()) if outfile else None, args)
        dlg.show()
        app.exec()
    
    
    
    
    