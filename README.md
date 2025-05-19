# ERD Design Tool

## Description

The ERD Design Tool is a PyQt6-based desktop application that allows users to visually create, edit, and manage Entity-Relationship Diagrams (ERDs). The software supports importing and exporting data structures, customizing the appearance of tables and relationships, and offers an intuitive user interface.

## Main Features

* **Visual ERD Creation and Editing:**
    * Add, delete, and edit tables and columns.
    * Create and manage relationships between tables.
    * Support for various data types for columns.
    * Specify Primary Keys (PK) and Foreign Keys (FK).
* **Intuitive User Interface:**
    * Graphical canvas with drag-and-drop support for tables.
    * Grid and Snap to Grid functionality for easy arrangement.
    * Zoom and scroll capabilities for the canvas.
    * Floating Action Button (FAB) for quick item addition.
    * Diagram Explorer to display the diagram structure in a tree view.
* **Customization:**
    * Selectable themes (Light/Dark).
    * Set default colors for table bodies and headers.
    * Customize colors for individual tables.
    * Adjust canvas size.
    * Manage the list of available data types for columns.
* **File and Data Management:**
    * Save and open diagrams (currently in an internal CSV format).
    * Import diagrams from CSV files.
    * Export diagrams to CSV files.
    * Zoom to fit all imported tables after CSV import.
* **Undo/Redo Functionality:**
    * Support for undoing and redoing most operations.
* **Dynamic UI Element Positioning:**
    * The Floating Action Button dynamically adjusts its position based on window size and the Diagram Explorer's docking state.

## Planned Features (from `erd_tool_improvements_he`)

* **UI/UX Enhancements:**
    * Toolbar for common actions.
    * Diagram Explorer improvements (drag to canvas, context menu).
    * Mini-map for the canvas.
    * Snap to other items.
    * Zoom to selection.
    * Customization of relationship line styles and cardinality symbols.
    * Clearer visual distinction for PK/FK columns.
* **Core Functionality:**
    * Generate SQL scripts (CREATE TABLE, ALTER TABLE).
    * Import schema from an existing database.
    * Diagram validation and error checking.
    * Support for additional relationship types (e.g., Identifying).
    * Add annotations/notes to the canvas.
* **Performance and Reliability:**
    * Optimization for large diagrams.
    * Unit tests for critical code sections.
* **Other:**
    * User documentation.

## Prerequisites

* Python 3.x
* PyQt6

## Installation

1.  Clone the repository to your local machine:
    ```bash
    git clone [https://github.com/Stastyle/ERDesigner](https://github.com/Stastyle/ERDesigner)
    cd ERDesigner
    ```
2.  (Recommended) Create and activate a virtual environment:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  Install the dependencies:
    ```bash
    pip install PyQt6
    ```

## Usage

Run the application from the project's root directory using the following command:
```bash
python main.py
```

## File Structure

The project is organized into several Python files, each responsible for a different aspect of the application:

* `main.py`: The main entry point for the application.
* `main_window.py`: Defines the main window (`ERDCanvasWindow`) and manages the integration of various components.
* `canvas_scene.py`: Contains `ERDGraphicsScene` for managing canvas interactions.
* `gui_items.py`: Contains graphical representations of tables and relationships (`TableGraphicItem`, `OrthogonalRelationshipLine`).
* `data_models.py`: Defines the data structures (`Table`, `Column`, `Relationship`).
* `commands.py`: Contains Undo/Redo commands (`QUndoCommand`).
* `dialogs.py`: Defines various dialogs used for user interaction.
* `constants.py`: Contains global constants used throughout the application.
* `utils.py`: Contains general utility functions.
* `config.ini`: The application's configuration file (auto-generated on first run).
* `icon.ico`: The application's icon file.
* **`main_window` Modules:**
    * `main_window_actions.py`: Implementations for actions like save, open, delete.
    * `main_window_config.py`: Loading and saving application settings.
    * `main_window_dialog_handlers.py`: Managing the opening and handling of dialogs.
    * `main_window_event_handlers.py`: Event handlers for the main window and view.
    * `main_window_explorer_utils.py`: Utility functions for the diagram explorer.
    * `main_window_file_operations.py`: File operations like CSV import/export.
    * `main_window_relationship_operations.py`: Operations related to relationships.
    * `main_window_table_operations.py`: Operations related to tables.
    * `main_window_theming.py`: Theme management and application styling.
    * `main_window_ui_setup.py`: Creation of UI elements like menus, diagram explorer, and floating button.

## Configuration

The application uses a `config.ini` file (auto-generated in the project directory) to store settings such as:
* Current theme (light/dark).
* Default table colors.
* Canvas size.
* List of available column data types.

## Contributing

We welcome contributions to the ERD Design Tool! If you'd like to contribute, please feel free to:

* Report bugs or suggest features by opening an issue.
* Submit pull requests with improvements or new features.

If you find this tool useful and would like to support its development, you can make a donation via PayPal:
[stastyle@gmail.com](mailto:stastyle@gmail.com)

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for details.
