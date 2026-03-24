import threading
import telebot
import time
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

REVIEW_CHANNEL_ID = -1003289844580
MAIN_CHANNEL_ID = -1002807922369
MAIN_CHANNEL_USERNAME = "FraudsWatchlist"
BOT_USERNAME = "FraudsWatchlistBOT"

DATA_FILE = "reports.json"

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r") as f:
            reports = json.load(f)
    except:
        reports = {}
else:
    reports = {}

user_state = {}
user_lock = set()
group_ids = set()
users_db = {}

REPORT_PNG_URL = "https://t.me/ScamsWatchlist/9"

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(reports, f, indent=2)

def show_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Create Report"))
    bot.send_message(chat_id, "Main Menu:", reply_markup=markup)

def get_user_id_by_username(username):
    try:
        user = bot.get_chat(username if username.startswith("@") else f"@{username}")
        return user.id
    except:
        return "Unknown"

def main_menu_reply():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("Create Report"),
    )
    return markup

@bot.message_handler(func=lambda m: m.text.startswith("ID:"))
def set_id_from_missrose(m):
    cid = m.chat.id
    try:
        user_id = int(m.text.split(":")[1].strip())
        if cid in user_state:
            user_state[cid]["target_chat_id"] = user_id
            bot.send_message(cid, f"Telegram User ID set to {user_id}")
    except Exception as e:
        bot.send_message(cid, f"Failed to set ID: {e}")

@bot.message_handler(commands=['start'])
def start(msg):
    cid = msg.chat.id
    bot.send_message(
        cid,
        "Hello! Click the button below to create a report.\n"
        "If you want to lookup a user you can use /lookup",
        reply_markup=main_menu_reply()
    )

@bot.message_handler(func=lambda msg: msg.text == "Create Report")
def create_report(msg):
    cid = msg.chat.id
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("User Report"),
        KeyboardButton("Imp Report")
    )
    markup.row(
        KeyboardButton("Cancel Report")
    )
    bot.send_message(
        cid,
        "Choose a report type:",
        reply_markup=markup
    )

@bot.message_handler(commands=['lookup'])
def lookup(msg):
    args = msg.text.split()

    if len(args) == 1:
        bot.send_message(msg.chat.id, "Usage: /lookup scammer_id or @username")
        return

    query = args[1].lower()

    for rid, data in reports.items():
        if query in data.get("target", "").lower() and data.get("msg_link"):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(
                "View Report",
                url=data["msg_link"]
            ))

            bot.send_message(
                msg.chat.id,
                f"This user has already been posted on @{MAIN_CHANNEL_USERNAME}.",
                reply_markup=markup
            )
            return

    bot.send_message(msg.chat.id, "No reports found.")

@bot.message_handler(func=lambda m: m.text == "User Report")
def user_report_start(msg):
    cid = msg.chat.id

    user_state[cid] = {"step": "target"}

    bot.send_message(
        cid,
        "Enter the username or user ID of the user you would like to report:"
    )

@bot.message_handler(func=lambda m: m.text == "Imp Report")
def imp_report_start(msg):
    cid = msg.chat.id

    user_state[cid] = {"step": "imp_fake"}

    bot.send_message(
        cid,
        "Send the ❌ impersonator's @username:"
    )

@bot.message_handler(func=lambda m: m.text == "Cancel Report")
def cancel_report(msg):
    user_state.pop(msg.chat.id, None)

    bot.send_message(
        msg.chat.id,
        "Your report has been cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )

    start(msg)

# ✅ ONLY LAST ORIGINAL HANDLE_STEPS (UNCHANGED LOGIC)
@bot.message_handler(func=lambda msg: msg.chat.type == "private")
def handle_steps(msg):
    cid = msg.chat.id
    text = (msg.text or "").strip()

    if cid in user_lock:
        return
    user_lock.add(cid)

    try:
        if cid not in user_state:
            return

        step = user_state[cid].get("step")

        # --- CANCEL REPORT ---
        if text == "Cancel Report":
            user_state.pop(cid, None)
            bot.send_message(cid, "Your report has been cancelled.")

            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row(KeyboardButton("User Report"), KeyboardButton("Imp Report"))
            bot.send_message(cid, "Choose a report type below:", reply_markup=markup)
            return

        # --- USER REPORT STEPS ---
        if step == "target":
            if text.isdigit():
                user_state[cid]["target_chat_id"] = int(text)
                user_state[cid]["target"] = "@N/A"
            else:
                user_state[cid]["target"] = text
                clean_username = text.lstrip("@")
                user_state[cid]["target_clean_username"] = clean_username
                user_state[cid]["target_chat_id"] = get_user_id_by_username(text) or "Unknown"

            user_state[cid]["step"] = "proof"
            bot.send_message(cid, "Send the proof group/channel link where you posted the scam evidence:")
            return

        elif step == "proof":
            user_state[cid]["proof"] = text

            rid = str(len(reports) + 1)
            user_state[cid]["rid"] = rid
            reports[rid] = user_state[cid].copy()
            save()

            user_state[cid].pop("step", None)
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row(KeyboardButton("Submit Report"), KeyboardButton("Cancel Report"))
            bot.send_message(cid, "Review your report and choose an action:", reply_markup=markup)
            return

        # --- IMPERSONATION REPORT STEPS ---
        elif step == "imp_fake":
            user_state[cid]["fake"] = text
            user_state[cid]["step"] = "imp_real"
            bot.send_message(cid, "Now send the ✅ real user's @username:")
            return

        elif step == "imp_real":
            user_state[cid]["real"] = text
            rid = str(len(reports) + 1)
            user_state[cid]["rid"] = rid
            reports[rid] = user_state[cid].copy()

            fake_username = user_state[cid]["fake"]
            reports[rid]["target_chat_id"] = get_user_id_by_username(fake_username) or "Unknown"
            save()
            user_state[cid].pop("step", None)

            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row(KeyboardButton("Submit Report"), KeyboardButton("Cancel Report"))
            bot.send_message(cid, "Review your report and choose an action:", reply_markup=markup)
            return

        # --- SUBMIT REPORT ---
        elif text == "Submit Report":
            data = user_state.get(cid)
            if not data or "rid" not in data:
                bot.send_message(cid, "No report found.")
                return

            rid = data["rid"]
            report = reports.get(rid)
            if report.get("submitted"):
                bot.send_message(cid, "⚠️ Already submitted.")
                return

            reports[rid]["submitted"] = True
            save()

            target_display = report.get("target") or report.get("fake")
            clean_username = report.get("target_clean_username")
            target_id = report.get("target_chat_id")
            proof_link = report.get("proof", "")

            review_text = (
                f"New Report #{rid}\n"
                f"Reporter: @{report.get('reporter')} ({report.get('chat_id')})\n"
                f"Target: {target_display}\n"
                f"Proof: {proof_link or 'No proof'}"
            )

            review_markup = InlineKeyboardMarkup()
            review_markup.add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{rid}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{rid}")
            )
            bot.send_message(REVIEW_CHANNEL_ID, review_text, reply_markup=review_markup)

            main_markup = InlineKeyboardMarkup()
            buttons_main = []

            if "fake" in report and "real" in report:
                fake = report["fake"]
                real = report["real"]
                fake_id = get_user_id_by_username(fake) if not isinstance(fake, int) else fake
                real_id = get_user_id_by_username(real) if not isinstance(real, int) else real
                caption = (
                    f"❌ Fake: <a href='tg://openmessage?user_id={fake_id}'>{fake}</a> ({fake_id})\n"
                    f"✅ Real: <a href='tg://openmessage?user_id={real_id}'>{real}</a> ({real_id})"
                )
                buttons_main = [
                    InlineKeyboardButton("Fake Profile", url=f"tg://openmessage?user_id={fake_id}"),
                    InlineKeyboardButton("Real Profile", url=f"tg://openmessage?user_id={real_id}")
                ]
            else:
                caption = f"❌ <b>User</b> {target_display} (Telegram ID: {target_id}) flagged"
                if clean_username:
                    buttons_main.append(
                        InlineKeyboardButton("View Profile", url=f"https://t.me/{clean_username}")
                    )
                elif isinstance(target_id, int):
                    buttons_main.append(
                        InlineKeyboardButton("View Profile", url=f"tg://openmessage?user_id={target_id}")
                    )

            if proof_link:
                buttons_main.append(InlineKeyboardButton("View Proofs", url=proof_link))

            if buttons_main:
                main_markup.add(*buttons_main)

            bot.send_photo(
                MAIN_CHANNEL_ID,
                REPORT_PNG_URL,
                caption=caption,
                parse_mode="HTML",
                reply_markup=main_markup
            )

            bot.send_message(cid, "Your report has been submitted for review!")
            user_state.pop(cid, None)
            show_main_menu(cid)

    except Exception as e:
        print("ERROR:", e)

    finally:
        user_lock.discard(cid)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    cid = call.message.chat.id

    try:
        if call.data.startswith("approve_") or call.data.startswith("reject_"):
            rid = str(call.data.split("_")[1])
            data = reports.get(rid)

            if not data:
                bot.answer_callback_query(call.id, "Report not found")
                return

        if call.data.startswith("approve_"):
            proof = data.get("proof")
            target = data.get("target") or data.get("fake") or "@N/A"

            caption = f"❌ <b>User</b> {target} flagged"

            markup = InlineKeyboardMarkup()
            buttons = []

            if proof:
                buttons.append(InlineKeyboardButton("View Proofs", url=proof))

            if buttons:
                markup.add(*buttons)

            sent = bot.send_photo(
                MAIN_CHANNEL_ID,
                REPORT_PNG_URL,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )

            reports[rid]["approved"] = True
            reports[rid]["msg_link"] = f"https://t.me/{MAIN_CHANNEL_USERNAME}/{sent.message_id}"
            save()

            bot.answer_callback_query(call.id, "Approved ✅")

        elif call.data.startswith("reject_"):
            reports[rid]["rejected"] = True
            save()
            bot.answer_callback_query(call.id, "Rejected ❌")

    except Exception as e:
        print("CALLBACK ERROR:", e)

@bot.message_handler(func=lambda msg: msg.chat.type in ["group", "supergroup"])
def track_groups(msg):
    group_ids.add(msg.chat.id)

def auto_promo():
    while True:
        try:
            for gid in list(group_ids):
                try:
                    markup = InlineKeyboardMarkup()
                    markup.add(
                        InlineKeyboardButton(
                            "Submit Report",
                            callback_data="create"
                        )
                    )

                    bot.send_message(
                        gid,
                        "<b>🌟 Keep your community safe!</b>\n\n"
                        "<b>Report scammers and verify users easily.</b>",
                        parse_mode="HTML",
                        reply_markup=markup
                    )

                    time.sleep(1)

                except Exception as e:
                    print(f"[PROMO ERROR] {gid} -> {e}")

            print("Promo sent to all groups ✅")

        except Exception as e:
            print("AUTO PROMO LOOP ERROR:", e)

        time.sleep(3600)


if __name__ == "__main__":
    print("Bot started...")

    promo_thread = threading.Thread(target=auto_promo)
    promo_thread.daemon = True
    promo_thread.start()

    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print("POLLING ERROR:", e)
            time.sleep(5)