import asyncio
import logging
import os
from typing import Dict
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, Request
import uvicorn

# Конфигурация (будет браться из переменных окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN", '8577568949:AAEph71xKD60CwLBUQNVugxkL2787Dcqo5U')
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", '')
ADMIN_ID = int(os.getenv("ADMIN_ID", 1766219747))
CHANNEL_LINK = 'https://t.me/CIVIKON'
USERNAME = '@Ciivik'

# Инициализация
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

logging.basicConfig(level=logging.INFO)

# Состояния FSM
class CartStates(StatesGroup):
    waiting_price = State()
    delivery_name = State()
    delivery_phone = State()
    delivery_address = State()
    delivery_method = State()

class UserData:
    def __init__(self):
        self.cart: Dict[str, Dict] = {}
        self.current_page = "main"
        self.waiting_price_for = None

# Хранилище пользователей
users_data: Dict[int, UserData] = {}

# Товары (легко расширять)
PRODUCTS = {
    "1": {
        "name": "Кулон-щупальце",
        "desc": "В этого бота не загрузить все мои работы, но это не проблема.\n"
                "Если у вас есть идея или пример кулона, просто напишите или покажите — и я возьму её в работу.\n"
                "А может, в моём канале уже есть работа, которая вам откликнулась, и вы хотели бы что-то похожее.\n"
                "Пишите, я на связи 🐱",
        "price": "договорная",
        "photos": [
            "AgACAgIAAxkBAAMQaacQn31G0oA8L62rtznZmSWZJdAAApEZaxuXizlJ16e_u5qqV1YBAAMCAAN5AAM6BA",
            "AgACAgIAAxkBAAMRaacQnxe-iJ0mz0NZHnhSp4Pxf4sAAnQXaxsuhjhJE5zJUbienX8BAAMCAAN5AAM6BA",
            "AgACAgIAAxkBAAMSaacQn95Vq4O-Ep6VfkXF7mrJWDQAApIZaxuXizlJNtv14LmiYgMBAAMCAAN5AAM6BA"
        ],
        "type": "custom_price"
    },
    "2": {
        "name": "Кулон-лёд",
        "desc": "Эпоксидная смола, в сердце работы можно добавить предмет на ваше усмотрение",
        "price": 800,
        "photo": "AgACAgIAAxkBAAMKaacPzzx8XkZKDv23FkuEGAjMBIMAAngXaxsuhjhJbkammSwPrsYBAAMCAAN5AAM6BA",
        "sizes": {
            "маленький": 700,
            "стандарт": 800,
            "большой": 900
        },
        "type": "sizes"
    },
    "3": {
        "name": "Картина-Nutella",
        "desc": "Банка настоящей нутеллы, разбитая в дребезги",
        "price": 2700,
        "photo": "AgACAgIAAxkBAAMTaacQn-aRndfZTyCdyjKiA58u4FIAAnYXaxsuhjhJwqLHBSqcOQIBAAMCAAN5AAM6BA",
        "type": "standard_custom"
    },
    "4": {
        "name": "Картина стрижамент-водка",
        "desc": "Бутылка настоящего алкоголя, разбитая на осколки",
        "price": 3800,
        "photo": "AgACAgIAAxkBAAMUaacQn7WP9-h2B-oNdPGJywABXlBDAAKTGWsbl4s5Sdyzp5D0oIelAQADAgADeQADOgQ",
        "type": "standard_custom"
    },
    "5": {
        "name": "Картина на заказ",
        "desc": "здесь вы можете заказать картину из осколков на своё усмотрение: бутылка, цвет, размер, рамка, детали и тд.",
        "price": "после уточнения деталей",
        "type": "custom_price"
    }
}

def get_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog"))
    builder.row(InlineKeyboardButton(text="🛒 Корзина", callback_data="cart"))
    return builder.as_markup()

def get_catalog_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in PRODUCTS.keys():
        builder.row(InlineKeyboardButton(text=PRODUCTS[i]["name"], callback_data=f"product_{i}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main"))
    return builder.as_markup()

def get_user_data(user_id: int) -> UserData:
    if user_id not in users_data:
        users_data[user_id] = UserData()
    return users_data[user_id]

async def send_product(product_id: str, user_id: int):
    user_data = get_user_data(user_id)
    product = PRODUCTS[product_id]
    
    # Отправка фото
    if "photos" in product:
        # Все фото кроме последнего - без описания
        for i, photo_id in enumerate(product["photos"]):
            if i == len(product["photos"]) - 1:  # Последнее фото
                await bot.send_photo(user_id, photo_id, caption=product["desc"])
            else:  # Остальные фото без подписи
                await bot.send_photo(user_id, photo_id)
    elif "photo" in product:
        await bot.send_photo(
            user_id, 
            product["photo"], 
            caption=f"{product['name']}\n{product['desc']}\n💰 {product['price']} ₽"
        )
    
    # Клавиатура в зависимости от типа товара
    builder = InlineKeyboardBuilder()
    
    if product["type"] == "sizes":
        for size, price in product["sizes"].items():
            builder.row(InlineKeyboardButton(text=f"{size} ({price}₽)", callback_data=f"add_{product_id}_{size}"))
    elif product["type"] == "standard_custom":
        builder.row(InlineKeyboardButton(text="✅ Купить стандартный размер", callback_data=f"add_{product_id}_standard"))
        builder.row(InlineKeyboardButton(text="💬 Обсудить детали", callback_data=f"custom_{product_id}"))
    elif product["type"] == "custom_price":
        builder.row(InlineKeyboardButton(text="💬 Обсудить детали", callback_data=f"custom_{product_id}"))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад к каталогу", callback_data="catalog"))
    await bot.send_message(user_id, "Выберите действие:", reply_markup=builder.as_markup())

@router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "🎨 Добро пожаловать в магазин ручных работ!\n\n"
        "Здесь вы можете:\n"
        "🛍 Просмотреть каталог\n"
        "🛒 Добавить товары в корзину\n"
        "💳 Оформить заказ",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "main")
async def main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎨 Добро пожаловать в магазин ручных работ!\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):
    await callback.message.edit_text("🛍 Каталог товаров:", reply_markup=get_catalog_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    product_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    await send_product(product_id, user_id)
    await callback.answer()

@router.callback_query(F.data.startswith("add_"))
async def add_to_cart(callback: CallbackQuery):
    parts = callback.data.split("_")
    product_id = parts[1]
    variant = "_".join(parts[2:])
    
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    product = PRODUCTS[product_id]
    if variant == "standard":
        price = product["price"]
        item_name = product["name"]
    else:
        price = product["sizes"][variant] if "sizes" in product else 0
        item_name = f"{product['name']} ({variant})"
    
    user_data.cart[f"{product_id}_{variant}"] = {
        "name": item_name,
        "price": price,
        "quantity": 1
    }
    
    await callback.message.edit_text(
        f"✅ {item_name} добавлен в корзину!\n"
        f"💰 Цена: {price}₽",
        reply_markup=get_catalog_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("custom_"))
async def custom_price(callback: CallbackQuery, state: FSMContext):
    product_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    user_data.waiting_price_for = product_id
    await state.set_state(CartStates.waiting_price)
    await state.update_data(waiting_for=product_id)
    
    await callback.message.edit_text(
        f"💬 Напишите мне для обсуждения деталей:\n"
        f"https://t.me/Ciivik\n\n"
        f"После обсуждения введите цену для этого товара:"
    )
    await callback.answer()

@router.message(StateFilter(CartStates.waiting_price))
async def process_custom_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    try:
        price = int(message.text)
        product_id = user_data.waiting_price_for
        
        user_data.cart[f"{product_id}_custom"] = {
            "name": f"{PRODUCTS[product_id]['name']} (договорная)",
            "price": price,
            "quantity": 1
        }
        
        await message.answer(
            f"✅ Товар {PRODUCTS[product_id]['name']} добавлен в корзину!\n"
            f"💰 Цена: {price}₽",
            reply_markup=get_catalog_keyboard()
        )
    except ValueError:
        await message.answer("Пожалуйста, введите числовую цену (например: 1500)")
    
    await state.clear()
    user_data.waiting_price_for = None

@router.callback_query(F.data == "cart")
async def show_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data.cart:
        await callback.message.edit_text(
            "🛒 Ваша корзина пуста\n\nДобавьте товары из каталога!",
            reply_markup=get_main_keyboard()
        )
        return
    
    total = 0
    cart_text = "🛒 Ваша корзина:\n\n"
    
    for item_id, item in user_data.cart.items():
        total += item["price"]
        cart_text += f"• {item['name']} - {item['price']}₽\n"
    
    cart_text += f"\n💰 Итого: {total}₽"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart"))
    builder.row(InlineKeyboardButton(text="💳 Оформить заказ", callback_data="checkout"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="main"))
    
    await callback.message.edit_text(cart_text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    user_data.cart.clear()
    
    await callback.message.edit_text(
        "🗑 Корзина очищена!",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data.cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return
    
    total = sum(item["price"] for item in user_data.cart.values())
    
    await callback.message.edit_text(
        f"💳 Сумма к оплате: {total}₽\n\n"
        "🔄 Оплата будет добавлена после получения PROVIDER_TOKEN\n\n"
        "Для тестирования перейдите к вводу данных доставки:",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="➡️ Продолжить оформление", callback_data="delivery_start")
        ).as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "delivery_start")
async def delivery_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CartStates.delivery_name)
    await callback.message.edit_text("📝 Введите ваше имя и фамилию:")
    await callback.answer()

@router.message(StateFilter(CartStates.delivery_name))
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CartStates.delivery_phone)
    await message.answer("📱 Введите номер телефона:")

@router.message(StateFilter(CartStates.delivery_phone))
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(CartStates.delivery_address)
    await message.answer("📦 Введите адрес доставки:")

@router.message(StateFilter(CartStates.delivery_address))
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(CartStates.delivery_method)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📬 Почта России", callback_data="delivery_post"))
    builder.row(InlineKeyboardButton(text="🚚 Курьерская доставка", callback_data="delivery_courier"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="delivery_back"))
    
    await message.answer("📤 Выберите способ доставки:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("delivery_"))
async def process_delivery_method(callback: CallbackQuery, state: FSMContext):
    method = "Почта России" if callback.data == "delivery_post" else "Курьерская доставка"
    await state.update_data(delivery_method=method)
    
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    # Подсчет итоговой суммы
    total = sum(item["price"] for item in user_data.cart.values())
    
    # Отправка заказа админу
    order_text = f"🆕 Новый заказ!\n\n"
    order_text += "🛒 Товары:\n"
    for item in user_data.cart.values():
        order_text += f"• {item['name']} - {item['price']}₽\n"
    order_text += f"\n💰 Итого: {total}₽\n"
    data = await state.get_data()
    order_text += f"\n👤 {data['name']}\n📱 {data['phone']}\n📦 {data['address']}\n🚚 {data['delivery_method']}"
    
    await bot.send_message(ADMIN_ID, order_text)
    
    # Подтверждение пользователю
    await callback.message.edit_text(
        "✅ Заказ успешно оформлен!\n"
        "В ближайшее время с вами свяжется администратор для уточнения деталей.",
        reply_markup=get_main_keyboard()
    )
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "delivery_back")
async def delivery_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CartStates.delivery_address)
    await callback.message.edit_text("📦 Введите адрес доставки:")
    await callback.answer()

# Получение File ID
@router.message(F.photo)
async def get_file_id(message: Message):
    file_id = message.photo[-1].file_id
    await message.answer(f"✅ File ID получен:\n`{file_id}`\n\nСкопируйте и добавьте в код!", parse_mode="Markdown")

@router.message(F.video)
async def get_video_id(message: Message):
    file_id = message.video.file_id
    await message.answer(f"✅ Video File ID получен:\n`{file_id}`\n\nСкопируйте и добавьте в код!", parse_mode="Markdown")

# FastAPI приложение
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Bot is running"}

@app.post(f"/webhook/{BOT_TOKEN}")
async def webhook(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

# Функции запуска
async def on_startup():
    """Установка webhook при запуске"""
    webhook_url = f"https://your-domain.bothost.ru/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    print(f"✅ Webhook установлен: {webhook_url}")

async def on_shutdown():
    """Удаление webhook при остановке"""
    await bot.delete_webhook()
    await bot.session.close()
    print("🔄 Webhook удален")

async def main():
    """Главная функция запуска"""
    print("🚀 Запуск бота...")
    await on_startup()
    
    config = uvicorn.Config(
        "main:app", 
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 8000)),
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
