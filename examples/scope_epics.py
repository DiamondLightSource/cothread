#!/usr/bin/env python3

'''Form Example with Monitor'''

import os, sys

import require
from cothread.catools import *
from cothread import *
from numpy import *
from PyQt4 import Qwt5, QtGui, QtCore, uic

iqt()

# Qt designer form class (widget is actually QtGui.QWidget)
scope_ui_file = os.path.join(os.path.dirname(__file__), 'scope.ui')
Ui_Scope, widget = uic.loadUiType(scope_ui_file)


# subclass form to implement buttons
class MyScope(widget, Ui_Scope):
    '''application class'''
    def __init__(self):
        widget.__init__(self)
        self.setupUi(self)

        self.channel.setText('SR21C-DI-EBPM-01:FR:WFX')
        self.monitor = None
        # make any contents fill the empty frame
        grid = QtGui.QGridLayout(self.axes)
        self.axes.setLayout(grid)
        self.makeplot()

    def bConnect_clicked(self):
        name = str(self.channel.text())
        print('Connect Clicked', name)
        # disconnect old channel if any
        if self.monitor:
            self.monitor.close()
        # connect new channel
        self.monitor = camonitor(name, self.on_event)
        QtGui.QMessageBox.warning(self, "I'm a warning", "Warning text")

    def on_event(self, value):
        '''camonitor callback'''
        if value.ok:
            x = arange(value.shape[0])
            self.c.setData(x, value)

    def makeplot(self):
        '''set up plotting'''
        # draw a plot in the frame
        p = Qwt5.QwtPlot(self.axes)
        c = Qwt5.QwtPlotCurve('FR:WFX')
        c.attach(p)
        c.setPen(QtGui.QPen(QtCore.Qt.blue))

        # === Plot Customization ===
        # set background to black
        p.setCanvasBackground(QtCore.Qt.black)
        # stop flickering border
        p.canvas().setFocusIndicator(Qwt5.QwtPlotCanvas.NoFocusIndicator)
        # set zoom colour
#         for z in p.zoomers:
#             z.setRubberBandPen(QtGui.QPen(QtCore.Qt.white))
        # set fixed scale
        p.setAxisScale(Qwt5.QwtPlot.yLeft, -1e7, 1e7)
        p.setAxisScale(Qwt5.QwtPlot.xBottom, 0, 2500)
        # automatically redraw when data changes
        p.setAutoReplot(True)
        # reset plot zoom (the default is 1000 x 1000)
#         for z in p.zoomers:
#             z.setZoomBase()

        self.p = p
        self.c = c
        self.axes.layout().addWidget(self.p)

# create and show form
s = MyScope()
s.show()

WaitForQuit()
