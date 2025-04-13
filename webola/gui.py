from PyQt5 import Qt, QtCore
from PyQt5.Qt import QShortcut, QKeySequence, QApplication, QHBoxLayout, QFrame,QSplitter, QFont, QTextEdit, QIcon, QTimer, QSize, QMainWindow,\
    QMessageBox, QCoreApplication, QVBoxLayout

from pony import orm

import time

from webola.database import Starter, Wettkampf
from webola.controlbar import ControlBar
from webola.tabs  import WebolaTabs

from pathlib import Path
import psutil
from webola.dialogs import AskReallyQuit, AskYesNo, AskXlsOrSql
from webola.importer import xlsx2sql
import sys
from webola.runner import run_export


'''
TODO
 o write manual
 o get rid of parent references
 o Werden alle Staffeln eines Laufes immer gemeinsam gewertet? 
'''

def early_exit(msg):
    box = QMessageBox(QMessageBox.Critical, "Webola", msg)
    box.setWindowIcon(QIcon(":/webola.png"))
    box.exec()
    sys.exit(1)

def yes_no_question(msg, info=""):
    return AskYesNo("Webola", msg, info).exec() == AskYesNo.Ok

def maybe_use_sql_file(xlsx, force):
    if force: return xlsx
    
    dlg = AskXlsOrSql(xlsx)
    dlg.exec()
    if dlg.clickedButton() == dlg.use_xlsx:
        return xlsx
    elif dlg.clickedButton() == dlg.use_sql:
        return None
    else:
        sys.exit(1)

def check_outfile(filename, force):
    if filename is None: return None
    outfile = Path(filename)

    if outfile.suffix != '.xlsx':
        early_exit("Als Ausgabe wurde <b>%s</b> angegeben, aber nur <b>xlsx</b> Dateien sind erlaubt." % outfile.name)        
    
    if outfile.is_file() and not force and not yes_no_question(
                "Die Datei <b>%s</b> existiert bereits." % outfile.name,
                "Soll die Datei wirklich überschrieben werden?"):
        sys.exit(1)
    return outfile

def read_wettkampf_from_db(sql):
    candidates = Wettkampf.select()[:]
    if len(candidates) >= 2:
        data = "".join( "<br>&nbsp;&nbsp;&nbsp;o %s (%s)" % (w.name, w.datum) for w in candidates )
        early_exit("Die SQL-Datei <b>%s</b> enhält mehrere Wettkämpfe: <br>" % sql
                   +"%s<br><br>Bitte die SQL-Datei manuell reparieren." % data)        
    elif len(candidates) == 1:
        return candidates[0]
    else:
        return Wettkampf.create()


class LogEdit(QTextEdit):
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        self.setReadOnly(True)
        font = QFont("Monospace");
        font.setStyleHint(QFont.TypeWriter);
        self.setFont(font)
        
    # def write(self,html):
    #     file = open(str(html), 'w')
    #     file.write(self.toHtml())
    #     file.close()
        
    def msg(self, text, sec):
        html = '<strong>%s %s</strong> %s' % (self.timepoint(), self.run_time(sec), text)
        self.append(html)
        
    def timepoint(self):
        return time.strftime("%H:%M:%S", time.localtime())
 
    def run_time(self, sec):
        if sec == 0:
            return "(-------)"
        else:
            msec = int(10*(sec - int(sec)))
            return "(%s.%d)" % (time.strftime("%M:%S", time.localtime(sec)),msec)
    
    # def webola(self): return self.parent().parent()
    
#def decorateSplitter(splitter, index=1):
#    gripLength = 25; 
#    gripWidth = 1;
#    grips = 3;
#    #splitter.setOpaqueResize(False)
#    #splitter.setChildrenCollapsible(False)
#    splitter.setHandleWidth(20)
#    handle = splitter.handle(index)
#    layout = QHBoxLayout(handle)
#    layout.setSpacing(1)
#    layout.addStretch()
#    vbox = QVBoxLayout()
#    for _ in range(grips):
#        line = QFrame(handle)
#        line.setMinimumSize(gripLength, gripWidth)
#        line.setMaximumSize(gripLength, gripWidth)
#        line.setFrameShape(QFrame.HLine)
#        vbox.addWidget(line)
#    layout.addLayout(vbox)
#    layout.addStretch()
#    return splitter

def indicateSplitter(splitter, index=1, collapse=False):
    splitter.setHandleWidth(13)
    handle = splitter.handle(index)
    line   = QFrame(handle)
    line.setFrameShape(QFrame.HLine)
    layout = QHBoxLayout(handle)
    layout.addWidget(line)
    if collapse:
        pos = splitter.getRange(index)[1]
        splitter.moveSplitter(pos,1)
    return splitter
                                

class CheckBatteryTimer(QTimer):
    def __init__(self, webola):
        super().__init__()
        self.size = QSize(32,32)
        
        self.timeout.connect(lambda: self.update_info(webola))
        self.start(5*1000)

    def update_info(self, webola):
        power, percent = self.check_battery_level()
        level = 'critical' if percent <= 25 else ( 
                'low'      if percent <= 50 else (
                'medium'   if percent <= 75 else (
                'full'     )))     
        if power is None:
            pixmap  = QIcon(f":/battery_{level}_powered.png").pixmap(self.size)
            tooltip = f"{percent}%"
        elif power:
            pixmap  = QIcon(f":/battery_{level}_powered.png").pixmap(self.size)
            tooltip = f"{percent}% (wird geladen)"
        else:
            pixmap  = QIcon(f":/battery_{level}.png").pixmap(self.size)
            tooltip = f"{percent}% (wird ENTLADEN)"

        for run in webola.tabs.runs():
            run.toolbar.battery.setPixmap (pixmap)
            run.toolbar.battery.setToolTip(tooltip)
        
    def check_battery_level(self):
        battery = psutil.sensors_battery()
        if battery:
            return battery.power_plugged, round(battery.percent)
        else:
            return None, 100
         
        #percent = round(QDateTime.currentDateTime().time().second()*100/60)
        #return percent % 2, percent

class WebolaGui(QMainWindow):
    def __init__(self, xlsx, sql, ergebnis, args):
        super().__init__()
        if xlsx: 
            wettkampf = xlsx2sql(xlsx, args.dm_mode)
        else:
            wettkampf = read_wettkampf_from_db(sql)
            
        wettkampf.vorlaeufe = args.vorlaeufe
        
        # qt_set_sequence_auto_mnemonic(False)
        self.setWindowIcon(QIcon(":/webola.png"))        
        self.setCentralWidget(Webola(wettkampf, ergebnis, args, self))
        
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.setMinimumSize(min(1300,rect.width()), min(800,rect.height()))

        qtRectangle = self.frameGeometry()
        centerPoint = rect.center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

    def toggle_fullscreen(self):
        self.setWindowState( Qt.Qt.WindowNoState if self.isFullScreen() else Qt.Qt.WindowFullScreen )

    def keyPressEvent(self, event):
        if event.key() == Qt.Qt.Key_Escape:
            # main window must not be closed directly when pressing ESC key
            # ... call Control's quit function
            return self.centralWidget().maybe_quit()
        else:
            return super().keyPressEvent(event)

    def closeEvent(self, event):
        event.ignore()
        self.centralWidget().maybe_quit()

class Webola(QFrame):
    
    def __init__(self, wettkampf, ergebnis, args, parent):
        super().__init__()
        
        self.setLayout(QVBoxLayout())
                
        self.wettkampf = wettkampf
        self.top_text_width = None
        self.bot_text_width = None
        self.log       = LogEdit()
        self.control   = ControlBar(wettkampf.disqualifikation, args)
        self.tabs      = WebolaTabs(self, args)
        self.battery   = CheckBatteryTimer(self)
                
        s = QSplitter(Qt.Qt.Vertical)
        self.layout().addWidget(s)
        s.addWidget(self.tabs)
        s.addWidget(self.log)
        s = indicateSplitter(s, collapse=True)
        
        self.layout().addWidget(self.control)
                             
        QShortcut(QKeySequence("Ctrl+E"), self, lambda: self.control.export.click())
        QShortcut(QKeySequence("Ctrl++"), self, lambda: self.scale_font(1.1))
        QShortcut(QKeySequence("Ctrl+-"), self, lambda: self.scale_font(0.9))
        QShortcut(QKeySequence("Ctrl+#"), self, lambda: self.scale_font())
        QShortcut(QKeySequence("PgUp"  ), self, lambda: self.tabs.switch_tab(+1))
        QShortcut(QKeySequence("PgDown"), self, lambda: self.tabs.switch_tab(-1))
        QShortcut(QKeySequence("Ctrl+F"), self, parent.toggle_fullscreen)

        self.control.fullscreen .clicked     .connect(parent.toggle_fullscreen)
        self.control.exit       .clicked     .connect(self.maybe_quit)
        self.control.export     .clicked     .connect(self.export)
        self.control.search     .found       .connect(self.tabs.show_run)
        self.control.max_penalty.valueChanged.connect(self.max_penalty_changed)
        
        self.max_penalty_changed(self.control.max_penalty.value()) # force DB's wettkampf.disqualifikation to be an int
        self.tabs.fill_from_db(self, args)
        
        if ergebnis is not None:
            self.control.xlsx.set_filename_and_path(ergebnis)

        for run in self.tabs.runs():
            run.update_tooltips()
        
        self.battery.update_info(self)

        QTimer.singleShot(100, self.scale_font)
        
        #self.control.split.setValue(3)
        #self.control.format.setCurrentIndex(2)
        #self.export()
        #orm.set_sql_debug(True)
        #orm.commit()
        #sys.exit(1)
      
    def maybe_quit(self):
        running = [ "'%s'" % r.name() for r in self.tabs.runs() if r.is_running() ] 
        if running:
            QMessageBox.information(self, "Programm beenden", "Bitte zuerst %s beenden." % ", ".join(running), QMessageBox.Ok)
            return
        
        if self.tabs.args.force or AskReallyQuit().exec() == AskReallyQuit.Ok:    
            QCoreApplication.quit()
            
    @staticmethod
    def unique_key(name, team, cnt=0):
        # mark duplicate names with * or **
        uname = "%s%s" % (name, cnt*"*")
        info  = "Staffel" if team.ist_staffel() else team.single().klasse
        info  = "" if info == "" else ", %s" % info
        return "%s (%s, Nr. %s%s)" % (uname, team.lauf.name, str(team.nummer), info)
        
    def start_search(self):
        data = {}
        for starter in orm.select( s for s in Starter if s.name and s.team.lauf.wettkampf == self.wettkampf):
            key = None
            cnt = 0
            while key is None or key in data.keys():
                key = self.unique_key(starter.name, starter.team, cnt)
                cnt += 1
            data[key] = starter.team.lauf 
        return data        

    def max_penalty_changed(self, n):
        self.wettkampf.disqualifikation = n
        orm.commit()
                    
    def export(self):
        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        orm.commit()
        indicator, exporter = run_export(self.wettkampf, self.tabs, self.control)
        if indicator: self.indicator = indicator
        if exporter : self.exporter  = exporter
        QApplication.restoreOverrideCursor()
#        
#        xlsx    = self.control.xlsx.file()
#        tex     = Path(xlsx).with_suffix('.tex')
#        formate = self.control.format.currentText().split('+')
#        
#        if xlsx:
#            QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
#
#            orm.commit()
#            
#            head = self.tabs.sheet.get_header()
#            ms   = xls_export_zielliste(self.wettkampf, xlsx, head, self)
#            
#            if 'TEX' in formate:
#                
#                to_do  = tex_export_zielliste (self.wettkampf, tex, head, formate)
#                
#                to_do += prepare_latex_export_urkunden(Path(xlsx), ms, SimpleNamespace(
#                    wettkampf = self.wettkampf, 
#                    formate   = formate, 
#                    maxres    = MaxRes(self.control.maxres_einzel .value(), 
#                                       self.control.maxres_staffel.value()),
#                    titel     = head, 
#                    datum     = self.tabs.sheet.date .text(),
#                    ort       = self.tabs.sheet.ort  .text(), 
#                    template  = self.control.template.currentText(), 
#                    staffel   = self.control.staffel .currentText(), 
#                    modus     = self.control.mode    .currentText(), 
#                    strafen   = self.control.strafen .currentText(),
#                    teamname  = self.control.teamname.currentText()))
#
#                if to_do:
#                    self.indicator = Indicator(self.control.export)
#                    self.exporter  = ExportThread(to_do)
#                    self.exporter.finished.connect(lambda: self.indicator.reset('Export'))
#                    self.exporter.start()
#
#            QApplication.restoreOverrideCursor()
           
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_font() # force update for all buttons 

    def scale_font(self, fac=None):   
        if fac is None:
            new = QApplication.font().pointSize()
        else:
            f  = QApplication.font()
            new = max(5, 10 if fac is None else round(f.pointSize() * fac)) 
            f.setPointSize(new) 
            QApplication.setFont(f)

        self.top_text_width = None
        self.bot_text_width = None
        
        #TeamButton.top_text_width = None
        #TeamButton.bot_text_width = None
    
        self.tabs.scale_font(new, fac)
