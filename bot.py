import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import openai
import google.generativeai as genai

# လော့ဂ်အား သတ်မှတ်ခြင်း
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ပတ်ဝန်းကျင် ကိန်းရှင်များအား ဖတ်ယူခြင်း
load_dotenv()

# တယ်လီဂရမ်ဘော့ အား သတ်မှတ်ခြင်း
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Google Gemini AI အား သတ်မှတ်ခြင်း
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# OpenAI (ChatGPT) အား သတ်မှတ်ခြင်း
openai.api_key = os.getenv('OPENAI_API_KEY')

# အသုံးပြုသူ မက်ဆေ့ခ်အရေအတွက်
user_message_count = {}

# တစ်ရက်အတွက် အများဆုံး မက်ဆေ့ခ်အရေအတွက်
MAX_MESSAGES_PER_DAY = 30

# ပြောင်းလဲမှု: အကြောင်းပြန်မှုအတွက် စာလုံးအရေအတွက် ကန့်သတ်ချက်
MAX_RESPONSE_LENGTH = 2600

# ပြောင်းလဲမှု: အသုံးပြုသူ input အတွက် စာလုံးအရေအတွက် ကန့်သတ်ချက်
MAX_USER_INPUT_LENGTH = 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("Gemini"), KeyboardButton("ChatGPT")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('ကြိုဆိုပါတယ်! AI မော်ဒယ်တစ်ခုကို ရွေးချယ်ပါ:', reply_markup=reply_markup)
    logger.info(f"အသုံးပြုသူ {update.effective_user.id} က ဘော့ကို စတင်အသုံးပြုပါသည်")

async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("ရာသီဥတု"), KeyboardButton("သတင်း")],
        [KeyboardButton("ဟာသများ"), KeyboardButton("ဗဟုသုတများ")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('လုပ်ဆောင်ချက်တစ်ခုကို ရွေးချယ်ပါ:', reply_markup=reply_markup)

async def gemini_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['ai_model'] = 'gemini'
    await select_action(update, context)
    logger.info(f"အသုံးပြုသူ {update.effective_user.id} က Gemini သို့ ပြောင်းလဲအသုံးပြုပါသည်")

async def chatgpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['ai_model'] = 'chatgpt'
    await select_action(update, context)
    logger.info(f"အသုံးပြုသူ {update.effective_user.id} က ChatGPT သို့ ပြောင်းလဲအသုံးပြုပါသည်")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    current_date = datetime.now().date()

    # နေ့သစ်တစ်ရက်အတွက် မက်ဆေ့ခ်အရေအတွက်အား ပြန်လည်သတ်မှတ်ခြင်း
    if user_id not in user_message_count or user_message_count[user_id]['date'] != current_date:
        user_message_count[user_id] = {'count': 0, 'date': current_date}

    # အသုံးပြုသူသည် နေ့စဉ်ကန့်သတ်ချက်ကို ကျော်လွန်သွားခြင်း ရှိမရှိ စစ်ဆေးခြင်း
    if user_message_count[user_id]['count'] >= MAX_MESSAGES_PER_DAY:
        await update.message.reply_text("ယနေ့အတွက် အများဆုံး မက်ဆေ့ခ်အရေအတွက်သို့ ရောက်ရှိသွားပါပြီ။ နက်ဖြန်တွင် ထပ်မံကြိုးစားကြည့်ပါ။")
        return

    # ပြောင်းလဲမှု: အသုံးပြုသူ input အရှည်ကို စစ်ဆေးခြင်း
    if len(update.message.text) > MAX_USER_INPUT_LENGTH:
        await update.message.reply_text(f"သင့်မက်ဆေ့ခ်သည် စာလုံး {MAX_USER_INPUT_LENGTH} ထက် ပိုရှည်နေပါသည်။ ကျေးဇူးပြု၍ တိုတောင်းသော မက်ဆေ့ခ်ကို ပေးပို့ပါ။")
        return

    # မက်ဆေ့ခ်အရေအတွက်အား တိုးမြှင့်ခြင်း
    user_message_count[user_id]['count'] += 1

    # စာရိုက်နေကြောင်း ပြသခြင်း
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    ai_model = context.user_data.get('ai_model', 'gemini')
    user_message = update.message.text

    if user_message in ["Gemini", "ChatGPT"]:
        if user_message == "Gemini":
            await gemini_command(update, context)
        else:
            await chatgpt_command(update, context)
        return

    if user_message in ["ရာသီဥတု", "သတင်း", "ဟာသများ", "ဗဟုသုတများ"]:
        await handle_action(update, context, user_message)
        return

    if ai_model == 'gemini':
        response = gemini_model.generate_content(user_message)
        reply_text = response.text
    else:  # ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "မြန်မာဘာသာဖြင့် ပြန်လည်တုံ့ပြန်ပါ။"},
                {"role": "user", "content": user_message}
            ]
        )
        reply_text = response.choices[0].message.content

    # ပြောင်းလဲမှု: အကြောင်းပြန်မှုအရှည်ကို ကန့်သတ်ခြင်းနှင့် *** ဖယ်ရှားခြင်း
    reply_text = reply_text.replace('*', '').strip()
    if len(reply_text) > MAX_RESPONSE_LENGTH:
        reply_text = reply_text[:MAX_RESPONSE_LENGTH] + "..."

    # ကူးယူရန်နှင့် မျှဝေရန် ခလုတ်များပါဝင်သည့် inline keyboard အား ဖန်တီးခြင်း
    keyboard = [
        [InlineKeyboardButton("ကူးယူရန်", callback_data="copy"),
         InlineKeyboardButton("မျှဝေရန်", switch_inline_query=reply_text[:100])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(reply_text, reply_markup=reply_markup)
    logger.info(f"အသုံးပြုသူ {user_id} သည် {ai_model} မှ တုံ့ပြန်မှုတစ်ခု ရရှိခဲ့သည်")


async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    ai_model = context.user_data.get('ai_model', 'gemini')
    if ai_model == 'gemini':
        response = gemini_model.generate_content(f"မြန်မာဘာသာဖြင့် {action} အကြောင်း အကျဉ်းချုပ် ပြောပြပါ")
        reply_text = response.text
    else:  # ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "မြန်မာဘာသာဖြင့် ပြန်လည်တုံ့ပြန်ပါ။"},
                {"role": "user", "content": f"{action} အကြောင်း အကျဉ်းချုပ် ပြောပြပါ"}
            ]
        )
        reply_text = response.choices[0].message.content

    # ပြောင်းလဲမှု: အကြောင်းပြန်မှုအရှည်ကို ကန့်သတ်ခြင်းနှင့် *** ဖယ်ရှားခြင်း
    reply_text = reply_text.replace('*', '').strip()
    if len(reply_text) > MAX_RESPONSE_LENGTH:
        reply_text = reply_text[:MAX_RESPONSE_LENGTH] + "..."

    await update.message.reply_text(reply_text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    if query.data == "copy":
        # Display a notification indicating the message has been copied
        await query.answer("Message copied to clipboard", show_alert=False)
    else:
        await query.answer()

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    
    # ပြောင်းလဲမှု: လက်ရှိ နေ့စွဲနှင့် အချိန်ကို သတ်မှတ်ခြင်း
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['current_date'] = current_date ,

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex('^(Gemini|ChatGPT)$'), handle_message))
    application.add_handler(MessageHandler(filters.Regex('^(ရာသီဥတု|သတင်း|ဟာသများ|ဗဟုသုတများ)$'), handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
