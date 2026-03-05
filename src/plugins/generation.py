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
async def handle_new_command(message: Message, state: FSMContext):
    """Handler for the /new command, starts the generation process."""
    await message.answer("""📝 **Ready to generate!**

Please send me the raw text, user story, or feature description you want to turn into test cases.""", parse_mode="Markdown")
    await state.set_state(GenState.waiting_for_text)


@router.message(Command("analyze_endpoint"))
async def handle_analyze_endpoint_command(message: Message, state: FSMContext):
    """Handler for the /analyze_endpoint command."""
    await message.answer("""🔬 **Ready to analyze an endpoint!**

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


@router.message(GenState.waiting_for_text, F.text)
async def handle_text_for_generation(message: Message, state: FSMContext, session: AsyncSession):
    """Receives the text from the user and starts the generation."""
    await state.clear()
    
    # Notify the user that the process has started
    processing_message = await message.answer("⏳ Processing your text... This might take a moment.")

    user = await crud.get_or_create_user(session, message.from_user.id)

    # Get recent memory
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
        # Send the full text and the file
        try:
            await processing_message.edit_text(generated_text, parse_mode="Markdown")
        except Exception:
            await processing_message.edit_text(generated_text)
        await message.answer_document(input_file, caption="Here is your file.")


@router.message(GenState.waiting_for_endpoint_text, F.text)
async def handle_endpoint_for_generation(message: Message, state: FSMContext, session: AsyncSession):
    """Receives the endpoint text from the user and starts the generation."""
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
        template_type="api-first"  # Force api-first for this feature
    )
    
    # Save to conversation memory
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
        # Send the full text and the file
        try:
            await processing_message.edit_text(generated_text, parse_mode="Markdown")
        except Exception:
            await processing_message.edit_text(generated_text)
        await message.answer_document(input_file, caption="Here is your file.")


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
