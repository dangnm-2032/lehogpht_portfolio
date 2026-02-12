import os
import re
import unicodedata

DATA_FOLDER = 'data/'
TEMP_FOLDER = os.path.join(DATA_FOLDER, '.temp')

def get_projects():
    return os.listdir(DATA_FOLDER)

def slugify_vi(text):
    text = text.replace('Đ', 'D').replace('đ', 'd')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def reorder_dict(d, value_to_move, new_position):
    """
    d: dict with integer keys representing order
    value_to_move: the value you want to move
    new_position: the new key position (1-based)
    """
    # Sort dict by keys
    items = [v for k, v in sorted(d.items())]

    # Remove the value
    items.remove(value_to_move)

    # Insert it at new position (0-based index)
    items.insert(new_position - 1, value_to_move)

    # Rebuild dict with keys starting from 1
    return {i + 1: v for i, v in enumerate(items)}
