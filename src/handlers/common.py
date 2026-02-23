from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext

from src.database import crud
from src.keyboards.inline import get_main_menu_keyboard
from src.plugins.settings import show_format_menu, show_template_menu
from src.states.generation import GenState # Corrected import

router = Router()

@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession):
    """
    Handler for the /start command.
    """
    await crud.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    welcome_text = """👋 **Welcome to the Test Case Generator Bot!**

I can turn your raw ideas, user stories, or feature descriptions into structured test cases.

Use the buttons below to get started."""
    
    await message.answer(
        welcome_text, 
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "start_generation")
async def handle_start_generation(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handler for the 'Generate New' button."""
    await query.answer("Starting new generation...")
    await query.message.answer("Please send me the text you want to generate test cases from.")
    await state.set_state(GenState.waiting_for_text) # Corrected state


@router.callback_query(F.data == "start_endpoint_analysis")
async def handle_start_endpoint_analysis(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handler for the 'From Endpoint' button."""
    await query.answer("Starting endpoint analysis...")
    await query.message.answer("""🔬 **Ready to analyze an endpoint!**

Please send me the endpoint details in the following format:
`METHOD /path/to/endpoint
{
  "key": "value"
}`
For example:
`POST /users
{
  "name": "John Doe",
  "email": "john.doe@example.com"
}`""", parse_mode="Markdown")
    await state.set_state(GenState.waiting_for_endpoint_text)


@router.callback_query(F.data == "open_format_menu")
async def handle_open_format_menu(query: CallbackQuery, session: AsyncSession):
    """Handler for the 'Format' button."""
    await query.answer()
    await show_format_menu(query.message, session)


@router.callback_query(F.data == "open_template_menu")
async def handle_open_template_menu(query: CallbackQuery, session: AsyncSession):
    """Handler for the 'Template' button."""
    await query.answer()
    await show_template_menu(query.message, session)

