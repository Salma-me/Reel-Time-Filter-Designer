from PyQt5.QtWidgets import QScrollArea, QLabel
from PyQt5.QtCore import pyqtSignal, QObject
import numpy as np
import time
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QPointF, QPoint, QLineF, QObject, QTimer
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtWidgets import QFileDialog, QWidget, QGraphicsView, QGraphicsScene
# from plotwidget import PlotWidget
from matplotlib import pyplot as plt
# from matplotlib_inline.backend_inline import FigureCanvas
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class Z_plane(QWidget):
    elementAdded = pyqtSignal(dict)
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.element_type = None
        self.is_pair = False
        self.is_close = False
        self.dragging = None  # Tuple of the element being dragged (element object, element index in lists)
        self.current_time = None
        self.last_click_time = None
        self.time_diff = 0
        # Define a tolerance distance (within which a click will be considered as being on a pole or zero)
        self.deleting_tolerance = 0.1
        self.conj_coords = {'zero': [], 'pole': []}
        self.conj_elements = {'zero': [], 'pole': []}
        # Initialize zeros and poles, lists of coord tuples(r, i)
        self.plotted_coords = {'zero': [], 'pole': []}
        # Dictionary of lists of elements plotted
        self.plotted_elements = {'zero': [], 'pole': []}
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(self.canvas)
        self.draw_unit_circle()
        # Connect the events
        self.fig.canvas.mpl_connect('button_press_event', self.update_times)
        self.fig.canvas.mpl_connect('button_press_event', self.start_drag_elements)
        self.fig.canvas.mpl_connect('button_release_event', self.end_drag_elements)
        self.fig.canvas.mpl_connect('motion_notify_event', self.on_dragging_elements)
        self.fig.canvas.mpl_connect('button_press_event', self.is_deleting_elements)
        self.fig.canvas.mpl_connect('button_press_event', self.add_elements)

    # print('on_mouse_click')
    # print(f"conj_coordinates= {self.conj_coordinates}")
    # print(f"conj_elements= {self.conj_elements}")
    # print(f"plotted_coordinates= {self.plotted_coordinates}")
    # print(f"plotted_elements= {self.plotted_elements}")
    # print(f"element_type= {self.element_type}")
    # print(f"is_pair= {self.is_pair}")

    def set_element_type(self, element_type):
        self.element_type = element_type

    def draw_unit_circle(self):
        # Plot the circle
        circle = plt.Circle((0, 0), 1, edgecolor=(79 / 255, 90 / 255, 112 / 255),
                            facecolor='none', linewidth=1.3)
        # Add the circle to the Axes
        self.ax.add_artist(circle)
        # Set the limits
        self.ax.set_xlim(-1.5, 1.5)
        self.ax.set_ylim(-1.5, 1.5)
        # Set the ticks every 0.5 step
        self.ax.set_xticks(np.arange(-1.5, 1.5, 0.5))
        self.ax.set_yticks(np.arange(-1.5, 1.5, 0.5))
        # Add labels to the axes
        self.ax.set_xlabel('Real', size=10, x=1.12, labelpad=-20)
        self.ax.set_ylabel('Imaginary', size=10, y=1.05, labelpad=-21, rotation=0)
        # Set the aspect of the plot to be equal
        self.ax.set_aspect('equal')
        # Add a grid
        self.ax.grid(True)

    def add_elements(self, event):
        # print('---------------add_elements----------------')
        # print(f"is_close= {self.is_close}")
        if self.is_close:
            # print('---------------add_elements (if True)----------------')
            # print(f"conj_coords= {self.conj_coords}")
            # print(f"conj_elements= {self.conj_elements}")
            # print(f"plotted_coords= {self.plotted_coords}")
            # print(f"plotted_elements= {self.plotted_elements}")
            return
        else:
            # Check which button is checked and add a zero or pole at the clicked position
            if self.element_type == 'zero':
                element = self.ax.scatter(event.xdata, event.ydata, s=60, edgecolors='blue', facecolors='none')
                self.add_conjugates(event, 'z')
                self.plotted_elements['zero'].append(element)
                self.plotted_coords['zero'].append((event.xdata, event.ydata))
            elif self.element_type == 'pole':
                element, = self.ax.plot(event.xdata, event.ydata, 'x', color='red')
                self.add_conjugates(event, 'p')
                self.plotted_elements['pole'].append(element)
                self.plotted_coords['pole'].append((event.xdata, event.ydata))
            else:
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Information)
                msg.setText("Please select either zeros 'o' or poles 'x' to add.")
                msg.setWindowTitle("Information")
                msg.exec_()
            self.fig.canvas.draw()

            # emit signal to update filter frequency response
            self.elementAdded.emit(self.plotted_coords)
            # print('---------------add_elements (if False)----------------')
            # print(f"conj_coords= {self.conj_coords}")
            # print(f"conj_elements= {self.conj_elements}")
            # print(f"plotted_coords= {self.plotted_coords}")
            # print(f"plotted_elements= {self.plotted_elements}")

    def update_conjugates(self, state):
        if state == QtCore.Qt.Checked:
            self.is_pair = True
        else:
            self.is_pair = False

        self.plot_pairs()
        self.fig.canvas.draw()

    def add_conjugates(self, event, element_type):
        if element_type == 'z':
            element = self.ax.scatter(event.xdata, - event.ydata, s=60, edgecolors='blue', facecolors='none', visible=False)
            self.conj_elements['zero'].append(element)
            self.conj_coords['zero'].append((event.xdata, - event.ydata))
        else:
            element, = self.ax.plot(event.xdata, - event.ydata, 'x', color='red')
            self.conj_elements['pole'].append(element)
            self.conj_coords['pole'].append((event.xdata, - event.ydata))

        self.plot_pairs()

    def plot_pairs(self):
        if self.is_pair:
            for element in self.conj_elements['zero']:
                # Make the marker visible
                element.set_visible(True)
            for element in self.conj_elements['pole']:
                element.set_visible(True)
        else:
            for element in self.conj_elements['zero']:
                # Make the marker visible
                element.set_visible(False)
            for element in self.conj_elements['pole']:
                element.set_visible(False)
            # for coordinates in self.plotted_coordinates['zero']:
            #     self.ax.scatter(coordinates[0], -coordinates[1], s=60, edgecolors='blue', facecolors='none')
            # for coordinates in self.plotted_coordinates['pole']:
            #     self.ax.plot(coordinates[0], -coordinates[1], 'x', color='red')

    def update_times(self, event):
        print('-----------update_times (bfr)-----------------')
        print(f"last time= {self.last_click_time}, current time= {self.current_time}")
        print(f"dragging: {self.dragging}")
        if self.current_time is not None:
            self.last_click_time = self.current_time
            self.current_time = time.time()
        else:
            self.current_time = time.time()
            self.last_click_time = self.current_time
        print('-----------update_times (ftr)-----------------')
        print(f"last time= {self.last_click_time}, current time= {self.current_time}")

        self.time_diff = self.current_time - self.last_click_time

    def is_deleting_elements(self, event):
        print('---------------is_deleting_elements (bfr)----------------')
        # print(f"is_close= {self.is_close}")
        # print(f"conj_coords= {self.conj_coords}")
        # print(f"conj_elements= {self.conj_elements}")
        # print(f"plotted_coords= {self.plotted_coords}")
        # print(f"plotted_elements= {self.plotted_elements}")
        if self.dragging is not None:
            print('---------------is_deleting_elements (dragging->return)----------------')
            return
        # if self.last_click_time is not None and self.time_diff < 3:
        #     return
        if not (self.plotted_elements['zero'] or self.plotted_elements['pole']):
            self.is_close = False
        # Check each plotted element
        for element_type in ['zero', 'pole']:
            for i, (element, coords, conjugate_element, conjugate_coords) in (
                    enumerate(zip(self.plotted_elements[element_type], self.plotted_coords[element_type],
                                  self.conj_elements[element_type], self.conj_coords[element_type]))):
                xdata, ydata = coords
                conj_xdata, conj_ydata = conjugate_coords
                distance_to_element = ((xdata - event.xdata) ** 2 + (ydata - event.ydata) ** 2) ** 0.5
                distance_to_conj = ((conj_xdata - event.xdata) ** 2 + (conj_ydata - event.ydata) ** 2) ** 0.5
                if distance_to_element < self.deleting_tolerance:
                    print('---------------is_deleting_elements (close to element)----------------')
                    self.is_close = True
                    # The click is close to this element, so remove it
                    element.remove()
                    self.plotted_elements[element_type].remove(element)
                    self.plotted_coords[element_type].remove(coords)
                    # Get the corresponding conjugates to remove them
                    conjugate_element = self.conj_elements[element_type][i]
                    conjugate_coords = self.conj_coords[element_type][i]
                    conjugate_element.remove()
                    self.conj_elements[element_type].remove(conjugate_element)
                    self.conj_coords[element_type].remove(conjugate_coords)
                    self.fig.canvas.draw()
                elif self.is_pair and (distance_to_conj < self.deleting_tolerance):
                    print('---------------is_deleting_elements (close to conj)----------------')
                    self.is_close = True
                    # The click is close to this element, so remove it
                    element.remove()
                    self.plotted_elements[element_type].remove(element)
                    self.plotted_coords[element_type].remove(coords)
                    # Get the corresponding conjugates to remove them
                    conjugate_element = self.conj_elements[element_type][i]
                    conjugate_coords = self.conj_coords[element_type][i]
                    conjugate_element.remove()
                    self.conj_elements[element_type].remove(conjugate_element)
                    self.conj_coords[element_type].remove(conjugate_coords)
                    self.fig.canvas.draw()
                else:
                    self.is_close = False
        # print('---------------is_deleting_elements (ftr)----------------')
        # print(f"is_close= {self.is_close}")
        # print(f"conj_coords= {self.conj_coords}")
        # print(f"conj_elements= {self.conj_elements}")
        # print(f"plotted_coords= {self.plotted_coords}")
        # print(f"plotted_elements= {self.plotted_elements}")

    def start_drag_elements(self, event):
        # print('-----------start_drag_elements (bfr)-----------------')
        # print(f"last time= {self.last_click_time}, current time= {self.current_time}")
        # print(f"dragging: {self.dragging}")
        # if self.current_time is not None:
        #     self.last_click_time = self.current_time
        #     self.current_time = time.time()
        # else:
        #     self.current_time = time.time()
        #     self.last_click_time = self.current_time
        #
        # # self.last_click_time = self.current_time
        # print('-----------start_drag_elements (ftr)-----------------')
        # print(f"last time= {self.last_click_time}, current time= {self.current_time}")

        # Check if a plotted element or conjugate was double-clicked
        if self.last_click_time is not None and self.time_diff < 3:
            for element_type in ['zero', 'pole']:
                print(f"length(plotted coords[{element_type}]): {len(self.plotted_coords[element_type])}")
                print(f"length(plotted elements[{element_type}]): {len(self.plotted_elements[element_type])}")
                for i, coord in enumerate(self.plotted_coords[element_type]):
                    if abs(event.xdata - coord[0]) < self.deleting_tolerance and abs(
                            event.ydata - coord[1]) < self.deleting_tolerance:
                        self.dragging = (element_type, i)
                        print(f"dragging: {element_type}, {i}")
                        return False
                if self.is_pair:
                    for i, coord in enumerate(self.conj_coords[element_type]):  # Check the conjugates
                        if abs(event.xdata - coord[0]) < self.deleting_tolerance and abs(
                                event.ydata - coord[1]) < self.deleting_tolerance:
                            self.dragging = (element_type, i)
                            print(f"dragging: {element_type}, {i}")
                            return False

    def end_drag_elements(self, event):
        print('-----------end_drag_elements (bfr)-----------------')
        print(f"dragging: {self.dragging}")
        # Stop dragging
        self.dragging = None
        print('-----------end_drag_elements (ftr)-----------------')
        print(f"dragging: {self.dragging}")

    def on_dragging_elements(self, event):
        print('-----------on_dragging_elements-----------------')
        # If dragging, update the position of the dragged element and its conjugate
        if self.dragging is not None:
            print(f"dragging: {self.dragging[0]}, {self.dragging[1]}")
            element_type, i = self.dragging
            print(f"length(plotted coords[{element_type}]): {len(self.plotted_coords[element_type])}")
            print(f"length(plotted elements[{element_type}]): {len(self.plotted_elements[element_type])}")
            self.plotted_coords[element_type][i] = (event.xdata, event.ydata)
            self.conj_coords[element_type][i] = (event.xdata, -event.ydata)  # Update the conjugate as well
            # Redraw the plot
            self.fig.canvas.draw()
        else:
            print(f"dragging None!: {self.dragging}")

    def clear_elements(self, element_to_delete):
        if element_to_delete == 'zero':
            # Remove zero elements from the plot
            for zero in self.plotted_elements['zero']:
                zero.remove()
            self.plotted_elements['zero'].clear()
            self.plotted_coords['zero'].clear()
            # Remove zero conjugates from the plot
            for z_conj in self.conj_elements['zero']:
                z_conj.remove()
            self.conj_elements['zero'].clear()
            self.conj_coords['zero'].clear()
        elif element_to_delete == 'pole':
            # Remove pole elements from the plot
            for pole in self.plotted_elements['pole']:
                pole.remove()
            self.plotted_elements['pole'].clear()
            self.plotted_coords['pole'].clear()
            # Remove pole conjugates from the plot
            for p_conj in self.conj_elements['pole']:
                p_conj.remove()
            self.conj_elements['pole'].clear()
            self.conj_coords['pole'].clear()
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("Please select either 'o' or 'x' before deleting elements.")
            msg.setWindowTitle("Information")
            msg.exec_()
        self.draw_unit_circle()
        self.fig.canvas.draw()
        self.elementAdded.emit(self.plotted_coords)

    def clear_all(self):
        for element_type in ['zero', 'pole']:
            self.clear_elements(element_type)
        self.is_close = False

global arbitarySignal
arbitarySignal = np.array([])
global isArbitarySignal
isArbitarySignal = False
global speed
speed = 0

class MousePad(QGraphicsView):
    startFiltration = pyqtSignal()

    def __init__(self, parent=None):
        super(MousePad, self).__init__(parent)
        self.setMouseTracking(False)
        self.last_pos = None
        self.last_time = 0
        self.amplitudes = []
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.getArbitarySignal)
        self.pointIndex = 0
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
    
    def getArbitarySignal(self):
        global arbitarySignal
        # print(f"arbitarySignal {arbitarySignal}")
        if len(self.amplitudes) > 0 and len(self.amplitudes) > self.pointIndex:
            arbitarySignal = np.append(arbitarySignal, self.amplitudes[self.pointIndex].y() * -1)
            self.pointIndex += 1

    def mousePressEvent(self, event):
        global arbitarySignal
        global isArbitarySignal
        if event.button() == Qt.LeftButton:
            self.setMouseTracking(True)
            self.last_pos = event.pos()
            self.amplitudes.append(event.pos())  # Start a new path
            self.timer.start()
            isArbitarySignal = True
            self.startFiltration.emit()
            print('---------(1) mousePressEvent-----------')
            # print(f"mouseTrack: {self.hasMouseTracking}")
            print(f"path length: {len(self.amplitudes)}")

    def mouseReleaseEvent(self, event):
        global isArbitarySignal
        if event.button() == Qt.LeftButton:
            self.setMouseTracking(False)
            self.last_pos = None
            self.last_time = 0
            self.pointIndex = 0
            self.scene.clear()  # Clear the scene
            isArbitarySignal = False
            self.timer.stop()
            # again to stop filtration
            self.startFiltration.emit()
            print('---------(2) mouseReleaseEvent-----------')
            # print(f"event.button(): {event.button()}")
            # print(f"mouseTrack: {self.hasMouseTracking}")
            print(f"path length: {len(self.amplitudes)}")

    def mouseMoveEvent(self, event):
        global speed
        # print('---------(3) mouseMoveEvent-----------')
        # print(f"mouseTrack: {self.hasMouseTracking}")
        if self.hasMouseTracking():
            # print('---------(3) mouseMoveEvent-----------')
            # print(f"mouseTrack: {self.hasMouseTracking}")
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            # print(f"dt= {dt}")

            dx = event.pos().x() - self.last_pos.x()
            dy = event.pos().y() - self.last_pos.y()
            distance = (dx ** 2 + dy ** 2) ** 0.5
            speed = distance / dt
            # print(f"dx= {dx}")
            # print(f"dy= {dy}")
            # print(f"distance= {distance}")
            # print(f"speed= {speed}")
            base = 2  # Choose a base for the logarithm
            frequency = base ** (speed / 1000)  # Calculate the frequency in Hz
            # print(f"frequency= {frequency}")
            
            # self.timer.setInterval(int(1000/speed))
            self.amplitudes.append(event.pos())
            # print(f"path length: {len(self.amplitudes)}")
            line = QLineF(QPointF(self.last_pos), QPointF(event.pos()))
            self.scene.addLine(line, QPen(Qt.white, 2))
            self.last_pos = event.pos()
            self.update()  # Trigger a repaint

    def paintEvent(self, event):
        super().paintEvent(event)  # Call the superclass paintEvent to draw the plot
        painter = QPainter(self)
        pen = QPen(Qt.white, 2)  # Use a white pen
        painter.setPen(pen)

        if self.amplitudes:
            # Draw the path
            for i in range(len(self.amplitudes) - 1):
                point1 = self.amplitudes[i]
                point2 = self.amplitudes[i + 1]
                # Unpack the points from the tuples
                x1, y1 = point1.x(), point1.y()
                x2, y2 = point2.x(), point2.y()
                painter.drawLine(x1, y1, x2, y2)


global all_pass_filters_list
all_pass_filters_list = []

class CustomScrollArea(QScrollArea):
    doubleClicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.currentItem = None

    def mouseDoubleClickEvent(self, event):
        widget = self.childAt(event.pos())
        if isinstance(widget, QLabel):
            self.currentItem = widget
            print(f"Double click: {self.currentItem.text()}")
            all_pass_filters_list.append(self.currentItem.text())
            self.doubleClicked.emit()
