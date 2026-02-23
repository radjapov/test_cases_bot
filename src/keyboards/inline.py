from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_format_keyboard(current_format: str) -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting the output format."""
    formats = ["markdown", "json", "csv"]
    builder = InlineKeyboardBuilder()
    for fmt in formats:
        text = f"✅ {fmt.upper()}" if fmt == current_format else fmt.upper()
        builder.add(InlineKeyboardButton(text=text, callback_data=f"set_format_{fmt}"))
    builder.adjust(3)
    return builder.as_markup()


def get_template_keyboard(current_template: str) -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting the generation template."""
    templates = ["classic", "api-first", "banking", "ui-automation", "performance"]
    builder = InlineKeyboardBuilder()
    for tpl in templates:
        text = f"✅ {tpl.title()}" if tpl == current_template else tpl.title()
        builder.add(InlineKeyboardButton(text=text, callback_data=f"set_template_{tpl}"))
    builder.adjust(3)
    return builder.as_markup()

def get_post_generation_keyboard() -> InlineKeyboardMarkup:
    """Creates a keyboard shown after a generation is complete."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📄 Export as File", callback_data="export_last"))
    # builder.add(InlineKeyboardButton(text="🔄 Regenerate", callback_data="regenerate_last"))
    # builder.add(InlineKeyboardButton(text="🔍 Clarify", callback_data="clarify_last"))
    return builder.as_markup()

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Creates the main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🚀 From Text", callback_data="start_generation"))
    builder.add(InlineKeyboardButton(text="🔬 From Endpoint", callback_data="start_endpoint_analysis"))
    builder.add(InlineKeyboardButton(text="⚙️ Format", callback_data="open_format_menu"))
    builder.add(InlineKeyboardButton(text="📝 Template", callback_data="open_template_menu"))
    builder.add(InlineKeyboardButton(text="📚 History", callback_data="view_history"))
    builder.add(InlineKeyboardButton(text="📄 Export Last", callback_data="export_last"))
    builder.adjust(2, 2, 2)
    return builder.as_markup()
