from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import crud
from src.keyboards import inline

router = Router()


async def show_format_menu(message: Message, session: AsyncSession):
    """Shows the format selection menu."""
    user = await crud.get_or_create_user(session, message.from_user.id)
    await message.answer(
        "Please choose your desired output format:",
        reply_markup=inline.get_format_keyboard(user.output_format)
    )


async def show_template_menu(message: Message, session: AsyncSession):
    """Shows the template selection menu."""
    user = await crud.get_or_create_user(session, message.from_user.id)
    await message.answer(
        "Please choose a generation template:",
        reply_markup=inline.get_template_keyboard(user.template_type)
    )


# --- Format Settings ---

@router.message(Command("format"))
async def handle_format_command(message: Message, session: AsyncSession):
    """Handler for the /format command."""
    await show_format_menu(message, session)


@router.callback_query(F.data.startswith("set_format_"))
async def handle_set_format_callback(query: CallbackQuery, session: AsyncSession):
    """Handler for format selection callbacks."""
    new_format = query.data.split("_")[-1]
    user = await crud.update_user_settings(session, query.from_user.id, output_format=new_format)
    
    await query.message.edit_text(
        f"✅ Output format set to **{new_format.upper()}**.",
        parse_mode="Markdown",
        reply_markup=inline.get_format_keyboard(user.output_format)
    )
    await query.answer("Format updated!")


# --- Template Settings ---

@router.message(Command("template"))
async def handle_template_command(message: Message, session: AsyncSession):
    """Handler for the /template command."""
    await show_template_menu(message, session)


@router.callback_query(F.data.startswith("set_template_"))
async def handle_set_template_callback(query: CallbackQuery, session: AsyncSession):
    """Handler for template selection callbacks."""
    new_template = query.data.split("_")[-1]
    user = await crud.update_user_settings(session, query.from_user.id, template_type=new_template)
    
    await query.message.edit_text(
        f"✅ Template set to **{new_template.title()}**.",
        parse_mode="Markdown",
        reply_markup=inline.get_template_keyboard(user.template_type)
    )
    await query.answer("Template updated!")
