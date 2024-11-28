import os
from PyQt6.QtWidgets import (QCalendarWidget, QToolButton, QSpinBox)
from PyQt6.QtCore import (QDate, Qt, QSize)
from PyQt6.QtGui import (QTextCharFormat, QColor, QFont, QIcon)

class CustomCalendarWidget(QCalendarWidget):
    """ Custom Qt's Calendar Widget """
    def __init__(self):
        """ Initialize CustomCalendarWidget instance"""
        super().__init__() # Inherit from QCalendarWidget
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.left_arrow_dir = os.path.join(self.current_dir, "images/left-arrow.png")
        self.right_arrow_dir = os.path.join(self.current_dir, "images/right-arrow.png")
        self.up_arrow_dir = os.path.join(self.current_dir, "images/up-arrow.png")
        self.down_arrow_dir = os.path.join(self.current_dir, "images/down-arrow.png")

        self.setStyleSheet("color: white; background-color:#dcdadb; border-radius: 10px; padding: 10px;")
        font = QFont("Roboto Regular", 11)
        self.setFont(font)

        # Header formatting (for day names Monday-Sunday)
        self.days = QTextCharFormat()
        self.days.setBackground(QColor(43, 94, 176, 100))  
        self.days.setForeground(QColor("white"))  # 
        self.setHeaderTextFormat(self.days)  

        self.setSelectedDate(QDate.currentDate()) # Set the default date 
        self.setFirstDayOfWeek(Qt.DayOfWeek.Monday) # Start of week on Monday
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)  
        self.setMaximumDate(QDate.currentDate()) # Disable selecting date set in the future

        # Initialize weekday and weekend formatting (to visually differentiate)
        self.weekday_formatting = QTextCharFormat()
        self.weekday_formatting.setBackground(QColor("#2b5eb0"))
        self.weekday_formatting.setFont(font)
        self.weekday_formatting.setForeground(QColor("white"))
        self.weekend_formatting = QTextCharFormat()
        self.weekend_formatting.setBackground(QColor("#dcdadb"))
        self.weekend_formatting.setFont(font)
        self.weekend_formatting.setForeground(QColor("red"))
        self.update_month_view_format() # Apply formatting

        # Manage formatting when user changes month view
        self.currentPageChanged.connect(self.update_month_view_format)

        # Customize navigation bar and year selection
        self.customize_navigation_bar()
        self.customize_year_selection()

    def update_month_view_format(self):
        """ Update the weekday and weekend formatting only for the days of the current month """
        self.clear_date_formats() # Clean previous formatting (different month = different set of days = different formatting)
        current_month = self.monthShown()
        current_year = self.yearShown()

        # Apply formatting for each VALID DATE in the current month
        for day in range(1, 32): 
            date = QDate(current_year, current_month, day)
            if date.isValid() and date.month() == current_month:
                # Set formatting for valid days (different for week days and weekend days)
                if date.dayOfWeek() == 6 or date.dayOfWeek() == 7:
                    self.setDateTextFormat(date, self.weekend_formatting)
                else:
                    self.setDateTextFormat(date, self.weekday_formatting)

    def clear_date_formats(self):
        """ Clear all date formats """
        for day in range(1, 32):
            for month in range(1, 13):
                date = QDate(self.yearShown(), month, day)
                if date.isValid():
                    self.setDateTextFormat(date, QTextCharFormat())

    def customize_navigation_bar(self):
        """ Customize the navigation bar (mainly the month and year navigation buttons) """
        font = QFont("Roboto", 12)

        tool_buttons = self.findChildren(QToolButton)
        for button in tool_buttons:
            button.setFont(font)
            button.setStyleSheet("color: white; background-color: #2b5eb0; border-radius: 5px; padding: 2px;")
            # Left arrow button
            if button.objectName() == "qt_calendar_prevmonth":
                button.setIcon(QIcon(self.left_arrow_dir))
                button.setIconSize(QSize(30, 20))  
                button.setStyleSheet("margin-left: 100px;")  
            # Right arrow button
            elif button.objectName() == "qt_calendar_nextmonth":
                button.setIcon(QIcon(self.right_arrow_dir))
                button.setIconSize(QSize(30, 20)) 
                button.setStyleSheet("margin-right: 100px;")

        # Customize the month selection dropdown
        tool_buttons = self.findChildren(QToolButton)
        month_button = None
        for button in tool_buttons:
            if button.menu():  # Find the month dropdown button
                month_button = button
                break
        if month_button:
            month_menu = month_button.menu()
            if month_menu:
                for action in month_menu.actions():
                    action.setFont(QFont("Roboto", 12))
                    action.setIconVisibleInMenu(False)  # Hide icons in month selection menu

    def customize_year_selection(self):
        """ Customize the year selection spinner """
        stylesheet_file = os.path.join(self.current_dir, "resources/styles/calendar_spinbox.qss")
        with open(stylesheet_file, "r") as file:
            stylesheet = file.read()
        # Find the year spinbox and apply the custom stylesheet
        year_spinbox = self.findChild(QSpinBox)
        if year_spinbox:
            year_spinbox.setFont(QFont("Roboto", 12))
            year_spinbox.setStyleSheet(stylesheet)