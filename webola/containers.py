
from PyQt5.QtCore import Qt
from PyQt5.Qt import QHBoxLayout, QVBoxLayout, QFrame, QWidget

class Line(QFrame):
    def __init__(self, shape=QFrame.VLine, width=None):
        QFrame.__init__(self)
        self.setFrameShape(shape)
        self.setStyleSheet("border: 1px solid lightgray;")
        
        if width: 
            if shape == QFrame.VLine:
                self.setMinimumWidth(width)
            else:
                self.setMinimumHeight(width)

class BoxContainer(QFrame):
    
    def __init__(self, box_layout, parent=None):
        QFrame.__init__(self, parent)
        l = box_layout
        l.setContentsMargins(0, 0, 0, 0)
        self.setLayout(l)
        
    def add(self, widget, align=None, stretch=0, enabled=True, tooltip=None):
        if (align == Qt.AlignCenter or 
            align == Qt.AlignRight  or
            align == Qt.AlignBottom): 
            self.layout().addStretch()
        
        if isinstance(widget, QWidget):
            self.layout().addWidget(widget, stretch)                
        else:
            self.layout().addLayout(widget, stretch)                
        
        widget.setEnabled(enabled)
        
        if tooltip: widget.setToolTip(tooltip)
        
        if (align == Qt.AlignCenter or 
            align == Qt.AlignLeft   or
            align == Qt.AlignTop): 
            self.layout().addStretch()
        
        return widget

    def widgets(self):
        _all = [ self.layout().itemAt(idx).widget() for idx in range(self.layout().count()) ]
        return [ w for w in _all if w ]

    def set_frame(self, style=QFrame.Panel, m=5):
        self.setFrameShape( style )
        self.layout().setContentsMargins(m, m, m, m)
        return self

class HBoxContainer(BoxContainer):
    def __init__(self, parent=None):
        BoxContainer.__init__(self, QHBoxLayout(), parent)

class VBoxContainer(BoxContainer):
    def __init__(self, parent=None):
        BoxContainer.__init__(self, QVBoxLayout(), parent)
        