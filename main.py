# main.py
# Main entry point for the ERD Design Tool application.

import sys
from PyQt6.QtWidgets import QApplication

# Import the main window class from main_window.py
# Ensure all other custom modules (constants, utils, data_models, gui_items, dialogs, canvas_scene)
# are in the same directory or in a location accessible via PYTHONPATH.
try:
    from main_window import ERDCanvasWindow
except ImportError as e:
    print(f"Error importing ERDCanvasWindow: {e}")
    print("Please ensure all module files (constants.py, utils.py, data_models.py, "
          "gui_items.py, dialogs.py, canvas_scene.py, main_window.py) "
          "are in the same directory or accessible via PYTHONPATH.")
    sys.exit(1)
except NameError as e: # Catch NameError if a class within main_window isn't defined due to missing import there
    print(f"NameError during import from main_window: {e}")
    print("This might indicate a missing import in one of the modules main_window.py depends on.")
    sys.exit(1)


def main():
    """
    Main function to initialize and run the ERD Design Tool application.
    """
    app = QApplication(sys.argv)
    
    # It's good practice to set application name and version if distributing
    # app.setApplicationName("ERD Design Tool")
    # app.setApplicationVersion("0.1.0")

    try:
        window = ERDCanvasWindow()
        window.show()
    except Exception as e:
        print(f"An error occurred while initializing the main window: {e}")
        # Optionally, show an error message dialog to the user
        # from PyQt6.QtWidgets import QMessageBox
        # QMessageBox.critical(None, "Application Error", f"Could not start the application: {e}")
        sys.exit(1)
        
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
