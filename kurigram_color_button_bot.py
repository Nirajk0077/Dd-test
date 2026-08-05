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

# User ne jo channels connect kiye hain (memory me hi hai, restart pe reset hoga)
# Structure: { user_id: [ {"id": -1001234, "title": "My Channel"}, ... ] }
CONNECTED_CHANNELS = {}

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


@app.on_message(filters.command("addchannel"))
async def addchannel_cmd(client, message):
    user_states[message.from_user.id] = {"step": "add_channel"}
    await message.reply_text(
        "📢 Channel connect karne ke steps:\n\n"
        "1) Bot ko us channel me ADMIN banao (post karne ki permission ke saath)\n\n"
        "2a) Agar channel PUBLIC hai: yaha uska username bhejo (jaise @mychannel)\n\n"
        "2b) Agar channel PRIVATE hai: us channel me jaakar koi bhi ek message "
        "yaha is chat me FORWARD kardo (ID type karne se kaam nahi karega, "
        "bot ko chat 'dekhne' ke liye forward chahiye)"
    )


@app.on_message(filters.command("mychannels"))
async def mychannels_cmd(client, message):
    channels = CONNECTED_CHANNELS.get(message.from_user.id, [])
    if not channels:
        await message.reply_text("Abhi koi channel connect nahi hai. /addchannel use karo.")
        return
    text = "📋 Aapke connected channels:\n\n"
    text += "\n".join(f"• {c['title']}" for c in channels)
    await message.reply_text(text)



@app.on_message(filters.command("newpost"))
async def newpost(client, message):
    user_states[message.from_user.id] = {"step": "text", "buttons": []}
    await message.reply_text(
        "📝 Apna post banana shuru karte hain.\n\n"
        "Pehle wo TEXT bhejo jo buttons ke UPAR dikhega:"
    )


@app.on_message((filters.text | filters.forwarded) & ~filters.command(["start", "newpost", "addchannel", "mychannels"]))
async def collect_input(client, message):
    uid = message.from_user.id
    if uid not in user_states:
        return  # user /newpost flow me nahi hai, ignore karo

    state = user_states[uid]
    step = state["step"]

    if step == "add_channel":
        try:
            if message.forward_from_chat:
                # Private channel se forward kiya gaya message -> seedha chat info mil gaya
                chat = message.forward_from_chat
            else:
                chat_ref = message.text.strip()
                chat = await client.get_chat(chat_ref)

            me = await client.get_me()
            member = await client.get_chat_member(chat.id, me.id)
            if member.status.value not in ("administrator", "creator"):
                await message.reply_text(
                    "⚠️ Bot is channel me ADMIN nahi hai. Pehle channel settings me "
                    "jaakar bot ko admin banao (post karne ki permission ke saath), "
                    "phir /addchannel se dobara try karo."
                )
                return

            CONNECTED_CHANNELS.setdefault(uid, [])
            if not any(c["id"] == chat.id for c in CONNECTED_CHANNELS[uid]):
                CONNECTED_CHANNELS[uid].append({"id": chat.id, "title": chat.title})
            await message.reply_text(f"✅ Channel '{chat.title}' connect ho gaya!")
        except Exception as e:
            await message.reply_text(
                f"❌ Channel connect nahi ho paya.\n"
                f"Public channel ho to @username check karo. Private ho to koi "
                f"message us channel se yaha FORWARD karo.\n\n"
                f"(Error: {e})"
            )
        del user_states[uid]
        return

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
        keyboard = [[InlineKeyboardButton(name, url=url)] for name, url in state["buttons"]]
        state["final_keyboard"] = keyboard
        channels = CONNECTED_CHANNELS.get(uid, [])

        if channels:
            # Konse connected channel me post karna hai, wo choose karwao
            chan_buttons = [
                [InlineKeyboardButton(f"📢 {c['title']}", callback_data=f"postto_{c['id']}")]
                for c in channels
            ]
            chan_buttons.append([InlineKeyboardButton("📩 Mujhe DM me bhejo", callback_data="postto_dm")])
            await callback_query.message.edit_text(
                "📍 Ye post KIS channel me karna hai? Neeche se choose karo:",
                reply_markup=InlineKeyboardMarkup(chan_buttons)
            )
        else:
            # Koi channel connect nahi hai, seedha DM me bhej do
            await callback_query.message.delete()
            await client.send_message(uid, state["text"], reply_markup=InlineKeyboardMarkup(keyboard))
            await client.send_message(
                uid,
                "👆 Aapka post ready hai! Seedha channel me post karwane ke liye "
                "/addchannel se apna channel connect karo."
            )
            del user_states[uid]

    await callback_query.answer()


@app.on_callback_query(filters.regex("^postto_"))
async def handle_postto(client, callback_query):
    uid = callback_query.from_user.id
    state = user_states.get(uid)
    if not state or "final_keyboard" not in state:
        await callback_query.answer("Session expire ho gaya, /newpost dobara bhejo.", show_alert=True)
        return

    target = callback_query.data.split("_", 1)[1]
    markup = InlineKeyboardMarkup(state["final_keyboard"])

    try:
        if target == "dm":
            await client.send_message(uid, state["text"], reply_markup=markup)
            await callback_query.message.edit_text("✅ Post aapko DM me bhej diya gaya.")
        else:
            chat_id = int(target)
            await client.send_message(chat_id, state["text"], reply_markup=markup)
            await callback_query.message.edit_text("✅ Post channel me successfully daal diya gaya!")
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ Post nahi ho paya. Check karo bot admin hai ya nahi.\n(Error: {e})"
        )

    del user_states[uid]
    await callback_query.answer()


if __name__ == "__main__":
    print("✅ Config theek hai. Bot start ho raha hai...")
    print("   Telegram par apne bot ko /start bhejo.")
    print("   Rokne ke liye Ctrl+C dabao.\n")
    app.run()
