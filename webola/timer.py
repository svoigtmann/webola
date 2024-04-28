from PyQt5 import QtCore
from PyQt5.Qt import QTime, QTimer, QLabel, Qt


class Stoppuhr(QLabel):
    
    tic = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        QLabel.__init__(self, "00:00")
        self.clock = QTime()
        self.timer = QTimer(self)
        self.valid = False
        self.setAlignment(Qt.AlignCenter)

    def elapsed(self): 
        return round(self.clock.elapsed()/1000,1) if self.valid else 0

    def display(self):
        self.setText(self.sec2time(int(self.elapsed())))
        
    def reset(self):
        self.done()
        self.display()
        
    def start(self):
        self.clock.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.display)
        self.timer.timeout.connect(lambda: self.tic.emit(self.elapsed()))
        self.timer.start(100)
        self.valid = True
    
    def done(self):
        self.valid = False
        self.timer.stop()
                
    @staticmethod
    def sec2time(sec):
        f    = round( 10*(sec-int(sec)) )
        m, s = divmod(sec, 60)
        h, m = divmod(m  , 60)
        if h == 0:
            return      "%02d:%02d%s" % (   m, s, '.%d'%f if f else '' )        
        else:
            return "%02d:%02d:%02d%s" % (h, m, s, '.%d'%f if f else '' )

