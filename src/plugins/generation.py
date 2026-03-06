import io
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import crud, memory_repository
from src.services import llm_processor, parser
from src.states.generation import GenState
from src.keyboards import inline

router = Router()


@router.message(Command("new"))
@router.callback_query(F.data == "start_generation")
async def handle_new_command(event: Message | CallbackQuery, state: FSMContext):
    """Handler for the /new command, starts the generation process."""
    text = """📝 **Ready to generate!**

Choose the generation mode:"""
    kb = inline.get_session_mode_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)
    await state.set_state(GenState.choosing_mode)
    await state.update_data(pending_type="text")


@router.message(Command("analyze_endpoint"))
@router.callback_query(F.data == "start_endpoint_analysis")
async def handle_analyze_endpoint_command(event: Message | CallbackQuery, state: FSMContext):
    """Handler for the /analyze_endpoint command."""
    text = """🔬 **Ready to analyze an endpoint!**

Choose the generation mode:"""
    kb = inline.get_session_mode_keyboard()
    if isinstance(event, CallbackQuery):
        await event.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)
    await state.set_state(GenState.choosing_mode)
    await state.update_data(pending_type="endpoint")


@router.callback_query(F.data.in_({"mode_fresh", "mode_context"}), GenState.choosing_mode)
async def handle_mode_choice(callback: CallbackQuery, state: FSMContext):
    """Handles the Fresh/Context mode selection."""
    use_history = callback.data == "mode_context"
    data = await state.get_data()
    pending_type = data.get("pending_type", "text")
    await state.update_data(use_history=use_history)

    mode_label = "🔗 with context" if use_history else "🆕 fresh start (no history)"

    if pending_type == "text":
        await callback.message.answer(
            f"Got it! Mode: **{mode_label}**\n\nNow send me the raw text, user story, or feature description.",
            parse_mode="Markdown"
        )
        await state.set_state(GenState.waiting_for_text)
    else:
        await callback.message.answer(
            f"Got it! Mode: **{mode_label}**\n\nNow send me the endpoint details:\n`METHOD /path/to/endpoint`\n`{{...json body...}}`",
            parse_mode="Markdown"
        )
        await state.set_state(GenState.waiting_for_endpoint_text)
    await callback.answer()


@router.message(GenState.waiting_for_text, F.text)
async def handle_text_for_generation(message: Message, state: FSMContext, session: AsyncSession):
    """Receives the text from the user and starts the generation."""
    data = await state.get_data()
    use_history = data.get("use_history", True)
    await state.clear()

    # Notify the user that the process has started
    processing_message = await message.answer("⏳ Processing your text... This might take a moment.")

    user = await crud.get_or_create_user(session, message.from_user.id)

    # Get recent memory only if context mode is enabled
    history = None
    if use_history:
        history = await memory_repository.get_recent_memory(session, user.id, limit=20)

    # Generate test cases
    generated_text = await llm_processor.generate_test_cases(
        raw_text=message.text,
        output_format=user.output_format,
        template_type=user.template_type,
        history=history
    )

    # Save to generation history
    generation = await crud.create_generation(
        session=session,
        user_id=user.id,
        raw_text=message.text,
        generated_test_cases=generated_text,
        output_format=user.output_format,
        template_type=user.template_type
    )

    # Save to conversation memory
    await memory_repository.save_to_memory(
        session=session,
        user_id=user.id,
        request=message.text,
        response=generated_text
    )

    # --- Send the result ---
    file_content = generated_text.encode('utf-8')
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_name = f"testcases_{date_str}_{user.id}.{user.output_format}"
    input_file = BufferedInputFile(file_content, filename=file_name)

    if len(generated_text) > 4000:
        summary = f"✅ Your test cases have been generated!\n\nThe result is too long to display directly, but I've attached it as a file (`{file_name}`)."
        await processing_message.edit_text(summary)
        await message.answer_document(input_file)
    else:
        try:
            await processing_message.edit_text(generated_text, parse_mode="Markdown")
        except Exception:
            await processing_message.edit_text(generated_text)
        await message.answer_document(input_file, caption="Here is your file.")


@router.message(GenState.waiting_for_endpoint_text, F.text)
async def handle_endpoint_for_generation(message: Message, state: FSMContext, session: AsyncSession):
    """Receives the endpoint text from the user and starts the generation."""
    data = await state.get_data()
    use_history = data.get("use_history", True)
    await state.clear()

    parsed_data = parser.parse_endpoint_string(message.text)
    if not parsed_data:
        await message.answer("❌ **Invalid format.** Please use the format:\n`METHOD /path\n{...}`")
        return

    method, endpoint, body = parsed_data

    processing_message = await message.answer(f"🔬 Analyzing `{method} {endpoint}`...")

    user = await crud.get_or_create_user(session, message.from_user.id)

    generated_text = await llm_processor.generate_endpoint_test_cases(
        output_format=user.output_format,
        method=method,
        endpoint=endpoint,
        body=body,
    )

    # Save to generation history
    await crud.create_generation(
        session=session,
        user_id=user.id,
        raw_text=message.text,
        generated_test_cases=generated_text,
        output_format=user.output_format,
        template_type="api-first"
    )

    # Save to conversation memory (always, regardless of mode)
    await memory_repository.save_to_memory(
        session=session,
        user_id=user.id,
        request=message.text,
        response=generated_text
    )

    # --- File Export Logic ---
    file_content = generated_text.encode('utf-8')
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_name = f"testcases_{date_str}_{user.id}.{user.output_format}"
    input_file = BufferedInputFile(file_content, filename=file_name)

    # --- Send the result ---
    if len(generated_text) > 4000:
        summary = f"✅ Your API test cases have been generated!\n\nThe result is too long to display directly, but I've attached it as a file (`{file_name}`)."
        await processing_message.edit_text(summary)
        await message.answer_document(input_file)
    else:
        try:
            await processing_message.edit_text(generated_text, parse_mode="Markdown")
        except Exception:
            await processing_message.edit_text(generated_text)
        await message.answer_document(input_file, caption="Here is your file.")


@router.callback_query(F.data == "clear_context")
@router.message(Command("clear_context"))
async def handle_clear_context(event: Message | CallbackQuery, session: AsyncSession):
    """Clears the user's conversation history."""
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id

    user = await crud.get_or_create_user(session, user_id)
    await memory_repository.clear_memory(session, user.id)

    text = "🧹 **Context cleared!** Your conversation history has been erased. The next generation will start fresh."
    if is_callback:
        await event.message.answer(text, parse_mode="Markdown")
        await event.answer("Context cleared!")
    else:
        await event.answer(text, parse_mode="Markdown")


@router.callback_query(F.data == "view_history")
@router.message(Command("history"))
async def handle_history_command(event: Message | CallbackQuery, session: AsyncSession):
    """Displays the user's last 5 generations."""

    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id

    generations = await crud.get_user_generations(session, user_id, limit=5)

    if not generations:
        answer_text = "You have no generation history yet. Use /new to start."
        if is_callback:
            await event.message.answer(answer_text)
            await event.answer()
        else:
            await event.answer(answer_text)
        return

    response_text = "📜 **Your Last 5 Generations:**\n\n"
    for i, gen in enumerate(generations, 1):
        # Truncate raw_text for display
        raw_text_preview = (gen.raw_text[:70] + '...') if len(gen.raw_text) > 70 else gen.raw_text
        response_text += f"*{i}. {gen.created_at.strftime('%Y-%m-%d %H:%M')}*\n"
        response_text += f"```\n{raw_text_preview}\n```\n"

    if is_callback:
        await event.message.answer(response_text, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(response_text, parse_mode="Markdown")


@router.callback_query(F.data == "export_last")
@router.message(Command("export"))
async def handle_export_command(event: Message | CallbackQuery, session: AsyncSession):
    """Exports the last generation as a file."""

    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id

    last_gen = await crud.get_last_generation(session, user_id)

    if not last_gen:
        answer_text = "You have no generation history to export."
        if is_callback:
            await event.message.answer(answer_text)
        else:
            await event.answer(answer_text)
        return

    file_content = last_gen.generated_test_cases.encode('utf-8')
    file_name = f"test_cases_{last_gen.id}.{last_gen.output_format}"

    input_file = BufferedInputFile(file_content, filename=file_name)

    if is_callback:
        await event.message.answer_document(input_file, caption=f"Here are your test cases from {last_gen.created_at.strftime('%Y-%m-%d %H:%M')}.")
        await event.answer("File sent!")
    else:
        await event.answer_document(input_file, caption="Here are your latest test cases.")
