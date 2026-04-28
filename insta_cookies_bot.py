import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from instagrapi import Client
import pyotp

logging.basicConfig(level=logging.INFO)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class CookiesForm(StatesGroup):
    waiting_usernames = State()
    waiting_passwords = State()
    waiting_secrets = State()

# ================== MAIN KEYBOARD ==================
# এই বাটনটি এখন কিবোর্ডের উপরে বড় হয়ে থাকবে
def main_keyboard():
    button = KeyboardButton(text="Instagram Cookies 🍪 বাহির করুন")
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button]],
        resize_keyboard=True, # বাটনটি সাইজে ছোট এবং সুন্দর দেখাবে
        one_time_keyboard=False # বাটনটি সব সময় কিবোর্ডে থাকবে
    )
    return keyboard

# ================== WELCOME MESSAGE ==================
async def welcome_message(message: types.Message):
    first_name = message.from_user.first_name or "ভাই"
    text = f"""
⚡ 「 𝙳𝚎𝚟𝚎𝚕𝚘𝚙𝚖𝚎𝚗𝚝 𝙱𝚢 𝚂𝚑𝚒𝚙𝚘𝚗 」 ⚡
━━━━━━━━━━━━━━━━━━━━
👋 আরে {first_name} ভাই নাকি! 
আমি জানতাম তুমি কোপ দিতে আসবে 😁

━━━━━━━━━━━━━━━━━━━━
📢 💠【 <a href="https://t.me/Income_Page_Marketing">𝙸𝚗𝚌𝚘𝚖𝚎 𝙿𝚊𝚐𝚎 𝙼𝚊𝚛𝚔𝚎𝚝𝚒𝚗𝚐</a> 】💠
━━━━━━━━━━━━━━━━━━━━
"""
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard(), disable_web_page_preview=True)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await welcome_message(message)

# ================== START COOKIES PROCESS (TEXT HANDLER) ==================
# এখন ইনলাইন বাটন না, সরাসরি টেক্সট বাটন থেকে কাজ করবে
@dp.message(F.text == "Instagram Cookies 🍪 বাহির করুন")
async def start_cookies(message: types.Message, state: FSMContext):
    await state.set_state(CookiesForm.waiting_usernames)
    await message.answer(
        "👤 <b>ইউজারনেম লিস্ট দেন</b>\n(প্রতি লাইনে একটা করে, সর্বোচ্চ ২০টা)",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove() # কাজ চলাকালীন কিবোর্ড সরিয়ে ফেলবে
    )

# ================== USERNAME & PASSWORD HANDLERS ==================
@dp.message(CookiesForm.waiting_usernames)
async def get_usernames(message: types.Message, state: FSMContext):
    usernames = [line.strip() for line in message.text.splitlines() if line.strip()]
    if not usernames or len(usernames) > 20:
        return await message.reply("❌ ১ থেকে ২০টা ইউজারনেম দিন।")
    await state.update_data(usernames=usernames)
    await state.set_state(CookiesForm.waiting_passwords)
    await message.reply(f"✅ {len(usernames)}টা ইউজারনেম নেওয়া হয়েছে।\n\n🔑 এখন সবগুলো অ্যাকাউন্টের <b>পাসওয়ার্ড</b> দিন।", parse_mode="HTML")

@dp.message(CookiesForm.waiting_passwords)
async def get_passwords(message: types.Message, state: FSMContext):
    data = await state.get_data()
    passwords = [line.strip() for line in message.text.splitlines() if line.strip()]
    if len(passwords) != len(data.get("usernames", [])):
        return await message.reply(f"❌ {len(data.get('usernames', []))}টা পাসওয়ার্ড দিন।")
    await state.update_data(passwords=passwords)
    await state.set_state(CookiesForm.waiting_secrets)
    await message.reply("🔐 এখন সবগুলো অ্যাকাউন্টের <b>2FA Secret Key</b> দিন।", parse_mode="HTML")

@dp.message(CookiesForm.waiting_secrets)
async def get_secrets(message: types.Message, state: FSMContext):
    data = await state.get_data()
    secrets = [line.strip().replace(" ", "") for line in message.text.splitlines() if line.strip()]
    if len(secrets) != len(data.get("usernames", [])):
        return await message.reply("❌ 2FA Secret Key ঠিক ততগুলোই দিন।")
    await message.reply(f"🤖 Cookies বাহির করা হচ্ছে... {len(data['usernames'])}টা অ্যাকাউন্ট", reply_markup=main_keyboard()) # কিবোর্ড আবার আনবে
    await process_all_accounts(message, data, secrets, state)

# ================== UPDATED LOGIN LOGIC ==================
async def process_all_accounts(message: types.Message, data, secrets, state: FSMContext):
    usernames = data["usernames"]
    passwords = data["passwords"]
    success_count = 0
    failed_count = 0

    for i in range(len(usernames)):
        username = usernames[i]
        await message.reply(f"🔄 প্রসেস করা হচ্ছে → {username} ({i+1}/{len(usernames)})")

        try:
            cl = Client()
            # ইন্সটাগ্রামের ডিটেকশন এড়াতে ফেইক ডিভাইস সেটআপ
            cl.set_device_settings({
                "app_version": "269.0.0.18.75",
                "android_release": "12",
                "android_version": "31",
                "model": "SM-S901B",
                "manufacturer": "samsung"
            })
            
            totp = pyotp.TOTP(secrets[i])
            verification_code = totp.now()

            # লগইন চেষ্টা
            cl.login(username, passwords[i], verification_code=verification_code)

            cookies_dict = cl.get_cookie_dict()
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
            result = f"{username}|{passwords[i]}|{cookie_str}"
            
            await message.reply(f"<code>{result}</code>", parse_mode="HTML")
            success_count += 1

        except Exception as e:
            failed_count += 1
            # এরর মেসেজ ক্লিন করে দেখানো
            error_msg = str(e)
            if "We can't find an account" in error_msg:
                error_msg = "ইন্সটাগ্রাম এই ইউজারনেম খুঁজে পাচ্ছে না (বট ব্লক হতে পারে)।"
            await message.reply(f"❌ Failed → {username}\nError: {error_msg[:150]}")

        await asyncio.sleep(8)  # আইপি ব্লক এড়াতে বিরতি

    await message.reply(f"🏁 <b>Work Complete!</b>\n\n✅ SUCCESS: <b>{success_count}</b>\n❌ FAILED: <b>{failed_count}</b>", parse_mode="HTML")
    await state.clear()

async def main():
    print("🚀 Bot Started with Keyboard Button!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    usernames = data["usernames"]
    passwords = data["passwords"]
    success_count = 0
    failed_count = 0

    for i in range(len(usernames)):
        username = usernames[i]
        await message.reply(f"🔄 প্রসেস করা হচ্ছে → {username} ({i+1}/{len(usernames)})")

        try:
            cl = Client()
            totp = pyotp.TOTP(secrets[i])
            verification_code = totp.now()

            # ইনস্টাগ্রামে লগইন
            cl.login(username, passwords[i], verification_code=verification_code)

            # কুকিজ বের করা
            cookies_dict = cl.get_cookie_dict()
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])

            result = f"{username}|{passwords[i]}|{cookie_str}"
            
            # Mono space এ দেখানোর জন্য HTML ট্যাগ ব্যবহার করা হলো (যাতে এরর না আসে)
            await message.reply(f"<code>{result}</code>", parse_mode="HTML")
            success_count += 1

        except Exception as e:
            failed_count += 1
            await message.reply(f"❌ Failed → {username}\nError: {str(e)[:250]}")

        # Instagram block এড়ানোর জন্য ১০ সেকেন্ডের বিরতি
        await asyncio.sleep(10)  

    # Final Summary
    final_text = f"""
🏁 <b>Work Complete!</b>

✅ SUCCESS: <b>{success_count}</b>
❌ FAILED: <b>{failed_count}</b>

📊 Total Accounts: {len(usernames)}
"""
    await message.reply(final_text, parse_mode="HTML")

    # কাজ শেষে ইউজারের ডাটা ক্লিয়ার করে দেওয়া
    await state.clear()

# ================== OWNER COMMANDS ==================
@dp.message(Command("status"))
async def bot_status(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ এই কমান্ড শুধু Owner-এর জন্য।")
    await message.reply("✅ <b>Bot চালু আছে</b>\n\n• বন্ধ করতে Render Dashboard থেকে <b>Suspend</b> করুন\n• চালু করতে <b>Resume</b> করুন", parse_mode="HTML")

@dp.message(Command("stopbot"))
async def stop_bot(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ এই কমান্ড শুধু Owner-এর জন্য।")
    
    await message.reply("🛑 Bot polling বন্ধ করা হচ্ছে...\n\nপুরোপুরি বন্ধ করতে Render Dashboard থেকে <b>Suspend</b> করুন।", parse_mode="HTML")
    await dp.stop_polling()

# ================== RUN THE BOT ==================
async def main():
    print("🚀 Instagram Cookies Bot Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
