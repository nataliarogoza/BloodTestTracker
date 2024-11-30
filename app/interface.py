import os
from database import DatabaseManager 
from custom import CustomCalendarWidget
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu, QComboBox)
from PyQt6.QtCore import (QDate, Qt, QTimer)
from PyQt6.QtGui import (QPalette, QFont, QPixmap, QBrush, QImage)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib import (pyplot as plt, font_manager)
import pandas as pd
import numpy as np

class LabResultsApp(QWidget): 
    """ GUI application class enables: viewing, managing, and analyzing laboratory results.
        It is built on top of PyQt's QWidget and serves as the main interface for the application """

    def __init__(self):
        """ Initialize the LabResultsApp instance """
        super().__init__() # Inheriting from QWidget
        self.current_dir = os.path.dirname(os.path.abspath(__file__)) # Store current directory path
        self.set_insert_mode()
        self.load_data()  
        self.init_ui()
        self.set_default_image()
        self.show_instruction()
        self.set_autorefresh()

    def set_insert_mode(self):
        """ Control insert vs update modes """
        self.editing_id = None # Initially set to insert mode

    def load_data(self):
        """ Load options to choose from, while inserting/updating results """
        test_names_file = os.path.join(self.current_dir, f"resources/textfiles/tests_names.txt")
        units_names_file = os.path.join(self.current_dir, f"resources/textfiles/units_names.txt")
        
        # Import blood test options
        try:
            with open(test_names_file, "r") as file:
                self.test_names_list = sorted([line.strip() for line in file.readlines()])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load test names: {str(e)}")
        
        # Import units options
        try:
            with open(units_names_file, "r") as file:
                self.units_names_list = [line.strip() for line in file.readlines()]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load units names: {str(e)}")

    def set_default_image(self):
        """ Display the image when app is being launched """
        image_path = os.path.join(self.current_dir, "images", "axolotl.webp")
        # Load the image into a QPixmap
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print("Error: Unable to load the image")
            return
        
        # Convert QPixmap to QImage, then to NumPy array 
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
        width, height = image.width(), image.height()
        ptr = image.bits()
        ptr.setsize(width * height * 3)
        img_data = np.array(ptr).reshape((height, width, 3))  # 3 values (R,G,B) per one pixel
        
        # Set up the plot
        self.figure.set_facecolor("#dcdadb")
        self.figure.tight_layout()  
        font = self.set_plot_font()  
        ax = self.figure.add_subplot(111)

        # Display the image in the plot
        ax.imshow(img_data)  
        ax.axis("off")  
        ax.set_title("Your blood test history will be plotted here - pick one above to analyze", font=font, fontsize=14)

        # Draw the canvas
        self.canvas.draw()

    def set_plot_font(self):
        """ Upload font from files """
        font_path = os.path.join(self.current_dir, "fonts/Roboto/Roboto-Regular.ttf")
        font = font_manager.FontProperties(fname=font_path)
        return font

    def show_instruction(self):
        """ Display instruction box """
        instruction_file = os.path.join(self.current_dir, f"resources/textfiles/instruction.txt")
        with open(instruction_file, "r") as file:
            text = file.read()
        QMessageBox.information(self, "Instruction", str(text))
          
    def set_autorefresh(self):
        """ Execute refresh_results_table() each 5 seconds """
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_results_table)
        self.timer.start(5000)  # 5000 milliseconds = 5 seconds

    def refresh_results_table(self):
        """ Fetch ALL results from database and display in "Entries History" section's table widget """
        db = DatabaseManager()
        results = db.select_all()
        self.results_table.setRowCount(len(results))
        for row_id, (test_name, result_value, unit, test_date) in enumerate(results):
            self.results_table.setItem(row_id, 0, QTableWidgetItem(test_name))
            self.results_table.setItem(row_id, 1, QTableWidgetItem(str(result_value)))
            self.results_table.setItem(row_id, 2, QTableWidgetItem(unit))
            self.results_table.setItem(row_id, 3, QTableWidgetItem(test_date.strftime("%Y-%m-%d")))

    def set_font(self):
        """ Set widget's to use particular font as a default """
        font = QFont("Roboto Regular", 12)  
        self.setFont(font)

    def set_background(self):
        """ Set background image """
        palette = QPalette()
        pixmap = QPixmap(os.path.join(self.current_dir, "images/background.png"))
        brush = QBrush(pixmap)
        palette = self.palette()
        palette.setBrush(QPalette.ColorRole.Window, brush)
        self.setPalette(palette)
        return palette
    
    def set_geometry(self):
        """ Show app window initially as 80% of screen size """
        screen = QApplication.primaryScreen() # Get screen resolution
        screen_geometry = screen.geometry()  
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        self.resize(int(screen_width * 0.8), int(screen_height * 0.8)) # Resize to 80% of user's screen width/height

    def load_stylesheet(self, file_path):
        """ Load QSS file and return its content """
        with open(file_path, "r") as file:
            return file.read()
    
    def add_or_update_result(self):
        """ Handler for adding new result or updating existing one in the database """
        db = DatabaseManager()
        test_name = self.test_name_input.currentText() # Store the currently selected test name 
        unit = self.unit_input.currentText() # Store the currently selected unit name
        try:
            result_value = float(self.result_value_input.text()) # Store the entered value
            result_date = self.result_date_input.selectedDate().toString("yyyy-MM-dd") # Store the selected date

            # Updating mode
            if self.editing_id is not None: 
                # Update in database
                db.update(self.editing_id, test_name, result_value, unit, result_date)
                QMessageBox.information(self, "Success", "Result updated successfully!")
                # Change the view to enable next entries
                self.editing_id = None
                self.clear_input_fields()
                self.refresh_results_table()
            
            # Adding new data mode
            else: 
                # Insert into database
                db.insert(test_name, result_value, unit, result_date)
                QMessageBox.information(self, "Success", "Result added successfully!")
                # Change the view to enable next entries
                self.clear_input_fields()
                self.refresh_results_table()
            
            # Update list of tests in the right panel that can be analyzed 
            current_selection = self.test_analysis_input.currentText()
            self.test_analysis_input.clear()  # Clear the existing list
            new_test_names = self.get_accessible_values()
            self.test_analysis_input.addItems(new_test_names)
            # Keeping test name picked before for analysis shown (not refreshing)
            if current_selection in new_test_names:
                self.test_analysis_input.setCurrentText(current_selection)

        except ValueError:
            QMessageBox.critical(self, "Input Error", "Please enter a valid number (with decimal point) for result value!")
   
    def get_accessible_values(self, column_name="test_name"):
        """ Fetch all values from chosen column from database table """
        db = DatabaseManager()
        results = db.select_chosen_column(column_name)
        return results

    def show_context_menu(self, pos):
        """ Show context menu for deleting or updating selected row """
        context_menu = QMenu(self)
        context_menu.setStyleSheet("background-color: #2b5eb0")
        delete_action = context_menu.addAction("Delete Result")
        update_action = context_menu.addAction("Change result")
        action = context_menu.exec(self.results_table.mapToGlobal(pos))
        if action == delete_action:
            self.delete_result()
        if action == update_action:
            self.prepare_update_result()

    def delete_result(self):
        """ Delete the selected result from the database """
        db = DatabaseManager()
        selected_row = self.results_table.currentRow()
        if selected_row != -1:  # If a row is selected
            test_name = self.results_table.item(selected_row, 0).text()
            result_value = self.results_table.item(selected_row, 1).text()
            unit = self.results_table.item(selected_row, 2).text()
            test_date = self.results_table.item(selected_row, 3).text()
            reply = QMessageBox.question(self, "Confirm Deletion", 
                f"Are you sure you want to delete the result:\n\nTest: {test_name}\nValue: {result_value} {unit}\nDate: {test_date}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                result_id = db.get_result_id(test_name, result_value, unit, test_date)
                if result_id:
                    db.delete(result_id)  # Delete from database
                    self.results_table.removeRow(selected_row)  # Remove from "Entries History" table view
                    QMessageBox.information(self, "Success", "Result deleted successfully!")
                else:
                    QMessageBox.critical(self, "Error", "Failed to find the result in database.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a result to delete.")

    def prepare_update_result(self):
        """ Load the selected result into input fields to allow updating """
        db = DatabaseManager()
        selected_row = self.results_table.currentRow()
        if selected_row != -1: 
            # Extract the data from the selected row
            test_name = self.results_table.item(selected_row, 0).text()
            result_value = self.results_table.item(selected_row, 1).text()
            unit = self.results_table.item(selected_row, 2).text()
            test_date = self.results_table.item(selected_row, 3).text()
            # Populate fields with selected data for editing
            self.test_name_input.setCurrentText(test_name)
            self.result_value_input.setText(result_value)
            self.unit_input.setCurrentText(unit)
            self.result_date_input.setSelectedDate(QDate.fromString(test_date, "yyyy-MM-dd"))
            # Retrieve and store the result ID for updating (it sets the logic to update mode)
            self.editing_id = db.get_result_id(test_name, result_value, unit, test_date)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a result to update.")
   
    def clear_input_fields(self):
        """ Clear input fields after adding or updating a result """
        # Clearing only result value field - it makes it easier to entry data from the same day, in the same unit
        #self.test_name_input.setCurrentIndex(0)
        #self.unit_input.setCurrentIndex(0)
        #self.result_date_input.setSelectedDate(QDate.currentDate())
        self.result_value_input.clear()
        self.set_insert_mode()

    def refresh_chosen_table(self):
        """ Fetch results from database for SELECTED test and display in "Analysis" section's table widget """
        db = DatabaseManager()
        test_name = self.test_analysis_input.currentText()
        results = db.select_chosen_all(test_name) if test_name else []
        self.chosen_table.setRowCount(len(results))
        for row_id, (result_value, unit, test_date) in enumerate(results):
            self.chosen_table.setItem(row_id, 0, QTableWidgetItem(str(result_value)))
            self.chosen_table.setItem(row_id, 1, QTableWidgetItem(unit))
            self.chosen_table.setItem(row_id, 2, QTableWidgetItem(test_date.strftime("%Y-%m-%d")))
    
    def choose_test(self):
        """ Initialize actions for selecting test in "Analysis" section """
        test_name = self.test_analysis_input.currentText()
        if not test_name:
            self.set_default_image()
            QMessageBox.warning(self, "No Test Selected", "Please select a test to analyze.")
            return
        self.refresh_chosen_table() # Display results for selected test
        self.update_statistics() # Show stats for selected test
        self.plot_data() # Plot history for selected test

    def update_statistics(self):
        """ Retrieve data and display statistics for selected test in "Analysis" section """
        row_count = self.chosen_table.rowCount()
        # If no data is avaiable (when app is launched and no test for analysis is selected)
        if row_count == 0:
            self.min_label.setText("Min: N/A")
            self.max_label.setText("Max: N/A")
            self.avg_label.setText("Avg: N/A")
            self.std_label.setText("Std Dev: N/A")
            return
        
        # Extract test results numerical values (from the first column)
        values = []
        for row in range(row_count):
            item = self.chosen_table.item(row, 0)  
            if item:
                try:
                    values.append(float(item.text()))  # Convert to float
                except ValueError:
                    continue  # Skip invalid entries

        # Compute statistics for selected test 
        if values:
            self.min_label.setText(f"MIN: {np.min(values):.2f}")
            self.max_label.setText(f"MAX: {np.max(values):.2f}")
            self.avg_label.setText(f"AVG: {np.mean(values):.2f} ± {np.std(values):.2f}")
        else:
            self.min_label.setText("MIN: N/A")
            self.max_label.setText("MAX: N/A")
            self.avg_label.setText("AVG: N/A")
        
    def plot_data(self):
        """ Plot and display results in time for selected test in "Analysis" section """
        # Fetch data from the chosen test table into a pandas DataFrame
        selected_test_name = self.test_analysis_input.currentText()
        data = []
        for row in range(self.chosen_table.rowCount()):
            result_value = float(self.chosen_table.item(row, 0).text())
            unit = self.chosen_table.item(row, 1).text()
            test_date = self.chosen_table.item(row, 2).text()
            data.append((result_value, unit, test_date))
        df = pd.DataFrame(data, columns=["Value", "Unit", "Date"])

        # Check if all units are the same (could happen because there's no restriction while entering data)
        unique_units = df["Unit"].unique()
        if len(unique_units) > 1:
            QMessageBox.warning(
                self, 
                "Inconsistent Units", 
                f"Selected test has multiple units: {', '.join(unique_units)}. Cannot plot data.")
            return

        # Convert the Date column to datetime and sort
        df["Date"] = pd.to_datetime(df["Date"])
        df.sort_values("Date", inplace=True)
        
        # Plot
        self.figure.clear() # Clear previous figure to avoid overlapping
        self.figure.set_facecolor("#dcdadb")
        font = self.set_plot_font()
        ax = self.figure.add_subplot(111) 
        ax.plot(df["Date"], df["Value"], marker="$X$", markerfacecolor="#9e2a47", markeredgecolor="#9e2a47", color="#2b5eb0")
        ax.set_title(f"{selected_test_name} Results Over Time", font=font, fontsize=14)
        ax.set_xlabel("Date", font=font, fontsize=14)
        ax.set_ylabel(f"Value ({unique_units[0]})", font=font, fontsize=14)
        ax.grid(True, alpha=0.5)

        # Update the canvas
        self.canvas.draw()  

    def set_canvas(self):
        """ Prepare a blank plotting area for later use """    
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure) # Makes it compatible with PyQt widgets

    def init_ui(self):
        """ Manage the GUI """
        self.set_canvas()
        self.set_font()
        self.setStyleSheet("color: white;")
        self.setPalette(self.set_background())
        self.set_geometry()

        main_layout = QHBoxLayout() # Will be divided in left and right panels
    
        # LEFT PANEL - DATA ENTRY AND DISPLAY
        left_panel = QVBoxLayout()

        # DATA ENTRY
        label_add = QLabel("Add New Result")
        label_add.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_add.setFont(QFont("Roboto Regular", 18, QFont.Weight.Bold))
        label_add.setStyleSheet("background-color: transparent;")
        left_panel.addWidget(label_add)

        data_entry_section = QWidget()
        data_entry_layout = QVBoxLayout()
        data_entry_section.setLayout(data_entry_layout)
        data_entry_section.setObjectName("dataEntrySection")
        data_entry_stylesheet_file = os.path.join(self.current_dir, f"resources/styles/data_entry_section.qss")
        data_entry_section_style = self.load_stylesheet(data_entry_stylesheet_file)
        data_entry_section.setStyleSheet(data_entry_section_style)

        self.test_name_input = QComboBox()
        self.test_name_input.addItems(self.test_names_list)
        self.test_name_input.setFont(QFont("Roboto Regular", 12))
        data_entry_layout.addWidget(self.test_name_input)
        
        self.result_value_input = QLineEdit()
        self.result_value_input.setPlaceholderText("Result Value")
        self.result_value_input.setFont(QFont("Roboto Regular", 12))
        data_entry_layout.addWidget(self.result_value_input)
       
        self.unit_input = QComboBox()
        self.unit_input.addItems(self.units_names_list)
        self.unit_input.setFont(QFont("Roboto Regular", 12))
        data_entry_layout.addWidget(self.unit_input)
   
        self.result_date_input = CustomCalendarWidget()
        data_entry_layout.addWidget(self.result_date_input)

        add_button = QPushButton("Add/Update Result")
        add_button.clicked.connect(self.add_or_update_result) # Triggering method to upload data in the database
        add_button.setStyleSheet("background-color: #35a854; color: white; border-radius: 5px; padding: 10px; font-family: Roboto Regular; font-size: 16px;")  # Styling for button
        data_entry_layout.addWidget(add_button)

        left_panel.addWidget(data_entry_section)
        
        # DATA DISPLAY
        label_results = QLabel("Entries History")
        label_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_results.setFont(QFont("Roboto Regular", 18, QFont.Weight.Bold))
        left_panel.addWidget(label_results)

        self.results_table = QTableWidget()
        results_table_stylesheet_file = os.path.join(self.current_dir, f"resources/styles/results_table.qss")
        results_table_style = self.load_stylesheet(results_table_stylesheet_file)
        self.results_table.setStyleSheet(results_table_style)
        self.results_table.setFont(QFont("Roboto Regular", 12))
        self.results_table.horizontalHeader().setFont(QFont("Roboto Regular", 12))
        self.results_table.verticalHeader().setFont(QFont("Roboto Regular", 11))
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Test Name", "Result Value", "Unit", "Test Date"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Stop from double-click editing
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Enable row selection mode
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # Add context menu for delete/update right-click
        self.results_table.customContextMenuRequested.connect(self.show_context_menu) 
        left_panel.addWidget(self.results_table)
        self.refresh_results_table() # Populate and refresh the results table

        # RIGHT PANEL - TEST SELECTION AND DATA ANALYSIS (STATISTICS AND PLOT)
        right_panel = QVBoxLayout()

        # TEST SELECTION
        label_analysis = QLabel("Analysis of Results")
        label_analysis.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_analysis.setFont(QFont("Roboto Regular", 18, QFont.Weight.Bold))
        right_panel.addWidget(label_analysis)

        analysis_section = QWidget()
        analysis_layout = QVBoxLayout()
        analysis_section.setLayout(analysis_layout)
        analysis_section.setObjectName("analysisSection") 
        stylesheet_file = os.path.join(self.current_dir, f"resources/styles/selected_section.qss")
        selected_section_style = self.load_stylesheet(stylesheet_file)
        analysis_section.setStyleSheet(selected_section_style)

        self.test_analysis_input = QComboBox()
        self.test_analysis_input.addItems(self.get_accessible_values())
        self.test_analysis_input.setFont(QFont("Roboto Regular", 12))
        analysis_layout.addWidget(self.test_analysis_input)

        choose_button = QPushButton("Choose Test/Refresh")
        choose_button.clicked.connect(self.choose_test) # Triggering method to retrieve data from the database
        choose_button.setStyleSheet("background-color: #35a854; color: white; border-radius: 5px; padding: 10px; font-family: Roboto Regular; font-size: 16px;")  # Styling for button
        analysis_layout.addWidget(choose_button)

        self.chosen_table = QTableWidget()
        self.chosen_table.setStyleSheet(selected_section_style)
        self.chosen_table.setFont(QFont("Roboto Regular", 12))
        self.chosen_table.horizontalHeader().setFont(QFont("Roboto Regular", 12))
        self.chosen_table.verticalHeader().setFont(QFont("Roboto Regular", 11))
        self.chosen_table.setColumnCount(3)
        self.chosen_table.setHorizontalHeaderLabels(["Result Value", "Unit", "Test Date"])
        self.chosen_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.chosen_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Stop from double-click editing
        self.chosen_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Enable row selection mode
        analysis_layout.addWidget(self.chosen_table)

        # DATA ANALYSIS

        # STATISTICS
        stats_section = QVBoxLayout()
        stats_section.setSpacing(1)  
        stats_section.setContentsMargins(10, 10, 10, 10)
        stats_label = QLabel("Statistics")
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_label.setFont(QFont("Roboto Regular", 16, QFont.Weight.Bold))
        stats_label.setStyleSheet("background-color: transparent; color: #9e2a47; border-radius: 5px; padding: 10px;")
        stats_section.addWidget(stats_label)

        self.min_label = QLabel("MIN: N/A")
        self.min_label.setFont(QFont("Roboto Regular", 12))
        self.max_label = QLabel("MAX: N/A")
        self.max_label.setFont(QFont("Roboto Regular", 12))
        self.avg_label = QLabel("AVG: N/A")
        self.avg_label.setFont(QFont("Roboto Regular", 12))
    
        for label in [self.min_label, self.max_label, self.avg_label]:
            stats_section.addWidget(label)
            label.setStyleSheet("background-color: transparent; color: black; border-radius: 5px; padding: 10px;")

        stats_widget = QWidget()
        stats_widget.setLayout(stats_section)
        stats_widget.setStyleSheet("background-color: transparent; color: #9e2a47;")
        stats_widget.setFixedWidth(250) 
        stats_section.addStretch()

        analysis_sub_layout = QHBoxLayout()  # Sub-layout for the table and statistics widget
        analysis_sub_layout.addWidget(self.chosen_table)  # Add the table
        analysis_sub_layout.addWidget(stats_widget)  # Add the statistics widget
        analysis_layout.addLayout(analysis_sub_layout)  # Add the sub-layout to the main analysis layout

        # PLOT
        self.plot_widget = QWidget()  
        self.plot_widget.setStyleSheet(selected_section_style)

        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.canvas)  
        self.plot_widget.setLayout(plot_layout)  
        analysis_layout.addWidget(self.plot_widget)  

        right_panel.addWidget(analysis_section)  

        main_layout.addLayout(left_panel)
        main_layout.addLayout(right_panel)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 2)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)  # left, top, right, bottom
        self.setLayout(main_layout)

        self.setWindowTitle("Blood Test Tracker")
        self.show()  # Makes it all visible on screen