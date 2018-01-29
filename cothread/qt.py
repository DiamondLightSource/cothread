import sys


qts = ['PyQt5', 'PyQt4']  ## ordered by preference

# check if PyQt alredy imported
QT_LIB = None
for lib in qts:
    if lib in sys.modules:
        QT_LIB = lib
        break

# if not imported let's try to import any
if QT_LIB is None:
    for lib in qts:
        try:
            __import__(lib)
            QT_LIB = lib
            break
        except ImportError:
            pass
if QT_LIB is None:
    ImportError("PyQt not found")

# now some PyQt is imported

if QT_LIB == 'PyQt5':
    from PyQt5 import QtCore, QtWidgets


elif QT_LIB == 'PyQt4':
    from PyQt4 import QtCore, QtGui
    QtWidgets = QtGui
