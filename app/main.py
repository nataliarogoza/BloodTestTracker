import sys 
from interface import LabResultsApp
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QLocale

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)) # Set the language to ENG
        ex = LabResultsApp()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
