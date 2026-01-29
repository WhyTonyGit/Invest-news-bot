from aiogram.fsm.state import State, StatesGroup


class AddCompanyState(StatesGroup):
    waiting_for_query = State()
    waiting_for_choice = State()


class RemoveCompanyState(StatesGroup):
    waiting_for_ticker = State()


class SettingsState(StatesGroup):
    waiting_for_poll_interval = State()
    waiting_for_hourly_limit = State()
