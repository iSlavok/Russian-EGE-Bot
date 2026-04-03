from aiogram.types import InlineKeyboardMarkup

from app.schemas import CategoryDTO, TaskOption
from bot.callback_datas import CategoryCallbackData
from bot.keyboards.back_button import add_back_button
from bot.keyboards.category_keyboards import get_categories_keyboard
from bot.keyboards.task_keyboards import get_task_options_keyboard


# ── add_back_button ──────────────────────────────────────────────────────────


class TestAddBackButton:
    def test_none_goes_to_main(self):
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        add_back_button(kb, None)
        assert kb.inline_keyboard[-1][0].callback_data == "main"

    def test_zero_goes_to_categories(self):
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        add_back_button(kb, 0)
        assert kb.inline_keyboard[-1][0].callback_data == "categories"

    def test_positive_id_packs_category_callback(self):
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        add_back_button(kb, 5)
        expected = CategoryCallbackData(category_id=5).pack()
        assert kb.inline_keyboard[-1][0].callback_data == expected


# ── get_categories_keyboard ──────────────────────────────────────────────────


class TestCategoriesKeyboard:
    def test_basic_categories(self):
        cats = [
            CategoryDTO(id=1, name="Math", handler_type=None, parent_id=None),
            CategoryDTO(id=2, name="Physics", handler_type=None, parent_id=None),
        ]
        kb = get_categories_keyboard(cats)
        texts = [row[0].text for row in kb.inline_keyboard[:-1]]  # exclude back button
        assert texts == ["Math", "Physics"]

    def test_with_current_category_adds_all_button(self):
        cats = [
            CategoryDTO(id=1, name="Math", handler_type=None, parent_id=None),
        ]
        kb = get_categories_keyboard(cats, current_category_id=10)
        all_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "Все" in all_texts


# ── get_task_options_keyboard ────────────────────────────────────────────────


class TestTaskOptionsKeyboard:
    def test_option_styles(self):
        options = [
            TaskOption(text="Yes", value="true"),
            TaskOption(text="No", value="false"),
            TaskOption(text="Maybe", value="maybe"),
        ]
        kb = get_task_options_keyboard(options, back_category_id=1)
        # Buttons before the back button row
        option_buttons = [btn for row in kb.inline_keyboard[:-1] for btn in row]
        assert len(option_buttons) == 3
        assert option_buttons[0].text == "Yes"
        assert option_buttons[1].text == "No"
        assert option_buttons[2].text == "Maybe"
