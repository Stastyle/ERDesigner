# main_window_event_handlers.py
# Version: 20250518.0040
# Contains event handlers for the main window and its view.

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

def keyPressEvent_handler(window, event):
    """Handles key press events for the main window."""
    if event.key() == Qt.Key.Key_Delete:
        window.delete_selected_items()
    elif event.matches(QKeySequence.StandardKey.Undo):
        window.undo_stack.undo()
    elif event.matches(QKeySequence.StandardKey.Redo):
        window.undo_stack.redo()
    elif event.key() == Qt.Key.Key_Escape:
        # Check if any drawing mode is active and cancel it
        action_cancelled = False
        if hasattr(window, 'scene') and hasattr(window.scene, 'cancel_active_drawing_modes'):
            action_cancelled = window.scene.cancel_active_drawing_modes()
        
        if action_cancelled:
            event.accept() # Consume ESC if a drawing mode was cancelled
            return
        # If no drawing mode was active, let ESC propagate for other uses (e.g., close dialogs)
    
    # Add other shortcuts here if needed
    # elif event.key() == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
    #     window.handle_add_table_button()
    
    # Call superclass's implementation for unhandled events if not accepted
    if not event.isAccepted():
        super(window.__class__, window).keyPressEvent(event)


def view_wheel_event_handler(window, event):
    """Handles wheel events on the QGraphicsView for zooming."""
    factor = 1.15
    if event.angleDelta().y() > 0:
        window.view.scale(factor, factor)
    else:
        window.view.scale(1.0 / factor, 1.0 / factor)
    event.accept()


def resizeEvent_handler(window, event): # This is a method of ERDCanvasWindow, not a standalone handler
    """Handles the main window's resize event."""
    super(window.__class__, window).resizeEvent(event) # Call QMainWindow's resizeEvent
    if hasattr(window, '_update_floating_button_position'):
        window._update_floating_button_position()
