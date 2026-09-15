from aiogram.fsm.state import State, StatesGroup


class OnboardingState(StatesGroup):
    choosing_genres = State()
    waiting_for_prompt = State()


class SearchState(StatesGroup):
    waiting_for_description = State()


class GenreSettingsState(StatesGroup):
    selecting_genres = State()
