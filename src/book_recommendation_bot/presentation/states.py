from aiogram.fsm.state import State, StatesGroup


class OnboardingState(StatesGroup):
    choosing_genres = State()
    waiting_for_prompt = State()
