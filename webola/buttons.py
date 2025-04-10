from PyQt5.Qt import Qt, QPushButton, QLabel, QVBoxLayout, QToolButton, QIcon,\
    QWidget
from webola.containers import VBoxContainer

class ToolButton(QToolButton):
    def __init__(self, name, slot=None, tip=None, parent=None):
        QToolButton.__init__(self, parent)
        self.setFocusPolicy(Qt.NoFocus)
        self.setIcon(QIcon(name))
        if slot: self.clicked.connect(slot)
        if tip:  self.setToolTip(tip)

class NoFocusButton(QPushButton):
    def __init__(self, text, slot=None, parent=None, enable=True):
        QPushButton.__init__(self, text, parent)
        self.setFocusPolicy(Qt.NoFocus)
        self.setEnabled(enable)
        if slot is None: slot = lambda: print(text)
        if slot:         self.clicked.connect(slot) # allow to set no slot by providing False

#class ButtonLabel(QLabel):
#    def __init__(self, label, parent):
#        QLabel.__init__(self, parent)
#        self.setText(label)
#        #self.setMargin(0)
#        #self.setContentsMargins(0,0,0,0)
#        #self.setAlignment(Qt.AlignCenter)
#        
#    def mousePressEvent(self, event):
#        if event.button() == Qt.LeftButton:
#            self.parent().click()           
#

#class ButtonLabel(QWidget):
#    def __init__(self, text, parent):
#        super().__init__()
#        self.parent = parent
#        
#    def setText(self, text):
#        pass
#        
#class SubtitleButton(NoFocusButton):
#    def __init__(self, slot=None, parent=None):
#        NoFocusButton.__init__(self, '', self.was_clicked, parent)        
#        
#        self.label= QLabel(self)
#        self.label.setStyleSheet('background-color: lightblue;border-width: 0px;')
#        
#        self.main = ButtonLabel('', self)
#        self.sub  = ButtonLabel('', self)
#        #
#        #self.main.setStyleSheet('background-color: lightblue;border-width: 0px;')
#        #self.sub.setStyleSheet('background-color: lightgreen;border-width: 0px;')
#        ##self.main.setContentsMargins(0,0,0,0)
#        ##self.sub.setContentsMargins(0,0,0,0)
#        ##self.main.setAlignment(Qt.AlignBottom)
#        #self.sub.setAlignment(Qt.AlignTop)        
#        ##self.setStyleSheet("QPushButton {border-style: outset; border-width: 0px;}")
#        #self.setStyleSheet( "padding: 0px; border:0px;" );
#        #
#        #v = QVBoxLayout(self)
#        #f = VBoxContainer()
#        #f.layout().setSpacing(0)
#        #f.layout().addStretch()
#        #f.setContentsMargins(0, 0, 0, 0)
#        #v.addWidget(f)
#        #f.add(self.main,stretch=4)
#        #f.add(self.sub,stretch=3)
#        #f.layout().addStretch()
#        ##v.setSpacing(0)
#        ###v.setContentsMargins(0,0,0,0)
#        ##v.addStretch()
#        ##v.addWidget(self.main)
#        ##v.addWidget(self.sub )
#        ##v.addStretch()
#        #self.setLayout(v)
#
#    def scale_fonts(self, new):
#        self.setMinimumHeight(round(70+5*(new-10))) # 10pt => 70, 12pt => 80
#        for w,fac in zip((self.main, self.sub),(1.125, 0.8)):
#            f = w.font()
#            f.setPointSize(round(new*fac)) 
#            w.setFont(f)
#
#    def setText(self, text, sub=None):
#        #two = "<font size=18>%s</font><br><b><font size=24>%s</font></b>" % (text, sub or '')
#        two = "%s<br>%s" % (text, sub or '')
#        self.label.setText(two)
#        
#        
#        
#        #self.main.setText(text)
#        #if sub is not None: self.sub.setText(sub)
#