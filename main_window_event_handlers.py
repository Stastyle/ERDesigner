# main_window_event_handlers.py
# Contains event handlers for the main window and its view.

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

def keyPressEvent_handler(window, event):
    """Handles key press events for the main window."""
    if event.key() == Qt.Key.Key_Delete:
        window.delete_selected_items() # Assumes delete_selected_items is on window
    elif event.matches(QKeySequence.StandardKey.Undo):
        window.undo_stack.undo()
    elif event.matches(QKeySequence.StandardKey.Redo):
        window.undo_stack.redo()
    # Add other shortcuts here if needed, e.g., Ctrl+T for Add Table
    # elif event.key() == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
    #     window.handle_add_table_button()
    else:
        # Important: Call superclass's implementation for unhandled events
        super(window.__class__, window).keyPressEvent(event)


def view_wheel_event_handler(window, event):
    """Handles wheel events on the QGraphicsView for zooming."""
    factor = 1.15  # Zoom factor
    if event.angleDelta().y() > 0:
        # Zoom In
        window.view.scale(factor, factor)
    else:
        # Zoom Out
        window.view.scale(1.0 / factor, 1.0 / factor)
    event.accept() # Consume the event


def resizeEvent_handler(window, event):
    """Handles the main window's resize event."""
    # Call the superclass's implementation first (important for QMainWindow)
    super(window.__class__, window).resizeEvent(event)
    
    # Update the position of the floating action button
    if hasattr(window, '_update_floating_button_position'):
        window._update_floating_button_position()
    
    # Any other layout adjustments that need to happen on main window resize
    # print(f"Main window resized to: {event.size()}") # For debugging
