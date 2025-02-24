# src/utils/formatting.py
def hex_to_rgb(hex_color):
    """Convert hex color to RGB string"""
    try:
        hex_color = hex_color.lstrip('#')
        return f"{int(hex_color[:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:], 16)}"
    except:
        return "0, 0, 0"  # Default to black if conversion fails

def lighten_color(hex_color, amount=10):
    """Lighten a hex color by a specified amount"""
    try:
        hex_color = hex_color.lstrip('#')
        rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        lightened = [min(255, int(component + amount)) for component in rgb]
        return f"#{lightened[0]:02x}{lightened[1]:02x}{lightened[2]:02x}"
    except:
        return hex_color

def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:,.2f}"

def format_percentage(value: float) -> str:
    """Format value as percentage"""
    return f"{value:+.2f}%"