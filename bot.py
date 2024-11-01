import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import openai
import google.generativeai as genai

import re

from telegram.ext import ContextTypes
from telegram import Update
from telegram.constants import ParseMode
from urllib.parse import quote

import asyncio
from telegram.constants import ChatAction

# လော့ဂ်အား သတ်မှတ်ခြင်း
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ပတ်ဝန်းကျင် ကိန်းရှင်များအား ဖတ်ယူခြင်း
load_dotenv()

# တယ်လီဂရမ်ဘော့ အား သတ်မှတ်ခြင်း
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# OpenAI (ChatGPT) အား သတ်မှတ်ခြင်း
openai.api_key = os.getenv('OPENAI_API_KEY')

# Google Gemini AI အား သတ်မှတ်ခြင်း
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# အသုံးပြုသူ မက်ဆေ့ခ်အရေအတွက်
user_message_count = {}

# တစ်ရက်အတွက် အများဆုံး မက်ဆေ့ခ်အရေအတွက်
MAX_MESSAGES_PER_DAY = 30

# အကြောင်းပြန်မှုအတွက် စာလုံးအရေအတွက် ကန့်သတ်ချက်
MAX_RESPONSE_LENGTH = 2600

# အသုံးပြုသူ input အတွက် စာလုံးအရေအတွက် ကန့်သတ်ချက်
MAX_USER_INPUT_LENGTH = 200

# start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # AI ရွေးချယ်ရန် inline keyboard ဖန်တီးခြင်း
    keyboard = [
        [InlineKeyboardButton("Gemini", callback_data="select_gemini"),
         InlineKeyboardButton("ChatGPT", callback_data="select_chatgpt")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # ကြိုဆိုစကားနှင့် AI ရွေးချယ်ရန် ညွှန်ကြားချက်
    welcome_message = (
        "မင်္ဂလာပါ၊ ကျွန်တော်က ASP ဖန်တီးပေးထားတဲ့ Tg Chat AI ဖြစ်ပါတယ်။\n"
        "အောက်မှာ ပေါ်လာတဲ့ AI ထဲက ဘယ် AI နဲ့ ဖြေစေချင်လဲ ရွေးပေးပါ။"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    logger.info(f"အသုံးပြုသူ {update.effective_user.id} က ဘော့ကို စတင်အသုံးပြုပါသည်")

# AI model ရွေးချယ်မှုကို ကိုင်တွယ်သည့် function
async def select_ai_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "select_gemini":
        context.user_data['ai_model'] = 'gemini'
        await query.edit_message_text("Gemini ကို ရွေးချယ်ပြီးပါပြီ။ မေးခွန်းမေးနိုင်ပါပြီ။")
    elif query.data == "select_chatgpt":
        context.user_data['ai_model'] = 'chatgpt'
        await query.edit_message_text("ChatGPT ကို ရွေးချယ်ပြီးပါပြီ။ မေးခွန်းမေးနိုင်ပါပြီ။")

# message handler
async def send_typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    while True:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(5)  # 5 စက္ကန့်တိုင်း typing action ကို ပြန်ပို့ပါမယ်

import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction, ParseMode

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_date = datetime.now().date()

    if user_id not in user_message_count or user_message_count[user_id]['date'] != current_date:
        user_message_count[user_id] = {'count': 0, 'date': current_date}

    if user_message_count[user_id]['count'] >= MAX_MESSAGES_PER_DAY:
        await update.message.reply_text("ယနေ့အတွက် အများဆုံး မက်ဆေ့ခ်အရေအတွက်သို့ ရောက်ရှိသွားပါပြီ။ နက်ဖြန်တွင် ထပ်မံကြိုးစားကြည့်ပါ။")
        return

    if len(update.message.text) > MAX_USER_INPUT_LENGTH:
        await update.message.reply_text(f"သင့်မက်ဆေ့ခ်သည် စာလုံး {MAX_USER_INPUT_LENGTH} ထက် ပိုရှည်နေပါသည်။ ကျေးဇူးပြု၍ တိုတောင်းသော မက်ဆေ့ခ်ကို ပေးပို့ပါ။")
        return

    user_message_count[user_id]['count'] += 1

    thinking_message = await update.message.reply_text("သင့်မေးခွန်းကို စဉ်းစားနေပါသည်...")

    ai_model = context.user_data.get('ai_model', 'chatgpt')
    user_message = update.message.text

    try:
        # စာရိုက်နေကြောင်း ပြသခြင်း
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        if ai_model == 'gemini':
            response = gemini_model.generate_content(user_message)
            reply_text = response.text
        else:  # ChatGPT
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "မြန်မာဘာသာဖြင့် ပြန်လည်တုံ့ပြန်ပါ။ အရေးကြီးသော အချက်များကို **bold** ဖြင့် ဖော်ပြပါ။ code များကို `inline code` သို့မဟုတ် ```code block``` ဖြင့် ဖော်ပြပါ။"},
                    {"role": "user", "content": user_message}
                ]
            )
            reply_text = response.choices[0].message.content

        reply_text = re.sub(r'```(\w+)?\n(.*?)\n```', lambda m: f'```{m.group(1) or ""}\n{m.group(2)}\n```', reply_text, flags=re.DOTALL)
        reply_text = reply_text[:MAX_RESPONSE_LENGTH]

        remaining_messages = MAX_MESSAGES_PER_DAY - user_message_count[user_id]['count']

        keyboard = [
            [InlineKeyboardButton("📋 ကူးယူရန်", callback_data="copy"),
             InlineKeyboardButton("🔗 မျှဝေရန်", callback_data="share")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        formatted_reply = (
            f"{reply_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🗨️ ကျန်ရှိသော မက်ဆေ့ခ်: {remaining_messages}"
        )

        await thinking_message.delete()
        await update.message.reply_text(formatted_reply, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"အသုံးပြုသူ {user_id} သည် {ai_model} မှ တုံ့ပြန်မှုတစ်ခု ရရှိခဲ့သည်")

    except Exception as e:
        await thinking_message.delete()
        logger.error(f"Error: {str(e)}")
        formatted_reply = "ဝမ်းနည်းပါတယ်။ AI နှင့် ချိတ်ဆက်ရာတွင် ပြဿနာ ဖြစ်ပေါ်နေပါသည်။ ခဏလေး နောက်မှ ထပ်စမ်းကြည့်ပါ။"
        await update.message.reply_text(formatted_reply)

    finally:
        # စာရိုက်နေကြောင်း ပြသခြင်းကို ရပ်တန့်ခြင်း
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

# Copy လုပ်ဆောင်ချက်အတွက် callback function
async def copy_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("စာသားကို ကူးယူပြီးပါပြီ။")

# Share လုပ်ဆောင်ချက်အတွက် callback function
async def share_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    message_text = query.message.text.split("\n\n")[0]  # AI ရဲ့ အဖြေကိုပဲ ယူပါမယ်
    
    # စာသားကို URL encoding လုပ်ပါမယ်
    encoded_text = quote(message_text)
    
    # Telegram share URL ဖန်တီးပါမယ်
    share_url = f"https://t.me/share/url?url={encoded_text}"
    
    share_message = (
        "အောက်ပါ link ကို နှိပ်၍ Telegram မှ တစ်ဆင့် မျှဝေနိုင်ပါသည်။"
    )
    
    # Share လုပ်ရန် button ဖန်တီးပါမယ်
    keyboard = [[InlineKeyboardButton("Telegram မှ Share လုပ်ရန်", url=share_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.answer("မျှဝေနိုင်ပါပြီ။")
    await query.edit_message_text(text=share_message, reply_markup=reply_markup)

# အဓိက function
def main() -> None:
    # လက်ရှိ နေ့စွဲနှင့် အချိန်ကို သတ်မှတ်ခြင်း
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['current_date'] = current_date

    # Handler များအား ထည့်သွင်းခြင်း
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(select_ai_model, pattern="^select_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(copy_text, pattern="^copy$"))
    application.add_handler(CallbackQueryHandler(share_text, pattern="^share$"))

    # ဘော့အား စတင်လည်ပတ်စေခြင်း
    application.run_polling()

if __name__ == '__main__':
    main()
