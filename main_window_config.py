# main_window_config.py
# Handles loading and saving of application settings.

import configparser
import os
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QByteArray 
import constants

CONFIG_FILE = "config.ini" 

# Removed DEFAULT_EXPLORER_COL0_WIDTH and DEFAULT_EXPLORER_COL1_WIDTH references for initialization here
# as they are no longer used for saving/loading specific widths.

def load_app_settings(window):
    """Loads application settings from the config file."""
    config = configparser.ConfigParser()
    
    # window.explorer_col0_width and window.explorer_col1_width are no longer loaded/used
    window.loaded_window_state = None 

    if not os.path.exists(CONFIG_FILE):
        print(f"Config file '{CONFIG_FILE}' not found. Creating with defaults.")
        constants.current_canvas_dimensions["width"] = constants.DEFAULT_CANVAS_WIDTH
        constants.current_canvas_dimensions["height"] = constants.DEFAULT_CANVAS_HEIGHT
        constants.editable_column_data_types = constants.DEFAULT_COLUMN_DATA_TYPES[:]
        window.current_theme = "light"
        window.user_default_table_body_color = None 
        window.user_default_table_header_color = None
        save_app_settings(window) 
        return

    config.read(CONFIG_FILE)
    window.current_theme = config.get('Theme', 'current_theme', fallback='light')
    
    body_hex = config.get('DefaultTableColors', 'body_color_hex', fallback=None)
    header_hex = config.get('DefaultTableColors', 'header_color_hex', fallback=None)
    
    if body_hex and QColor.isValidColor(body_hex):
        window.user_default_table_body_color = QColor(body_hex)
    else:
        window.user_default_table_body_color = None 

    if header_hex and QColor.isValidColor(header_hex):
        window.user_default_table_header_color = QColor(header_hex)
    else:
        window.user_default_table_header_color = None 

    try:
        canvas_w = config.getint('CanvasSize', 'width', fallback=constants.DEFAULT_CANVAS_WIDTH)
        canvas_h = config.getint('CanvasSize', 'height', fallback=constants.DEFAULT_CANVAS_HEIGHT)
        constants.current_canvas_dimensions["width"] = canvas_w
        constants.current_canvas_dimensions["height"] = canvas_h
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
        constants.current_canvas_dimensions["width"] = constants.DEFAULT_CANVAS_WIDTH
        constants.current_canvas_dimensions["height"] = constants.DEFAULT_CANVAS_HEIGHT
    
    if hasattr(window, 'scene') and window.scene: 
         window.scene.setSceneRect(0, 0, constants.current_canvas_dimensions["width"], constants.current_canvas_dimensions["height"])

    try:
        types_str = config.get('ColumnDataTypes', 'types', fallback=','.join(constants.DEFAULT_COLUMN_DATA_TYPES))
        loaded_types = [t.strip().upper() for t in types_str.split(',') if t.strip()]
        if loaded_types:
            constants.editable_column_data_types = loaded_types
        else: 
            constants.editable_column_data_types = constants.DEFAULT_COLUMN_DATA_TYPES[:]
            if not types_str: 
                 print("ColumnDataTypes 'types' was empty in config, using defaults.")
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("ColumnDataTypes settings not found in config, using defaults.")
        constants.editable_column_data_types = constants.DEFAULT_COLUMN_DATA_TYPES[:]

    if not constants.editable_column_data_types:
        print("Editable column data types list is empty after loading, resetting to defaults.")
        constants.editable_column_data_types = constants.DEFAULT_COLUMN_DATA_TYPES[:]

    # Removed loading of Diagram Explorer column widths
        
    # Load QMainWindow state (for dock widgets, toolbars)
    try:
        window_state_str = config.get('WindowState', 'state', fallback=None)
        if window_state_str:
            if window_state_str.strip(): 
                window.loaded_window_state = QByteArray.fromBase64(window_state_str.encode('utf-8'))
            else:
                window.loaded_window_state = None
                print("WindowState 'state' was empty in config.")
        else:
            window.loaded_window_state = None
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("WindowState not found in config, will use default layout.")
        window.loaded_window_state = None
        
    print(f"Loaded settings: Theme='{window.current_theme}', Canvas=({constants.current_canvas_dimensions['width']}x{constants.current_canvas_dimensions['height']}), Data Types={constants.editable_column_data_types}")
    # Removed print of Explorer Columns


def save_app_settings(window):
    """Saves application settings to the config file."""
    config = configparser.ConfigParser()
    config['Theme'] = {'current_theme': window.current_theme}
    config['DefaultTableColors'] = {
        'body_color_hex': window.user_default_table_body_color.name() if window.user_default_table_body_color else '',
        'header_color_hex': window.user_default_table_header_color.name() if window.user_default_table_header_color else ''
    }
    config['CanvasSize'] = {
        'width': str(constants.current_canvas_dimensions["width"]),
        'height': str(constants.current_canvas_dimensions["height"])
    }
    
    types_to_save = constants.editable_column_data_types
    if not types_to_save: 
        types_to_save = constants.DEFAULT_COLUMN_DATA_TYPES[:]
    config['ColumnDataTypes'] = {'types': ','.join(types_to_save)}

    # Removed saving of Diagram Explorer column widths
    # The section [DiagramExplorer] can be removed entirely if not used for other settings.
    # If you want to keep the section for future use, you can leave it empty or comment out the lines.
    # For now, let's remove the section if it's empty.
    if 'DiagramExplorer' in config: # Check if it exists from previous versions
        config.remove_section('DiagramExplorer')
    
    # Save QMainWindow state
    window_state_bytes = window.saveState()
    config['WindowState'] = {
        'state': window_state_bytes.toBase64().data().decode('utf-8')
    }

    try:
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        print(f"Application settings saved to {CONFIG_FILE}.")
    except IOError as e:
        print(f"Error saving settings to {CONFIG_FILE}: {e}")
