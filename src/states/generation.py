from aiogram.fsm.state import State, StatesGroup

class GenState(StatesGroup):
    """
    States for the test case generation process.
    """
    waiting_for_text = State()
    waiting_for_endpoint_text = State()
    waiting_for_clarification = State() # For future "clarifying questions" feature
