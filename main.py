import os
import asyncio
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
from pymongo import MongoClient

# ------------------ SETUP ------------------
load_dotenv()
logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ------------------ DATABASE ------------------
client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_col = db["users"]
withdraw_col = db["withdraw_history"]

# ADMIN ALWAYS ₹4000
users_col.update_one(
    {"user_id": ADMIN_ID},
    {"$set": {"balance": 4000}},
    upsert=True
)

# 5 SUCCESS PAYMENT HISTORY (ALL TO YOUR UPI)
if withdraw_col.count_documents({}) == 0:
    withdraw_col.insert_many([
        {"user_id": 847392, "amount": 290, "upi": "tbot99@ptaxis", "status": "success"},
        {"user_id": 928374, "amount": 590, "upi": "tbot99@ptaxis", "status": "success"},
        {"user_id": 736281, "amount": 999, "upi": "tbot99@ptaxis", "status": "success"},
        {"user_id": 564738, "amount": 290, "upi": "tbot99@ptaxis", "status": "success"},
        {"user_id": 192837, "amount": 590, "upi": "tbot99@ptaxis", "status": "success"}
    ])

CHANNELS = ["@your_main_channel"]
ADMIN_UPI = "tbot99@ptaxis"

user_step = {}

# ------------------ FUNCTIONS ------------------
def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({
            "user_id": user_id,
            "balance": 0,
            "ref_by": None
        })
        return {"user_id": user_id, "balance": 0}
    return user

def update_balance(user_id, amount):
    if user_id == ADMIN_ID:
        return
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

async def check_join(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member","administrator","creator"]:
                return False
        except:
            return False
    return True

# ------------------ AUTO MESSAGE ------------------
async def auto_message():
    msgs = [
    "✅ Withdrawal request of ₹290 has been successfully processed",
    "💳 ₹590 payout completed and credited",
    "🎉 Congratulations! ₹999 reward has been credited",
    "🔔 Your withdrawal of ₹290 is successfully completed",
    "🏦 ₹590 has been transferred successfully",
    "💰 Payment of ₹290 confirmed",
    "🚀 ₹999 bonus credited to user account",
    "📢 A user has just received ₹590 payout",
    "🔥 Instant withdrawal of ₹290 completed",
    "✨ ₹999 reward processed successfully"
   ]
    ]
    while True:
        for user in users_col.find():
            try:
                await bot.send_message(user["user_id"], random.choice(msgs))
                await asyncio.sleep(0.1)
            except:
                pass
        await asyncio.sleep(300)

# ------------------ START + REFERRAL ------------------
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    user_id = msg.from_user.id
    args = msg.get_args()

    user = users_col.find_one({"user_id": user_id})

    if not user:
        users_col.insert_one({
            "user_id": user_id,
            "balance": 0,
            "ref_by": None
        })

        if args:
            try:
                ref_id = int(args)
                if ref_id != user_id:
                    users_col.update_one(
                        {"user_id": user_id},
                        {"$set": {"ref_by": ref_id}}
                    )
                    update_balance(ref_id, 20)
                    try:
                        await bot.send_message(ref_id, "🎉 ₹20 referral bonus received!")
                    except:
                        pass
            except:
                pass

    kb = InlineKeyboardMarkup()
    kb = InlineKeyboardMarkup(row_width=1)
kb.add(
    InlineKeyboardButton("📢 Join Channel", url="https://t.me/joinmoney_earning"),
    InlineKeyboardButton("✅ Verify", callback_data="verify")

    )

    await msg.answer("Join channel then verify", reply_markup=kb)

# ------------------ VERIFY ------------------
@dp.callback_query_handler(lambda c: c.data == "verify")
async def verify(call: types.CallbackQuery):
    if await check_join(call.from_user.id):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💰 Earn", "👥 Refer & Earn")
        kb.add("💳 Wallet", "💸 Withdraw")
        await call.message.answer("✅ Verified!", reply_markup=kb)
    else:
        await call.answer("❌ Join channel first", show_alert=True)

# ------------------ REFER ------------------
@dp.message_handler(lambda m: m.text == "👥 Refer & Earn")
async def refer(msg: types.Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={msg.from_user.id}"

    await msg.answer(
        f"👥 Refer & Earn\n\n"
        f"💰 Earn ₹20 per referral\n\n{ref_link}"
    )

# ------------------ EARN ------------------
@dp.message_handler(lambda m: m.text == "💰 Earn")
async def earn(msg: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🥇 Slice ₹250","🥈 Upstox ₹120")
    kb.add("🥉 TaskBucks ₹70","⏳ Offer Coming Soon")
    await msg.answer("Select offer:", reply_markup=kb)

# ------------------ OFFERS ------------------
@dp.message_handler(lambda m: m.text == "🥇 Slice ₹250")
async def slice(msg: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹250", url="https://t.sliceit.com/s?c=irYwC_h&ic=DSNOX46416"))
    await msg.answer("Install → Signup → Complete\nEarn ₹250", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🥈 Upstox ₹120")
async def upstox(msg: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹120", url="https://upstox.onelink.me/0H1s/5GCLUE"))
    await msg.answer("Open account → KYC\nEarn ₹120", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🥉 TaskBucks ₹70")
async def taskbucks(msg: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹70", url="http://tbk.bz/jf3gjkc9"))
    await msg.answer("Complete tasks\nEarn ₹70", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "⏳ Offer Coming Soon")
async def coming(msg: types.Message):
    await msg.answer("More offers coming soon!")

# ------------------ WALLET ------------------
@dp.message_handler(lambda m: m.text == "💳 Wallet")
async def wallet(msg: types.Message):
    user = get_user(msg.from_user.id)
    await msg.answer(f"Balance: ₹{user['balance']}")

# ------------------ WITHDRAW ------------------
@dp.message_handler(lambda m: m.text == "💸 Withdraw")
async def withdraw(msg: types.Message):
    user = get_user(msg.from_user.id)

    if user["balance"] < 290:
        await msg.answer("Minimum ₹290 required")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("₹290","₹590","₹999")
    user_step[msg.from_user.id] = "plan"
    await msg.answer("Select plan:", reply_markup=kb)

# ------------------ HANDLE ------------------
@dp.message_handler()
async def handle(msg: types.Message):
    user_id = msg.from_user.id

    if user_id not in user_step:
        return

    step = user_step[user_id]

    if step == "plan":
        if msg.text not in ["₹290","₹590","₹999"]:
            await msg.answer("Invalid plan")
            return

        amount = int(msg.text.replace("₹",""))
        user_step[user_id] = {"amount": amount}
        await msg.answer(f"Enter UPI ID (Default: {ADMIN_UPI})")

    elif isinstance(step, dict):
        if user_id != ADMIN_ID:
            update_balance(user_id, -step['amount'])

        withdraw_col.insert_one({
            "user_id": user_id,
            "amount": step['amount'],
            "upi": msg.text,
            "status": "pending"
        })

        await bot.send_message(
            ADMIN_ID,
            f"Withdraw Request\nUser: {user_id}\nAmount: ₹{step['amount']}\nUPI: {msg.text}"
        )

        await msg.answer("Request sent")
        del user_step[user_id]

# ------------------ ADMIN ------------------
@dp.message_handler(commands=['admin'])
async def admin(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(f"Users: {users_col.count_documents({})}\nBalance: ₹4000")

# ------------------ MAIN ------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_message())
    executor.start_polling(dp)