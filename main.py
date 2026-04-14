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
if not users_col.find_one({"user_id": ADMIN_ID}):
    users_col.insert_one({"user_id": ADMIN_ID, "balance": 4000, "ref_by": None})

# ------------------ FUNCTIONS ------------------
def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(BASE_URL + "sendMessage", json=data)

def get_updates(offset):
    return requests.get(BASE_URL + "getUpdates", params={"offset": offset}).json()

def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({"user_id": user_id, "balance": 0, "ref_by": None})
        return {"user_id": user_id, "balance": 0}
    return user

def update_balance(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

def check_join(user_id):
    url = BASE_URL + "getChatMember"
    params = {"chat_id": CHANNEL, "user_id": user_id}
    res = requests.get(url, params=params).json()
    try:
        status = res["result"]["status"]
        return status in ["member", "administrator", "creator"]
    except:
        return False

# ------------------ KEYBOARDS ------------------
def main_menu():
    return {
        "keyboard": [
            ["💰 Earn", "👥 Refer"],
            ["💳 Wallet", "💸 Withdraw"]
        ],
        "resize_keyboard": True
    }

def earn_menu():
    return {
        "keyboard": [
            ["🥇 Slice ₹250"],
            ["🥈 Upstox ₹120"],
            ["🥉 TaskBucks ₹70"]
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
                        users_col.update_one({"user_id": user_id}, {"$set": {"ref_by": ref_id}})
                        update_balance(ref_id, 20)
                        send_message(ref_id, "🎉 ₹20 referral bonus received")
                except:
                    pass

            send_message(
                user_id,
                "📢 Join channel first:\nhttps://t.me/joinmoney_earning\n\nThen type VERIFY"
            )

        # VERIFY
        elif text.lower() == "verify":
            if check_join(user_id):
                send_message(user_id, "✅ Verified!", main_menu())
            else:
                send_message(user_id, "❌ Pehle channel join karo")

        # EARN
        elif text == "💰 Earn":
            send_message(user_id, "Select offer:", earn_menu())

        elif text == "🥇 Slice ₹250":
            send_message(user_id, "Install → Signup → Earn ₹250\nhttps://t.sliceit.com/s?c=irYwC_h&ic=DSNOX46416")

        elif text == "🥈 Upstox ₹120":
            send_message(user_id, "Open account → Earn ₹120\nhttps://upstox.onelink.me/0H1s/5GCLUE")

        elif text == "🥉 TaskBucks ₹70":
            send_message(user_id, "Complete tasks → Earn ₹70\nhttp://tbk.bz/jf3gjkc9")

        # WALLET
        elif text == "💳 Wallet":
            send_message(user_id, f"💰 Balance: ₹{user['balance']}")

        # REFER
        elif text == "👥 Refer":
            link = f"https://t.me/Taskbucket_bot?start={user_id}"
            send_message(user_id, f"👥 Refer & Earn ₹20\n\n{link}")

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

                send_message(user_id, "✅ Withdraw request sent\n💸 ₹290 deducted")
                send_message(ADMIN_ID, f"Withdraw Request\nUser: {user_id}\nUPI: {upi}")
            else:
                send_message(user_id, "❌ Balance kam hai")

            del user_step[user_id]

    time.sleep(2)
