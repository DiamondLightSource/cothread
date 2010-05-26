#!/usr/bin/env dls-python

'''Form Example with Monitor'''

import subprocess
import os

# version control
import require
from cothread.catools import *
from cothread import *
iqt(use_timer = True)

from numpy import *
from qwt.qplt import Plot, Curve, Bottom, QwtPlot, \
     QwtPlotCanvas, Qt, Pen, QwtDoubleRect

from qt import *


def load(filename, cls):
    '''loads python class from ui file'''
    pyuic = subprocess.Popen(
        ['pyuic2.4', filename],
        stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    (stdout, stderr) = pyuic.communicate()
    if pyuic.returncode != 0:
        raise Exception(stderr)

    ns = {}
    exec stdout in ns
    globals()[cls] = ns[cls]



# Qt designer form class
scope_ui_file = os.path.join(os.path.dirname(__file__), 'scope.ui')
load(scope_ui_file, 'Scope')

# subclass form to implement buttons
class MyScope(Scope):
    '''application class'''
    def __init__(self):
        Scope.__init__(self)
        self.channel.setText('SR21C-DI-EBPM-01:FR:WFX')
        self.monitor = None
        # make any contents fill the empty frame
        grid = QVBoxLayout(self.axes)
        grid.setAutoAdd(True)
        self.makeplot()

    def bConnect_clicked(self):
        name = str(self.channel.text())
        print 'Connect Clicked', name
        # disconnect old channel if any
        if self.monitor:
            self.monitor.close()
        # connect new channel
        self.monitor = camonitor(name, self.on_event)

    def on_event(self, value):
        '''camonitor callback'''
        if value.ok:
            x = arange(value.shape[0])
            self.p.setCurveData(1, x, value)

    def makeplot(self):
        '''set up plotting'''
        # draw a plot in the frame
        p = Plot(self.axes, Curve([], [], 'FR:WFX', Pen(Qt.blue)))
        # === Plot Customization ===
        # turn off grid
        p.enableGridX(False)
        p.enableGridY(False)
        # set background to black
        p.setCanvasBackground(Qt.black)
        # stop flickering border
        p.canvas().setFocusIndicator(QwtPlotCanvas.NoFocusIndicator)
        # move legend to bottom
        p.setLegendPosition(QwtPlot.Bottom)
        # set zoom colour
        for z in p.zoomers:
            z.setRubberBandPen(QPen(Qt.white))
        # set fixed scale
        p.setAxisScale(QwtPlot.yLeft, -1e7, 1e7)
        p.setAxisScale(QwtPlot.xBottom, 0, 2500)
        # automatically redraw when data changes
        p.setAutoReplot(True)
        # reset plot zoom (the default is 1000 x 1000)
        for z in p.zoomers:
            z.setZoomBase()
        # === End Plot Customization ===
        self.p = p

# create and show form
s = MyScope()
s.show()

WaitForQuit()
