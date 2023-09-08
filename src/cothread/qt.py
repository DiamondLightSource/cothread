import sys


qts = ['PyQt6', 'PyQt5', 'PyQt4']  ## ordered by preference

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
    raise ImportError("PyQt not found")

assert QT_LIB in qts, "PyQt version not supported"

# now some PyQt is imported

exec_name = ''

if QT_LIB == 'PyQt6':
    from PyQt6 import QtCore, QtWidgets
    exec_name = 'exec'


elif QT_LIB == 'PyQt5':
    from PyQt5 import QtCore, QtWidgets
    exec_name = 'exec_'


elif QT_LIB == 'PyQt4':
    from PyQt4 import QtCore, QtGui
    QtWidgets = QtGui
    exec_name = 'exec_'
