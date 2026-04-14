import os
import time
import requests
import threading
from pymongo import MongoClient
from dotenv import load_dotenv
from flask import Flask

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

# 🔥 ADMIN ₹4000 FIX
def fix_admin():
    users_col.update_one(
        {"user_id": ADMIN_ID},
        {"$set": {"balance": 4000}},
        upsert=True
    )

# ---------------- FUNCTIONS ----------------
def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(BASE_URL + "sendMessage", json=data)

def get_updates(offset):
    return requests.get(BASE_URL + "getUpdates", params={"offset": offset}).json()

def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({"user_id": user_id, "balance": 0, "ref_by": None})
        return {"user_id": user_id, "balance": 0, "ref_by": None}
    return user

def update_balance(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

# 🔒 FORCE JOIN
def check_join(user_id):
    try:
        res = requests.get(BASE_URL + "getChatMember",
            params={"chat_id": CHANNEL, "user_id": user_id}).json()
        return res["result"]["status"] in ["member","administrator","creator"]
    except:
        return False

def join_msg():
    return """🚫 *Access Locked*

👉 Join channel:
https://t.me/joinmoney_earning

Then press /start again"""

def main_menu():
    return {
        "keyboard": [
            ["💰 Earn", "👥 Refer"],
            ["💳 Wallet", "💸 Withdraw"]
        ],
        "resize_keyboard": True
    }

# ---------------- BOT LOOP ----------------
def bot_loop():
    global offset
    print("🤖 Bot started")

    while True:
        fix_admin()

        updates = get_updates(offset)

        for update in updates.get("result", []):
            offset = update["update_id"] + 1

            if "message" not in update:
                continue

            msg = update["message"]
            user_id = msg["from"]["id"]
            text = msg.get("text", "")

            user = get_user(user_id)

            # 🔒 FORCE JOIN
            if not check_join(user_id):
                send_message(user_id, join_msg())
                continue

            # 🚀 START
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

                send_message(user_id, "✅ Welcome!", main_menu())

            # 💰 EARN
            elif text == "💰 Earn":

                send_message(user_id,
                    """💳 *Slice Offer*

🎁 ₹250 Cashback

1. Install app  
2. Signup  
3. Use code DSNOX46416  
4. First payment""",
                    {"inline_keyboard":[[{"text":"🔥 Get ₹250","url":"https://t.sliceit.com/s?c=irYwC_h&ic=DSNOX46416"}]]}
                )

                time.sleep(1)

                send_message(user_id,
                    """📈 *Upstox*

🎁 ₹120 Reward

1. Open account  
2. Complete KYC""",
                    {"inline_keyboard":[[{"text":"🔥 Get ₹120","url":"https://upstox.onelink.me/0H1s/5GCLUE"}]]}
                )

                time.sleep(1)

                send_message(user_id,
                    """📱 *TaskBucks*

🎁 Earn money

1. Install  
2. Complete tasks""",
                    {"inline_keyboard":[[{"text":"🔥 Start","url":"http://tbk.bz/jf3gjkc9"}]]}
                )

                time.sleep(1)

                send_message(user_id, "🚀 More offers coming soon...")

            # 💳 WALLET
            elif text == "💳 Wallet":

                history = withdraw_col.find({"user_id": user_id}).sort("_id",-1).limit(5)

                hist = ""
                for h in history:
                    hist += f"₹{h['amount']} - {h['status']}\n"

                if not hist:
                    hist = "No transactions"

                send_message(user_id, f"""🏦 *Account Summary*

💰 Balance: ₹{user['balance']}

📜 History:
{hist}""")

            # 👥 REFER
            elif text == "👥 Refer":
                link = f"https://t.me/Taskbucket_bot?start={user_id}"
                send_message(user_id, f"👥 Earn ₹20 per referral\n\n{link}")

            # 💸 WITHDRAW
            elif text == "💸 Withdraw":

                if user["balance"] < 290:
                    send_message(user_id, "❌ Minimum ₹290 required")
                else:
                    keyboard = {
                        "keyboard":[["₹290","₹590","₹999"]],
                        "resize_keyboard":True
                    }
                    send_message(user_id, "💸 Select plan:", keyboard)
                    user_step[user_id] = "plan"

            elif user_id in user_step and user_step[user_id] == "plan":

                if text not in ["₹290","₹590","₹999"]:
                    send_message(user_id,"❌ Invalid plan")
                    continue

                amount = int(text.replace("₹",""))
                user_step[user_id] = {"amount":amount}
                send_message(user_id,"💳 Enter UPI ID:")

            elif user_id in user_step and isinstance(user_step[user_id],dict):

                amount = user_step[user_id]["amount"]
                upi = text

                if user["balance"] < amount:
                    send_message(user_id,"❌ Not enough balance")
                    del user_step[user_id]
                    continue

                update_balance(user_id,-amount)

                withdraw_col.insert_one({
                    "user_id":user_id,
                    "amount":amount,
                    "upi":upi,
                    "status":"pending"
                })

                send_message(user_id,f"✅ Withdraw request sent ₹{amount}")

                send_message(ADMIN_ID,
                    f"🚨 Withdraw Request\nUser: {user_id}\nAmount: ₹{amount}\nUPI: {upi}"
                )

                del user_step[user_id]

        time.sleep(2)

# ---------------- FLASK ----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print("🌐 Flask running on", port)
    app.run(host="0.0.0.0", port=port)

# ---------------- START ----------------
threading.Thread(target=bot_loop).start()
threading.Thread(target=run_flask).start()
