# utils/helpers.py
import tempfile
import uuid

def process_uploaded_image(uploaded_file):
    """Process an uploaded image file."""
    return uploaded_file.getvalue() if uploaded_file else None

def get_session_id():
    """Generate a unique session ID."""
    return str(uuid.uuid4())

def format_wine_list(wines, include_position=True):
    """Format wine list for display."""
    if not wines:
        return "No wines found in your collection."
    
    result = ""
    for wine in wines:
        result += f"**{wine['name']}**\n"
        result += f"{wine['description']}\n"
        if include_position and wine.get('position_id'):
            result += f"Location: {wine.get('position_id')}\n"
        result += "\n"
    
    return result