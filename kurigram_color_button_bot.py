"""
Kurigram Bot with Colored URL Buttons (Green / Blue / Red)
-------------------------------------------------------------
Telegram Bot API 9.4 (Feb 2026) ne buttons me 'style' field add ki hai:
  "success" -> Green button
  "primary" -> Blue button
  "danger"  -> Red button
  (kuch na do / None) -> Default color

STEP-BY-STEP SETUP:
  1) pip install kurigram tgcrypto --upgrade
  2) my.telegram.org par login karke API_ID aur API_HASH lo
  3) @BotFather se naya bot banao aur BOT_TOKEN lo
  4) Neeche CONFIG section me teeno values daalo
  5) Run karo: python kurigram_color_button_bot.py

Agar koi value missing/galat hogi, bot chalu hote hi clear message dega
ki exactly kya theek karna hai — crash ho kar confusing error nahi dega.
"""

import os
import sys
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# User ke chat state track karne ke liye (memory me, restart hone par reset ho jayega)
user_states = {}

# =========================================================
# CONFIG -- yaha apni values daalo
# (Environment variable set ho to wahi use hogi, warna neeche wali default)
# =========================================================
API_ID = os.environ.get("API_ID", "")          # my.telegram.org se, e.g. "12345678"
API_HASH = os.environ.get("API_HASH", "")      # my.telegram.org se
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")    # @BotFather se

# Apna khud ka text yaha likho (emoji bhi daal sakte ho)
MESSAGE_TEXT = "Click button 👇"

# Har button: (button_text, url, style)
# style options: "success" (green), "primary" (blue), "danger" (red), None (default)
#
# EXAMPLE - Multiple buttons kaise banaye:
#   - Ek row me ek hi button = alag list
#   - Ek row me 2+ buttons = same list ke andar, wo side-by-side (same line) dikhenge
BUTTONS = [
    [("Website", "https://example.com", "success")],     # 🟢 Green (apni row)
    [("YouTube", "https://youtube.com", "primary"),        # 🔵 Blue   \__ ye dono
     ("Instagram", "https://instagram.com", "danger")],    # 🔴 Red    /   same line pe
    [("More Info", "https://example.com/info", None)],     # Default color, naya row
]
# =========================================================


def check_config():
    """Config missing/galat hone par user ko clearly bataye, crash na ho."""
    missing = []
    if not API_ID:
        missing.append("API_ID (my.telegram.org se lo)")
    if not API_HASH:
        missing.append("API_HASH (my.telegram.org se lo)")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN (@BotFather se lo)")

    if missing:
        print("\n❌ Bot start nahi ho paya, ye values missing hain:\n")
        for item in missing:
            print(f"   - {item}")
        print("\nInhe script ke CONFIG section me daalo, ya environment")
        print("variables ki tarah set karo, fir dobara run karo.\n")
        sys.exit(1)

    try:
        int(API_ID)
    except ValueError:
        print(f"\n❌ API_ID sirf number hona chahiye, abhi hai: '{API_ID}'\n")
        sys.exit(1)


check_config()

app = Client(
    "color_button_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,   # Koyeb/Render/Heroku jaisi hosting pe filesystem restart pe
                      # reset ho jata hai, isliye session file disk pe save nahi
                      # karte — har start pe naya session bana lega, koi issue nahi.
)


@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = [
        [InlineKeyboardButton(text, url=url, style=style) for text, url, style in row]
        for row in BUTTONS
    ]
    await message.reply_text(
        MESSAGE_TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@app.on_message(filters.command("newpost"))
async def newpost(client, message):
    user_states[message.from_user.id] = {"step": "text", "buttons": []}
    await message.reply_text(
        "📝 Apna post banana shuru karte hain.\n\n"
        "Pehle wo TEXT bhejo jo buttons ke UPAR dikhega:"
    )


@app.on_message(filters.text & ~filters.command(["start", "newpost"]))
async def collect_input(client, message):
    uid = message.from_user.id
    if uid not in user_states:
        return  # user /newpost flow me nahi hai, ignore karo

    state = user_states[uid]
    step = state["step"]

    if step == "text":
        state["text"] = message.text
        state["step"] = "button_name"
        await message.reply_text("🔘 Ab pehle button ka NAAM bhejo (jaise: Website):")

    elif step == "button_name":
        state["current_name"] = message.text
        state["step"] = "button_url"
        await message.reply_text("🔗 Ab is button ka URL bhejo (https:// se shuru hona chahiye):")

    elif step == "button_url":
        url = message.text.strip()
        if not url.startswith("http"):
            await message.reply_text("⚠️ URL http:// ya https:// se shuru honi chahiye. Dobara bhejo:")
            return
        state["buttons"].append((state["current_name"], url))
        state["step"] = "ask_more"
        await message.reply_text(
            f"✅ Button '{state['current_name']}' add ho gaya.\n\nAur button add karna hai?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Haan, aur button", callback_data="more_yes"),
                InlineKeyboardButton("✅ Nahi, post banao", callback_data="more_no"),
            ]])
        )


@app.on_callback_query(filters.regex("^more_"))
async def handle_more(client, callback_query):
    uid = callback_query.from_user.id
    state = user_states.get(uid)
    if not state:
        await callback_query.answer("Session expire ho gaya, /newpost dobara bhejo.", show_alert=True)
        return

    if callback_query.data == "more_yes":
        state["step"] = "button_name"
        await callback_query.message.edit_text("🔘 Agle button ka NAAM bhejo:")
    else:
        # Final post bana kar bhejo, user isse forward/share kar sakta hai
        keyboard = [[InlineKeyboardButton(name, url=url)] for name, url in state["buttons"]]
        await callback_query.message.delete()
        await client.send_message(
            uid,
            state["text"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await client.send_message(
            uid,
            "👆 Aapka post ready hai! Isse apne channel/group me forward ya share kar sakte ho."
        )
        del user_states[uid]

    await callback_query.answer()


if __name__ == "__main__":
    print("✅ Config theek hai. Bot start ho raha hai...")
    print("   Telegram par apne bot ko /start bhejo.")
    print("   Rokne ke liye Ctrl+C dabao.\n")
    app.run()
