import asyncio
import logging
import uuid
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


logging.basicConfig(level=logging.INFO)

TOKEN = "8033257118:AAGhrKz6zfvta_YjB8yCb4L01isfyOJ4GnA"

ADMIN_CHAT_ID = "453926083"


DB_NAME = "applications.db"

# --- Функции для работы с базой данных ---
def init_db():
    """Инициализирует базу данных и создает таблицу applications, если ее нет."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            service_type TEXT NOT NULL,
            description TEXT,
            time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Новая'
        )
    """)
    conn.commit()
    conn.close()
    logging.info("База данных SQLite инициализирована.")

def save_application_to_db(app_data: dict):
    """Сохраняет новую заявку в базу данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications (id, user_id, name, phone, address, service_type, description, time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        app_data["id"],
        app_data["user_id"],
        app_data["name"],
        app_data["phone"],
        app_data["address"],
        app_data["service_type"],
        app_data["description"],
        app_data["time"],
        app_data["status"]
    ))
    conn.commit()
    conn.close()
    logging.info(f"Заявка ID {app_data['id']} сохранена в БД.")

def get_all_applications_from_db():
    """Возвращает все заявки из базы данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, name, phone, address, service_type, description, time, status FROM applications ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    applications = {}
    for row in rows:
        app_id, user_id, name, phone, address, service_type, description, time, status = row
        applications[app_id] = {
            "id": app_id,
            "user_id": user_id,
            "name": name,
            "phone": phone,
            "address": address,
            "service_type": service_type,
            "description": description,
            "time": time,
            "status": status
        }
    return applications

def get_application_by_id_from_db(app_id: str):
    """Возвращает одну заявку по ее ID из базы данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, name, phone, address, service_type, description, time, status FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        app_id, user_id, name, phone, address, service_type, description, time, status = row
        return {
            "id": app_id,
            "user_id": user_id,
            "name": name,
            "phone": phone,
            "address": address,
            "service_type": service_type,
            "description": description,
            "time": time,
            "status": status
        }
    return None

def update_application_status_in_db(app_id: str, new_status: str):
    """Обновляет статус заявки в базе данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id))
    conn.commit()
    conn.close()
    logging.info(f"Статус заявки ID {app_id} обновлен на '{new_status}'.")

# Определение состояний для FSM
class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_service_type = State()
    waiting_for_description = State()
    waiting_for_time = State()

class AdminStates(StatesGroup):
    viewing_applications = State()
    changing_status = State()

class ClientStates(StatesGroup):
    main_menu = State()
    viewing_client_applications = State()


bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_main_menu_keyboard():
    """Главная клавиатура для пользователя."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Сделать новую заявку")],
            [KeyboardButton(text="📊 Мои заявки")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_phone_keyboard():
    """Клавиатура для отправки контакта с кнопкой 'Назад'."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить мой контакт", request_contact=True)],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_service_type_keyboard():
    """Клавиатура для выбора типа услуги с кнопкой 'Назад'."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Видеонаблюдение"), KeyboardButton(text="📞 Телефония")],
            [KeyboardButton(text="🔐 СКУД"), KeyboardButton(text="❔ Другое")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_time_keyboard():
    """Клавиатура для выбора времени с кнопкой 'Назад'."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="09:00-10:00"), KeyboardButton(text="10:00-11:00")],
            [KeyboardButton(text="11:00-12:00"), KeyboardButton(text="12:00-13:00")],
            [KeyboardButton(text="13:00-14:00"), KeyboardButton(text="14:00-15:00")],
            [KeyboardButton(text="15:00-16:00"), KeyboardButton(text="16:00-17:00")],
            [KeyboardButton(text="17:00-18:00")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_back_keyboard():
    """Простая клавиатура только с кнопкой 'Назад'."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_client_applications_list_keyboard(client_applications: list):
    """
    Inline-клавиатура для списка заявок клиента.
    """
    if not client_applications:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Нет активных заявок.", callback_data="no_client_apps")]])

    buttons = []
    for app_id, app_data in client_applications:
        status_emoji = {
            "Новая": "🆕",
            "В работе": "⚙️",
            "Завершена": "✅",
            "Отклонена": "❌"
        }.get(app_data.get("status", "Новая"), "❔")
        buttons.append([InlineKeyboardButton(text=f"{status_emoji} {app_data['service_type']} от {app_data['time']}", callback_data=f"view_client_app_{app_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_admin_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Посмотреть заявки")],
            [KeyboardButton(text="⬅️ Выход из админ-панели")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_application_list_keyboard(applications_page: list):
    if not applications_page:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Нет заявок", callback_data="no_applications")]])
    buttons = []
    for app_id, app_data in applications_page:
        status_emoji = {
            "Новая": "🆕",
            "В работе": "⚙️",
            "Завершена": "✅",
            "Отклонена": "❌"
        }.get(app_data.get("status", "Новая"), "❔")
        buttons.append([InlineKeyboardButton(text=f"{status_emoji} {app_data['name']} - {app_data['service_type']}", callback_data=f"view_app_{app_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_application_details_keyboard(app_id: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить статус", callback_data=f"change_status_{app_id}")],
        [InlineKeyboardButton(text="Назад к списку", callback_data="back_to_app_list")]
    ])
    return keyboard

def get_status_change_keyboard(app_id: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Новая 🆕", callback_data=f"set_status_{app_id}_Новая")],
        [InlineKeyboardButton(text="В работе ⚙️", callback_data=f"set_status_{app_id}_В работе")],
        [InlineKeyboardButton(text="Завершена ✅", callback_data=f"set_status_{app_id}_Завершена")],
        [InlineKeyboardButton(text="Отклонена ❌", callback_data=f"set_status_{app_id}_Отклонена")],
        [InlineKeyboardButton(text="Отмена", callback_data=f"view_app_{app_id}")]
    ])
    return keyboard




@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Добро пожаловать! Что вы хотите сделать?",
        reply_markup=get_main_menu_keyboard()
    )
    await state.set_state(ClientStates.main_menu)



@dp.message(F.text == "📝 Сделать новую заявку", StateFilter(ClientStates.main_menu))
async def start_new_application(message: types.Message, state: FSMContext):
    await message.answer(
        "Для оформления заявки, пожалуйста, представьтесь (введите ваше имя):",
        reply_markup=get_back_keyboard()
    )
    await state.set_state(OrderStates.waiting_for_name)

@dp.message(OrderStates.waiting_for_name, F.text == "⬅️ Назад")
async def back_from_name(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=get_main_menu_keyboard())
    await state.set_state(ClientStates.main_menu)

@dp.message(OrderStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        f"Спасибо, {message.text}! Теперь, пожалуйста, отправьте ваш номер телефона, нажав кнопку ниже "
        "или введите его вручную.",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(OrderStates.waiting_for_phone)

@dp.message(OrderStates.waiting_for_phone, F.text == "⬅️ Назад")
async def back_from_phone(message: types.Message, state: FSMContext):
    await message.answer("Вернитесь к вводу имени:", reply_markup=get_back_keyboard())
    await state.set_state(OrderStates.waiting_for_name)

@dp.message(OrderStates.waiting_for_phone, F.contact)
async def process_phone_by_contact(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("Телефон принят. Теперь введите ваш адрес (город, улица, дом, квартира/офис):",
                         reply_markup=get_back_keyboard())
    await state.set_state(OrderStates.waiting_for_address)

@dp.message(OrderStates.waiting_for_phone)
async def process_phone_by_text(message: types.Message, state: FSMContext):
    if not message.text.replace('+', '').isdigit() and not (message.text.startswith('+') and message.text[1:].isdigit()):
        await message.answer("Пожалуйста, введите корректный номер телефона или используйте кнопку.")
        return

    await state.update_data(phone=message.text)
    await message.answer("Телефон принят. Теперь введите ваш адрес (город, улица, дом, квартира/офис):",
                         reply_markup=get_back_keyboard())
    await state.set_state(OrderStates.waiting_for_address)

@dp.message(OrderStates.waiting_for_address, F.text == "⬅️ Назад")
async def back_from_address(message: types.Message, state: FSMContext):
    """Обработчик кнопки 'Назад' с этапа ввода адреса."""
    await message.answer("Вернитесь к вводу телефона:", reply_markup=get_phone_keyboard())
    await state.set_state(OrderStates.waiting_for_phone)

@dp.message(OrderStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Адрес принят. Теперь выберите тип услуги:",
                         reply_markup=get_service_type_keyboard())
    await state.set_state(OrderStates.waiting_for_service_type)

@dp.message(OrderStates.waiting_for_service_type, F.text == "⬅️ Назад")
async def back_from_service_type(message: types.Message, state: FSMContext):
    """Обработчик кнопки 'Назад' с этапа выбора услуги."""
    await message.answer("Вернитесь к вводу адреса:", reply_markup=get_back_keyboard())
    await state.set_state(OrderStates.waiting_for_address)

@dp.message(OrderStates.waiting_for_service_type)
async def process_service_type(message: types.Message, state: FSMContext):
    allowed_services = ["🎥 Видеонаблюдение", "📞 Телефония", "🔐 СКУД", "❔ Другое"]
    if message.text not in allowed_services:
        await message.answer("Пожалуйста, выберите услугу из предложенных вариантов на клавиатуре.")
        return

    await state.update_data(service_type=message.text)
    await message.answer("Тип услуги выбран. Теперь, пожалуйста, опишите вашу проблему или задачу:",
                         reply_markup=get_back_keyboard())
    await state.set_state(OrderStates.waiting_for_description)

@dp.message(OrderStates.waiting_for_description, F.text == "⬅️ Назад")
async def back_from_description(message: types.Message, state: FSMContext):
    """Обработчик кнопки 'Назад' с этапа ввода описания."""
    await message.answer("Вернитесь к выбору типа услуги:", reply_markup=get_service_type_keyboard())
    await state.set_state(OrderStates.waiting_for_service_type)

@dp.message(OrderStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Описание принято. Теперь выберите удобное для вас время для связи с менеджером:",
                         reply_markup=get_time_keyboard())
    await state.set_state(OrderStates.waiting_for_time)

@dp.message(OrderStates.waiting_for_time, F.text == "⬅️ Назад")
async def back_from_time(message: types.Message, state: FSMContext):
    """Обработчик кнопки 'Назад' с этапа выбора времени."""
    await message.answer("Вернитесь к вводу описания:", reply_markup=get_back_keyboard())
    await state.set_state(OrderStates.waiting_for_description)

@dp.message(OrderStates.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    allowed_times = [
        "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
        "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00",
        "17:00-18:00"
    ]
    if message.text not in allowed_times:
        await message.answer("Пожалуйста, выберите время из предложенных вариантов на клавиатуре.")
        return

    await state.update_data(time=message.text)
    user_data = await state.get_data()
    user_id = str(message.from_user.id)

    application_id = str(uuid.uuid4())[:8]

    application_data = {
        "id": application_id,
        "user_id": user_id,
        "name": user_data.get('name', 'Не указано'),
        "phone": user_data.get('phone', 'Не указан'),
        "address": user_data.get('address', 'Не указан'),
        "service_type": user_data.get('service_type', 'Не указана'),
        "description": user_data.get('description', 'Нет описания'),
        "time": user_data.get('time', 'Не указано'),
        "status": "Новая"
    }
    save_application_to_db(application_data)

    admin_message = (
        f"📌 Новая заявка (ID: {application_id})\n"
        f"👤 Имя: {application_data['name']}\n"
        f"📞 Телефон: {application_data['phone']}\n"
        f"🏠 Адрес: {application_data['address']}\n"
        f"🔧 Услуга: {application_data['service_type']}\n"
        f"📝 Описание: {application_data['description']}\n"
        f"⏰ Время: {application_data['time']}\n"
        f"📊 Статус: {application_data['status']}"
    )

    try:
        await bot.send_message(ADMIN_CHAT_ID, admin_message)
        await message.answer("✅ Заявка отправлена! Менеджер свяжется с вами.",
                             reply_markup=get_main_menu_keyboard())
    except Exception as e:
        logging.error(f"Ошибка при отправке заявки администратору: {e}")
        await message.answer("Произошла ошибка при отправке заявки. Попробуйте позже.",
                             reply_markup=get_main_menu_keyboard())

    await state.clear()
    await state.set_state(ClientStates.main_menu)




@dp.message(F.text == "📊 Мои заявки", StateFilter(ClientStates.main_menu))
async def show_client_applications(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    all_applications = get_all_applications_from_db()
    client_applications = []
    for app_id, app_data in all_applications.items():
        if app_data.get("user_id") == user_id:
            client_applications.append((app_id, app_data))

    if not client_applications:
        await message.answer("У вас пока нет активных заявок.", reply_markup=get_main_menu_keyboard())
        await state.set_state(ClientStates.main_menu)
        return

    await message.answer(
        "Ваши заявки:",
        reply_markup=get_client_applications_list_keyboard(client_applications)
    )
    await state.set_state(ClientStates.viewing_client_applications)

@dp.callback_query(F.data.startswith("view_client_app_"), StateFilter(ClientStates.viewing_client_applications))
async def view_client_application_details(callback_query: types.CallbackQuery, state: FSMContext):
    app_id = callback_query.data.split("_")[3]
    app_data = get_application_by_id_from_db(app_id)
    user_id = str(callback_query.from_user.id)

    if not app_data or app_data.get("user_id") != user_id:
        await callback_query.answer("Заявка не найдена или не принадлежит вам.", show_alert=True)
        return

    status_emoji = {
        "Новая": "🆕",
        "В работе": "⚙️",
        "Завершена": "✅",
        "Отклонена": "❌"
    }.get(app_data.get("status", "Новая"), "❔")

    details_message = (
        f"**Детали вашей заявки (ID: `{app_id}`)**\n"
        f"🔧 Услуга: {app_data.get('service_type', 'Не указана')}\n"
        f"📝 Описание: {app_data.get('description', 'Нет описания')}\n"
        f"⏰ Время: {app_data.get('time', 'Не указано')}\n"
        f"📊 Статус: {status_emoji} {app_data.get('status', 'Новая')}\n\n"
        f"Мы свяжемся с вами по телефону: {app_data.get('phone', 'Не указан')}\n"
        f"По адресу: {app_data.get('address', 'Не указан')}"
    )

    await callback_query.message.edit_text(
        details_message,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад к моим заявкам", callback_data="back_to_client_app_list")]]),
        parse_mode="Markdown"
    )
    await callback_query.answer()

@dp.callback_query(F.data == "back_to_client_app_list", StateFilter(ClientStates.viewing_client_applications))
async def back_to_client_app_list_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await show_client_applications(callback_query.message, state)



@dp.message(Command("admin"))
async def admin_command(message: types.Message, state: FSMContext):
    if str(message.chat.id) != ADMIN_CHAT_ID:
        await message.answer("У вас нет доступа к админ-панели.")
        return

    await state.clear()
    await message.answer(
        "Добро пожаловать в админ-панель! Что хотите сделать?",
        reply_markup=get_admin_main_keyboard()
    )
    await state.set_state(AdminStates.viewing_applications)

@dp.message(F.text == "📊 Посмотреть заявки", StateFilter(AdminStates.viewing_applications))
async def show_applications_list(message: types.Message, state: FSMContext):
    all_applications = get_all_applications_from_db()
    if not all_applications:
        await message.answer("На данный момент нет активных заявок.", reply_markup=get_admin_main_keyboard())
        return

    applications_for_display = []
    for app_id, app_data in all_applications.items():
        applications_for_display.append((app_id, app_data))

    await message.answer(
        "Текущие заявки:",
        reply_markup=get_application_list_keyboard(applications_for_display)
    )

@dp.callback_query(F.data.startswith("view_app_"), StateFilter(AdminStates.viewing_applications))
async def view_application_details(callback_query: types.CallbackQuery, state: FSMContext):
    app_id = callback_query.data.split("_")[2]
    app_data = get_application_by_id_from_db(app_id)

    if not app_data:
        await callback_query.answer("Заявка не найдена.", show_alert=True)
        return

    status_emoji = {
        "Новая": "🆕",
        "В работе": "⚙️",
        "Завершена": "✅",
        "Отклонена": "❌"
    }.get(app_data.get("status", "Новая"), "❔")

    details_message = (
        f"**Детали заявки ID: `{app_id}`**\n"
        f"👤 Имя: {app_data.get('name', 'Не указано')}\n"
        f"📞 Телефон: {app_data.get('phone', 'Не указан')}\n"
        f"🏠 Адрес: {app_data.get('address', 'Не указан')}\n"
        f"🔧 Услуга: {app_data.get('service_type', 'Не указана')}\n"
        f"📝 Описание: {app_data.get('description', 'Нет описания')}\n"
        f"⏰ Время: {app_data.get('time', 'Не указано')}\n"
        f"📊 Статус: {status_emoji} {app_data.get('status', 'Новая')}"
    )

    await callback_query.message.edit_text(
        details_message,
        reply_markup=get_application_details_keyboard(app_id),
        parse_mode="Markdown"
    )
    await callback_query.answer()

@dp.callback_query(F.data.startswith("change_status_"), StateFilter(AdminStates.viewing_applications, AdminStates.changing_status))
async def prompt_change_status(callback_query: types.CallbackQuery, state: FSMContext):
    app_id = callback_query.data.split("_")[2]


    await callback_query.message.edit_text(
        f"Выберите новый статус для заявки ID: `{app_id}`",
        reply_markup=get_status_change_keyboard(app_id),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.changing_status)
    await callback_query.answer()

@dp.callback_query(F.data.startswith("set_status_"), StateFilter(AdminStates.changing_status))
async def set_application_status(callback_query: types.CallbackQuery, state: FSMContext):

    _, _, app_id, new_status = callback_query.data.split("_", 3)

    if get_application_by_id_from_db(app_id):
        update_application_status_in_db(app_id, new_status)


        app_data_updated = get_application_by_id_from_db(app_id)

        await callback_query.answer(f"Статус заявки ID `{app_id}` изменен на '{new_status}'", show_alert=True)

        # Reconstruct the message content with the new status
        status_emoji = {
            "Новая": "🆕",
            "В работе": "⚙️",
            "Завершена": "✅",
            "Отклонена": "❌"
        }.get(app_data_updated.get("status", "Новая"), "❔")

        details_message = (
            f"**Детали заявки ID: `{app_id}`**\n"
            f"👤 Имя: {app_data_updated.get('name', 'Не указано')}\n"
            f"📞 Телефон: {app_data_updated.get('phone', 'Не указан')}\n"
            f"🏠 Адрес: {app_data_updated.get('address', 'Не указан')}\n"
            f"🔧 Услуга: {app_data_updated.get('service_type', 'Не указана')}\n"
            f"📝 Описание: {app_data_updated.get('description', 'Нет описания')}\n"
            f"⏰ Время: {app_data_updated.get('time', 'Не указано')}\n"
            f"📊 Статус: {status_emoji} {app_data_updated.get('status', 'Новая')}"
        )


        await callback_query.message.edit_text(
            details_message,
            reply_markup=get_application_details_keyboard(app_id),
            parse_mode="Markdown"
        )


        client_id = app_data_updated.get("user_id")
        if client_id:
            try:
                await bot.send_message(
                    client_id,
                    f"🔔 Статус вашей заявки на '{app_data_updated['service_type']}' (ID: `{app_id}`) изменен на: **{new_status}**",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.warning(f"Не удалось отправить уведомление клиенту {client_id}: {e}")


        await state.set_state(AdminStates.viewing_applications)

    else:
        await callback_query.answer("Ошибка: Заявка не найдена.", show_alert=True)

        await state.set_state(AdminStates.viewing_applications)
        await show_applications_list(callback_query.message, state)


@dp.callback_query(F.data == "back_to_app_list", StateFilter(AdminStates.viewing_applications))
async def back_to_app_list(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await show_applications_list(callback_query.message, state)

@dp.message(F.text == "⬅️ Выход из админ-панели", StateFilter(AdminStates))
async def exit_admin_panel(message: types.Message, state: FSMContext):
    await message.answer(
        "Вы вышли из админ-панели. Добро пожаловать в главное меню!",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()
    await state.set_state(ClientStates.main_menu)


@dp.message(F.text, ~StateFilter(
    OrderStates.waiting_for_name,
    OrderStates.waiting_for_phone,
    OrderStates.waiting_for_address,
    OrderStates.waiting_for_service_type,
    OrderStates.waiting_for_description,
    OrderStates.waiting_for_time
), ~Command("admin"))
async def handle_unrecognized_text(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state.startswith("AdminStates"):
        return

    await message.answer(
        "Я не понял вашу команду. Пожалуйста, используйте кнопки на клавиатуре или команду /start, чтобы вернуться в главное меню.",
        reply_markup=get_main_menu_keyboard()
    )
    await state.set_state(ClientStates.main_menu)


async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())