import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from instagrapi import 
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

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Instagram Cookies 🍪 বাহির করুন", callback_data="start_cookies")]
        ]
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await welcome_message(message)

# ================== START COOKIES PROCESS ==================
@dp.callback_query(F.data == "start_cookies")
async def start_cookies(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CookiesForm.waiting_usernames)
    await callback.message.edit_text(
        "👤 ইউজারনেম লিস্ট দেন\n(প্রতি লাইনে একটা করে, সর্বোচ্চ ২০টা)"
    )
    await callback.answer()

# ================== USERNAME HANDLER ==================
@dp.message(CookiesForm.waiting_usernames)
async def get_usernames(message: types.Message, state: FSMContext):
    usernames = [line.strip() for line in message.text.splitlines() if line.strip()]
    
    if not usernames or len(usernames) > 20:
        return await message.reply("❌ ১ থেকে ২০টা ইউজারনেম দিন (প্রতি লাইনে একটা)।")
    
    await state.update_data(usernames=usernames)
    await state.set_state(CookiesForm.waiting_passwords)
    
    await message.reply(f"✅ {len(usernames)}টা ইউজারনেম নেওয়া হয়েছে।\n\n🔑 এখন সবগুলো অ্যাকাউন্টের পাসওয়ার্ড দিন (একই অর্ডারে, প্রতি লাইনে একটা)")

# ================== PASSWORD HANDLER ==================
@dp.message(CookiesForm.waiting_passwords)
async def get_passwords(message: types.Message, state: FSMContext):
    data = await state.get_data()
    passwords = [line.strip() for line in message.text.splitlines() if line.strip()]
    
    if len(passwords) != len(data.get("usernames", [])):
        return await message.reply(f"❌ {len(data.get('usernames', []))}টা পাসওয়ার্ড দিন।")
    
    await state.update_data(passwords=passwords)
    await state.set_state(CookiesForm.waiting_secrets)
    
    await message.reply("🔐 এখন সবগুলো অ্যাকাউন্টের **2FA Secret Key** দিন\n(প্রতি লাইনে একটা করে)")

# ================== 2FA SECRET HANDLER ==================
@dp.message(CookiesForm.waiting_secrets)
async def get_secrets(message: types.Message, state: FSMContext):
    data = await state.get_data()
    secrets = [line.strip().replace(" ", "") for line in message.text.splitlines() if line.strip()]
    
    if len(secrets) != len(data.get("usernames", [])):
        return await message.reply("❌ 2FA Secret Key গুলোও ঠিক ততগুলো দিন।")
    
    await message.reply(f"🤖 Cookies বাহির করা হচ্ছে... {len(data['usernames'])}টা অ্যাকাউন্ট")
    
    await process_all_accounts(message, data, secrets, state)

# ================== MAIN PROCESSING FUNCTION ==================
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
            totp = pyotp.TOTP(secrets[i])
            verification_code = totp.now()

            cl.login(username, passwords[i], verification_code=verification_code)

            cookies_dict = cl.get_cookie_dict()
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])

            result = f"{username}|{passwords[i]}|{cookie_str}"
            
            # Mono space এ দেখানোর জন্য
            await message.reply(f"```{result}```", parse_mode="MarkdownV2")
            success_count += 1

        except Exception as e:
            failed_count += 1
            await message.reply(f"❌ Failed → {username}\nError: {str(e)[:250]}")

        await asyncio.sleep(10)  # Instagram block এড়ানোর জন্য

    # Final Summary
    await message.reply(f"""
🏁 **Work Complete!**

✅ SUCCESS: **{success_count}**
❌ FAILED: **{failed_count}**

📊 Total Accounts: {len(usernames)}
""", parse_mode="Markdown")

    await state.clear()

# ================== OWNER COMMANDS ==================
@dp.message(Command("status"))
async def bot_status(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ এই কমান্ড শুধু Owner-এর জন্য।")
    await message.reply("✅ **Bot চালু আছে**\n\n• বন্ধ করতে Render Dashboard থেকে **Suspend** করুন\n• চালু করতে **Resume** করুন")

@dp.message(Command("stopbot"))
async def stop_bot(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ এই কমান্ড শুধু Owner-এর জন্য।")
    
    await message.reply("🛑 Bot polling বন্ধ করা হচ্ছে...\n\nপুরোপুরি বন্ধ করতে Render Dashboard থেকে **Suspend** করুন।")
    await dp.stop_polling()

# ================== RUN THE BOT ==================
async def main():
    print("🚀 Instagram Cookies Bot Started on Render.com")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
