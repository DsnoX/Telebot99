import os
import time
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_col = db["users"]
withdraw_col = db["withdraw"]

CHANNEL = "@joinmoney_earning"

offset = 0
user_step = {}

# ------------------ ADMIN SET ------------------
users_col.update_one(
    {"user_id": ADMIN_ID},
    {"$set": {"balance": 4000}},
    upsert=True
)

# ------------------ FUNCTIONS ------------------
def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if keyboard:
        data["reply_markup"] = keyboard

    requests.post(BASE_URL + "sendMessage", json=data)

def get_updates(offset):
    return requests.get(BASE_URL + "getUpdates", params={"offset": offset}).json()

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
    users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": amount}}
    )

# ------------------ VERIFY ------------------
def check_join(user_id):
    url = BASE_URL + "getChatMember"
    params = {"chat_id": CHANNEL, "user_id": user_id}
    try:
        res = requests.get(url, params=params).json()
        status = res["result"]["status"]
        return status in ["member", "administrator", "creator"]
    except:
        return False

# ------------------ MENU ------------------
def main_menu():
    return {
        "keyboard": [
            ["💰 Earn", "👥 Refer"],
            ["💳 Wallet", "💸 Withdraw"]
        ],
        "resize_keyboard": True
    }

# ------------------ BOT LOOP ------------------
print("Bot running...")

while True:
    updates = get_updates(offset)

    for update in updates["result"]:
        offset = update["update_id"] + 1

        if "message" not in update:
            continue

        msg = update["message"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        user = get_user(user_id)

        # START + REFERRAL
        if text.startswith("/start"):
            parts = text.split()

            if len(parts) > 1:
                try:
                    ref_id = int(parts[1])
                    if ref_id != user_id and not user.get("ref_by"):
                        users_col.update_one(
                            {"user_id": user_id},
                            {"$set": {"ref_by": ref_id}}
                        )
                        update_balance(ref_id, 20)
                        send_message(ref_id, "🎉 ₹20 referral bonus received")
                except:
                    pass

            if check_join(user_id):
                send_message(user_id, "✅ Welcome!", main_menu())
            else:
                send_message(
                    user_id,
                    "🚫 Join channel first:\nhttps://t.me/joinmoney_earning"
                )

        # EARN MENU
        elif text == "💰 Earn":
            keyboard = {
                "keyboard": [
                    ["🥇 Slice ₹250"],
                    ["🥈 Upstox ₹120"],
                    ["🥉 TaskBucks ₹70"],
                    ["⏳ Offer Coming Soon"]
                ],
                "resize_keyboard": True
            }

            send_message(
                user_id,
                "💰 *Earn Money Easily*\n\nSelect any offer below 🚀",
                keyboard
            )

        # OFFERS
        elif text == "🥇 Slice ₹250":
            send_message(
                user_id,
                "💳 *Slice Card*\n\n🎁 ₹250 Cashback",
                {
                    "inline_keyboard": [[{
                        "text": "🔥 Get ₹250",
                        "url": "https://t.sliceit.com/s?c=irYwC_h&ic=DSNOX46416"
                    }]]
                }
            )

        elif text == "🥈 Upstox ₹120":
            send_message(
                user_id,
                "📈 *Upstox*\n\n🎁 ₹120 Reward",
                {
                    "inline_keyboard": [[{
                        "text": "🔥 Get ₹120",
                        "url": "https://upstox.onelink.me/0H1s/5GCLUE"
                    }]]
                }
            )

        elif text == "🥉 TaskBucks ₹70":
            send_message(
                user_id,
                "📱 *TaskBucks*\n\n🎁 Earn money easily",
                {
                    "inline_keyboard": [[{
                        "text": "🔥 Start Earning",
                        "url": "http://tbk.bz/jf3gjkc9"
                    }]]
                }
            )

        elif text == "⏳ Offer Coming Soon":
            send_message(user_id, "🚀 New offers coming soon")

        # WALLET
        elif text == "💳 Wallet":
            send_message(user_id, f"💰 Balance: ₹{user['balance']}")

        # REFER
        elif text == "👥 Refer":
            link = f"https://t.me/Taskbucket_bot?start={user_id}"
            send_message(user_id, f"👥 Earn ₹20 per referral\n\n{link}")

        # WITHDRAW
        elif text == "💸 Withdraw":
            if user["balance"] < 290:
                send_message(user_id, "❌ Minimum ₹290 required")
            else:
                send_message(user_id, "Enter UPI ID:")
                user_step[user_id] = "upi"

        elif user_id in user_step:
            upi = text

            if user["balance"] >= 290:
                update_balance(user_id, -290)

                withdraw_col.insert_one({
                    "user_id": user_id,
                    "amount": 290,
                    "upi": upi,
                    "status": "pending"
                })

                send_message(user_id, "✅ Withdraw request sent")
                send_message(
                    ADMIN_ID,
                    f"Withdraw Request\nUser: {user_id}\nUPI: {upi}"
                )
            else:
                send_message(user_id, "❌ Not enough balance")

            del user_step[user_id]

    time.sleep(2)
