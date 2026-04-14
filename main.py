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

# 🔥 MAIN + BACKUP CHANNEL
CHANNELS = ["@joinmoney_earning"
offset = 0
user_step = {}

# 🔥 ADMIN ₹4000 FIX
def fix_admin():
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

# 🔥 FORCE JOIN CHECK
def check_join(user_id):
    for channel in CHANNELS:
        url = BASE_URL + "getChatMember"
        params = {"chat_id": channel, "user_id": user_id}

        try:
            res = requests.get(url, params=params).json()
            status = res["result"]["status"]

            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False

    return True

# 🔥 JOIN MESSAGE
def join_msg():
    return """🚫 *Access Locked*

👉 Join both channels:

📢 Main:
https://t.me/joinmoney_earning

📢 Backup:
https://t.me/your_backup_channel

Then press /start again"""

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
    fix_admin()  # admin always ₹4000

    updates = get_updates(offset)

    for update in updates["result"]:
        offset = update["update_id"] + 1

        if "message" not in update:
            continue

        msg = update["message"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        user = get_user(user_id)

        # 🔥 FORCE CHECK (sab pe)
        if not check_join(user_id):
            send_message(user_id, join_msg())
            continue

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

            send_message(user_id, "✅ Welcome!", main_menu())

        # EARN
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

            send_message(user_id, "💰 Select offer:", keyboard)

        elif text == "🥇 Slice ₹250":
            send_message(
                user_id,
                "💳 Slice Card\n🎁 ₹250 Cashback",
                {"inline_keyboard": [[{"text": "🔥 Get ₹250", "url": "https://t.sliceit.com/s?c=irYwC_h&ic=DSNOX46416"}]]}
            )

        elif text == "🥈 Upstox ₹120":
            send_message(
                user_id,
                "📈 Upstox\n🎁 ₹120 Reward",
                {"inline_keyboard": [[{"text": "🔥 Get ₹120", "url": "https://upstox.onelink.me/0H1s/5GCLUE"}]]}
            )

        elif text == "🥉 TaskBucks ₹70":
            send_message(
                user_id,
                "📱 TaskBucks\n🎁 Earn money",
                {"inline_keyboard": [[{"text": "🔥 Start", "url": "http://tbk.bz/jf3gjkc9"}]]}
            )

        elif text == "⏳ Offer Coming Soon":
            send_message(user_id, "🚀 Coming soon")

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
                send_message(ADMIN_ID, f"Withdraw\nUser: {user_id}\nUPI: {upi}")

            del user_step[user_id]

    time.sleep(2)
