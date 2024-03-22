import numpy as np
from scipy import signal
import pyqtgraph as pg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QMessageBox, QApplication, QVBoxLayout, QWidget
import sys
import task6UI
import classes
from classes import Z_plane

class MainApp(QtWidgets.QMainWindow, task6UI.Ui_MainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        self.setupUi(self)

        self.z_plane = Z_plane(self.widget_unit_circle)
        self.draw_unit_circle()

        self.signalViewBox = self.plotWidget_filterred_signal.getViewBox()
        self.signalViewBox_2 = self.plotWidget_real_time_signal.getViewBox()
        self.signalViewBox.setXLink(self.signalViewBox_2)
        self.signalViewBox.setXRange(0, 0.01)

        self.axisStep = 0

        self.signalLength = 100000
        self.time = np.linspace(0, 10, self.signalLength)

        # -------------------------test signal 1------------------------
        self.signal = np.random.randn(self.signalLength)
        # apply Moving Average Filter to smooth out the signal
        windowSize = 100
        self.signal = np.convolve(self.signal, np.ones(windowSize), 'same') / windowSize
        
        # -------------------------test signal 2------------------------
        # self.signal = np.sin(2 * self.time)
        # noiseLevel = 0.06
        # # Generate high frequency noise
        # highFreqNoise = np.random.normal(0, noiseLevel, len(self.signal))
        # self.signal += highFreqNoise


        self.filteredSignal = np.zeros_like(self.signal)
        # self.filteredSignal = np.array([])
        # Initialize poles and zeros
        self.poles = np.array([])
        self.zeros = np.array([])
        self.b = np.array([])
        self.a = np.array([])

        self.timerInterval = 20  # Default timer interval (milliseconds)
        self.timer = QTimer()
        self.timer.setInterval(self.timerInterval)
        self.timer.timeout.connect(self.signalFilteringProcess)
        self.currentPoint = 0
        self.isProcessing = False
        self.toolButton_zeros.clicked.connect(self.select_element_type)
        self.toolButton_poles.clicked.connect(self.select_element_type)
        self.pushButton_clear_z_p.clicked.connect(lambda: self.z_plane.clear_elements(self.z_plane.element_type))
        self.pushButton_clear_all_z_p.clicked.connect(self.z_plane.clear_all)

        self.checkBox_conjegates.stateChanged.connect(self.z_plane.update_conjugates)

        self.z_plane.elementAdded.connect(self.get_added_zeroes_poles)

        self.allPassZeroes = np.array([])
        self.allPassPoles = np.array([])

        self.scrollArea.doubleClicked.connect(lambda work = "addItem": self.updateAllPassFilterItemsList(work))
        self.pushButton_clear_all_pass_filters.clicked.connect(lambda _,work = "clear": self.updateAllPassFilterItemsList(work))
        self.pushButton_save_customized_filter.clicked.connect(lambda _,work = "addCustomizedItem": self.updateAllPassFilterItemsList(work))
        self.listWidget.itemSelectionChanged.connect(self.constructAllPassFilter)

        self.horizontalSlider_filtration_speed.valueChanged.connect(self.adjustFilterationSpeed)
        self.toolButton_filtration_start_stop.clicked.connect(self.handleFiltrationProcessState)
        self.plotWidget_mouse_movement.startFiltration.connect(self.handleArbitarySignal)

    def select_element_type(self):
        if self.sender() == self.toolButton_zeros:
            self.z_plane.set_element_type('zero')
            self.toolButton_zeros.setDown(True)
            self.toolButton_poles.setDown(False)
        else:
            self.z_plane.set_element_type('pole')
            self.toolButton_poles.setDown(True)
            self.toolButton_zeros.setDown(False)

    def draw_unit_circle(self):
        self.z_plane.draw_unit_circle()

    def get_added_zeroes_poles(self, plottedZeroesPolesCoord):
        self.poles = np.array([])
        self.zeros = np.array([])

        for zero in plottedZeroesPolesCoord["zero"]:
            self.zeros = np.append(self.zeros, complex(zero[0]+zero[1]*1j))
        for pole in plottedZeroesPolesCoord["pole"]:
            self.poles = np.append(self.poles, complex(pole[0]+pole[1]*1j))
        self.plot_frequency_response()

    def plot_frequency_response(self):
        if len(self.allPassZeroes) != 0:
            self.zeros = np.append(self.zeros, self.allPassZeroes)
        if len(self.allPassPoles) != 0:
            self.poles = np.append(self.poles, self.allPassPoles)

        self.b = np.array([])
        self.a = np.array([])
        # self.filteredSignal = np.zeros_like(self.signal)
        # self.plotWidget_real_time_signal.clear()
        # self.plotWidget_filterred_signal.clear()
        if self.isProcessing:
            self.handleFiltrationProcessState()

        # calculate numerator and denominator
        if len(self.zeros) > 0:
            self.b = np.poly(self.zeros)  # Coefficients of the numerator of the filter transfer function
        if len(self.poles) > 0:
            self.a = np.poly(self.poles)  # Coefficients of the denominator of the filter transfer function

        print(f"a type {type(self.a)}")
        print(f"b type {type(self.b)}")

        # Compute frequency response
        w, h = signal.freqz_zpk(self.zeros, self.poles, 1)
        self.plotWidget_mag.clear()
        self.plotWidget_mag.plot(w, np.abs(h), pen=pg.mkPen('k', width=2))
        self.plotWidget_mag.setLimits(xMin=min(w), xMax=max(w), yMin=min(np.abs(h)), yMax=max(np.abs(h)))
        self.plotWidget_phase.clear()
        self.plotWidget_phase.plot(w, np.unwrap(np.angle(h)), pen=pg.mkPen('k', width=2))
        self.plotWidget_phase.setLimits(xMin=min(w), xMax=max(w), yMin=min(np.unwrap(np.angle(h))), yMax=max(np.unwrap(np.angle(h))))
        self.plotWidget_filterred_phase.clear()
        self.plotWidget_filterred_phase.plot(w, np.unwrap(np.angle(h)), pen=pg.mkPen('k', width=2))
        self.plotWidget_filterred_phase.setLimits(xMin=min(w), xMax=max(w), yMin=min(np.unwrap(np.angle(h))), yMax=max(np.unwrap(np.angle(h))))

    def updateAllPassFilterItemsList(self, work):
        if work == "clear":
            self.listWidget.clear()
            classes.all_pass_filters_list.clear()
        if work == "addCustomizedItem":
            item = f"{self.lineEdit_real.text()}+{self.lineEdit_imaginary.text()}j"
            classes.all_pass_filters_list.append(item)
            self.lineEdit_real.clear()
            self.lineEdit_imaginary.clear()
            work = "addItem"
        # item added from the library
        if work == "addItem":
            self.listWidget.addItem(classes.all_pass_filters_list[-1])
            lastItem = self.listWidget.item(self.listWidget.count() - 1)
            # selected by default
            lastItem.setSelected(True)
        self.constructAllPassFilter()

    def constructAllPassFilter(self):
        self.zeros = np.setdiff1d(self.zeros, self.allPassZeroes)
        self.poles = np.setdiff1d(self.poles, self.allPassPoles)
        self.allPassZeroes = np.array([])
        self.allPassPoles = np.array([])

        if self.listWidget.count() != 0:
            # get a list of the selected items only
            selectedItems = self.listWidget.selectedItems()
            a_values = np.array([])
            for item in selectedItems:
                # exclude "a=" from items text
                a_values = np.append(a_values, complex(item.text()[2:]))

            # poles = a
            self.allPassPoles = a_values
            # zeroes = 1 / a*
            self.allPassZeroes = 1 / (np.conjugate(self.allPassPoles))

            w, allPassResponse = signal.freqz_zpk(self.allPassZeroes, self.allPassPoles, 1)
            frequencies = w/(2 * np.pi)
            allPassPhaseResponse = np.unwrap(np.angle(allPassResponse))

            self.plotWidget_all_pass_filter.clear()
            self.plotWidget_all_pass_filter.plot(frequencies, allPassPhaseResponse, pen=pg.mkPen('b', width=2))
            self.plotWidget_all_pass_filter.setLimits(xMin=min(frequencies), xMax=max(frequencies), yMin=min(allPassPhaseResponse), yMax=max(allPassPhaseResponse))

            self.plot_frequency_response()

    def signalFilteringProcess(self):
        if self.currentPoint < self.signalLength or self.currentPoint < len(classes.arbitarySignal):
            print("intered filtration")
            # apply the difference equation on the current point
            self.filteredSignal[self.currentPoint] = self.applyFiltering()
            print(f"filter output{self.filteredSignal[self.currentPoint]}")
            # self.filteredSignal = np.append(self.filteredSignal, self.applyFiltering())

            # Update signal graph
            self.updateSignalGraph()

            # Update filtered signal graph
            self.updateFilteredFignalGraph()

            self.animateAxis()

            self.currentPoint += 1

    def animateAxis(self):
        if self.axisStep < max(self.time) and self.time[self.currentPoint] >= 0.01:
            # self.signalViewBox.setXRange(self.axisStep, 0.05 + self.axisStep)
            self.signalViewBox.setXRange(self.axisStep, 0.02 + self.axisStep)
            self.axisStep += 0.0001

    def adjustFilterationSpeed(self, sliderValue):
        if classes.isArbitarySignal:
            self.timer.setInterval(int(1000/classes.speed))
        else:
            self.timer.setInterval(int(1000/sliderValue))

    def applyFiltering(self):
        if classes.isArbitarySignal:
            signal = classes.arbitarySignal / 5
        else:
            signal = self.signal
        print(f"signal shape {signal.shape} annddd {signal}")
        print(f"filteredSignal shape{self.filteredSignal.shape} anddd {self.filteredSignal}")
        return sum([self.b[k] * signal[self.currentPoint - k] if self.currentPoint - k >= 0 else 0 for k in range(len(self.b))]) - sum([self.a[k]*self.filteredSignal[self.currentPoint - k] if self.currentPoint - k >= 0 else 0 for k in range(1, len(self.a))])

    def updateSignalGraph(self):
        if classes.isArbitarySignal:
            signal = classes.arbitarySignal / 5
        else:
            signal = self.signal
        # Plot original signal up to the current point
        self.plotWidget_real_time_signal.clear()
        self.plotWidget_real_time_signal.plot(self.time[:self.currentPoint], signal[:self.currentPoint])
        if self.currentPoint > 0:
            self.plotWidget_real_time_signal.setLimits(xMin=-0.1, xMax=max(self.time[:self.currentPoint]) + 0.1, yMin=min(signal) - 0.1, yMax=max(signal) + 0.1)

    def updateFilteredFignalGraph(self):
        # Plot filtered signal up to the current point
        print(f"type of filtered signal {type(self.filteredSignal)}")
        print(f"filtered {self.filteredSignal}")
        self.plotWidget_filterred_signal.clear()
        self.plotWidget_filterred_signal.plot(self.time[:self.currentPoint], self.filteredSignal[:self.currentPoint])
        if self.currentPoint > 0:
            self.plotWidget_filterred_signal.setLimits(xMin=-0.1, xMax=max(self.time[:self.currentPoint]) + 0.1, yMin=min(self.filteredSignal) - 0.1, yMax=max(self.filteredSignal) + 0.1)

    def handleFiltrationProcessState(self):
        if self.isProcessing:
            self.isProcessing = False
            self.timer.stop()
        else:
            print(f"started//////////////////////////////{classes.isArbitarySignal}")
            if len(self.poles) == 0 and len(self.zeros) == 0:
                pass
            else:
                self.isProcessing = True
                # if classes.isArbitarySignal:
                #     self.timer.setInterval(int(1000/classes.speed))
                # else:
                #     self.timer.setInterval(int(1000/(self.horizontalSlider_filtration_speed.value())))
                self.timer.setInterval(15)
                self.timer.start()

    def handleArbitarySignal(self):
        print(f"started//////////////////////////////***************{classes.isArbitarySignal}")
        # self.filteredSignal = np.zeros_like(self.signal)
        # self.plotWidget_filterred_signal.clear()
        # self.plotWidget_real_time_signal.clear()
        # self.currentPoint = 0
        self.handleFiltrationProcessState()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())