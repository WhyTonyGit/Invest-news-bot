from aiogram.fsm.state import State, StatesGroup


class AddCompanyState(StatesGroup):
    waiting_for_query = State()


class RemoveCompanyState(StatesGroup):
    waiting_for_ticker = State()
