# ERD Design Tool

## Description

The ERD Design Tool is a PyQt6-based desktop application that allows users to visually create, edit, and manage Entity-Relationship Diagrams (ERDs). The software supports importing and exporting data structures, customizing the appearance of tables and relationships, and offers an intuitive user interface.

## Main Features

* **Visual ERD Creation and Editing:**
    * Add, delete, and edit tables and columns.
    * Create and manage relationships between tables.
    * Visual cardinality representation (Crow's Foot symbols and/or text, user-selectable).
    * Data type mismatch warnings with resolution options when creating relationships.
    * Support for various data types for columns.
    * Specify Primary Keys (PK) and Foreign Keys (FK).
    * Copy and paste tables (including via Ctrl+C/Ctrl+V).
    * Duplicate column name validation during table editing.
* **Intuitive User Interface:**
    * Graphical canvas with drag-and-drop support for tables.
    * Grid and Snap to Grid functionality for easy arrangement.
    * Zoom and scroll capabilities for the canvas.
    * Floating Action Button (FAB) for quick item addition.
    * Diagram Explorer to display the diagram structure in a tree view.
    * SQL Preview panel (auto-updates).
    * Notes pane for diagram-specific annotations (saved with the diagram).
    * Context menus for quick actions on tables (Edit, Copy, Delete) and canvas (Add Table, Add Relationship, Paste Table).
* **Customization:**
    * Selectable themes (Light/Dark).
    * Set default colors for table bodies and headers.
    * Customize colors for individual tables.
    * Adjust canvas size.
    * Manage the list of available data types for columns.
    * Configurable cardinality display (Text, Symbols, or Both).
    * Delete custom colors from the color palette (via right-click).
* **File and Data Management:**
    * Save and open diagrams in a custom `.erd` format (internally CSV-based).
    * Import diagrams from `.erd` files.
    * Export diagrams to `.erd` files.
    * Export diagram to SQL DDL (CREATE TABLE, ALTER TABLE for FKs).
    * Import basic SQL DDL to generate a diagram.
    * Zoom to fit all imported tables after import.
    * Prompt to save unsaved changes before closing, opening a new diagram, or importing.
* **Undo/Redo Functionality:**
    * Support for undoing and redoing most operations, including default color changes and notes editing.
* **Dynamic UI Element Positioning:**
    * The Floating Action Button dynamically adjusts its position based on window size and the Diagram Explorer's docking state.
* **Keyboard Shortcuts:**
    * Common operations like Copy (Ctrl+C), Paste (Ctrl+V), Delete, Undo (Ctrl+Z), Redo (Ctrl+Y/Ctrl+Shift+Z) are supported.


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
* `sql_generator.py`: Logic for generating SQL DDL from the diagram.
* `sql_parser.py`: Logic for parsing SQL DDL for import.
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


Feel free to contact me at stas.meirovich@gmail.com
## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for details.
