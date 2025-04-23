import telebot
from telebot import types
from datetime import datetime
import json
import os
from persiantools.jdatetime import JalaliDate
from fpdf import FPDF

TOKEN = "7657768228:AAEmyjSKBwdpy_i7dDVx0McyW1Eaazc0n30"
bot = telebot.TeleBot(TOKEN)
data_file = "data.json"

# بارگذاری و ذخیره‌سازی اطلاعات
def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# شروع
@bot.message_handler(commands=['start'])
def start(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ ثبت ساعت و مسیر", "📊 گزارش کامل امروز")
    markup.add("🧮 محاسبه کل ماه", "📄 تولید PDF پایان ماه")
    bot.send_message(msg.chat.id, "به ربات محاسبه هزینه رانندگان خوش آمدید! یکی از گزینه‌ها را انتخاب کنید:", reply_markup=markup)

# ذخیره ورودی مرحله‌ای
user_inputs = {}

@bot.message_handler(func=lambda m: m.text == "➕ ثبت ساعت و مسیر")
def ask_entry_time(msg):
    user_inputs[msg.chat.id] = {}
    markup = types.InlineKeyboardMarkup()
    for h in range(6, 20):
        markup.add(types.InlineKeyboardButton(f"{h:02d}", callback_data=f"ورود:{h}"))
    bot.send_message(msg.chat.id, "ساعت ورود را انتخاب کن:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ورود:"))
def ask_entry_minute(call):
    hour = int(call.data.split(":")[1])
    user_inputs[call.message.chat.id]["entry_hour"] = hour
    markup = types.InlineKeyboardMarkup()
    for m in [0, 15, 30, 45]:
        markup.add(types.InlineKeyboardButton(f"{m:02d}", callback_data=f"دقیقه_ورود:{m}"))
    bot.edit_message_text("حالا دقیقه ورود را انتخاب کن:", call.message.chat.id, call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("دقیقه_ورود:"))
def ask_exit_hour(call):
    minute = int(call.data.split(":")[1])
    user_inputs[call.message.chat.id]["entry_minute"] = minute
    markup = types.InlineKeyboardMarkup()
    for h in range(12, 24):
        markup.add(types.InlineKeyboardButton(f"{h:02d}", callback_data=f"خروج:{h}"))
    bot.edit_message_text("ساعت خروج را انتخاب کن:", call.message.chat.id, call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("خروج:"))
def ask_exit_minute(call):
    hour = int(call.data.split(":")[1])
    user_inputs[call.message.chat.id]["exit_hour"] = hour
    markup = types.InlineKeyboardMarkup()
    for m in [0, 15, 30, 45]:
        markup.add(types.InlineKeyboardButton(f"{m:02d}", callback_data=f"دقیقه_خروج:{m}"))
    bot.edit_message_text("حالا دقیقه خروج را انتخاب کن:", call.message.chat.id, call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("دقیقه_خروج:"))
def ask_kilometer(call):
    minute = int(call.data.split(":")[1])
    user_inputs[call.message.chat.id]["exit_minute"] = minute
    bot.send_message(call.message.chat.id, "کیلومتر پیموده شده را وارد کن:")

@bot.message_handler(func=lambda m: m.chat.id in user_inputs and "exit_minute" in user_inputs[m.chat.id] and "km" not in user_inputs[m.chat.id])
def ask_route(msg):
    try:
        km = int(msg.text)
        user_inputs[msg.chat.id]["km"] = km
        bot.send_message(msg.chat.id, "مسیر مأموریت را وارد کن:")
    except:
        bot.send_message(msg.chat.id, "عدد معتبر وارد کن!")

@bot.message_handler(func=lambda m: m.chat.id in user_inputs and "km" in user_inputs[m.chat.id] and "route" not in user_inputs[m.chat.id])
def ask_partner(msg):
    user_inputs[msg.chat.id]["route"] = msg.text
    bot.send_message(msg.chat.id, "نام همراه یا همراهان را وارد کن:")

@bot.message_handler(func=lambda m: m.chat.id in user_inputs and "route" in user_inputs[m.chat.id] and "partner" not in user_inputs[m.chat.id])
def save_final_data(msg):
    user_inputs[msg.chat.id]["partner"] = msg.text

    entry = datetime(2000, 1, 1, user_inputs[msg.chat.id]["entry_hour"], user_inputs[msg.chat.id]["entry_minute"])
    exit_ = datetime(2000, 1, 1, user_inputs[msg.chat.id]["exit_hour"], user_inputs[msg.chat.id]["exit_minute"])
    hours = (exit_ - entry).seconds / 3600
    km = user_inputs[msg.chat.id]["km"]
    cost_hour = hours * 40000
    cost_km = km * 3000
    total = int(cost_hour + cost_km)
    insurance = int(total * 0.07)
    final = total - insurance

    today = JalaliDate.today().strftime("%Y-%m-%d")
    user_id = str(msg.from_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {}
    data[user_id][today] = {
        "ورود": entry.strftime("%H:%M"),
        "خروج": exit_.strftime("%H:%M"),
        "ساعت": round(hours, 1),
        "کیلومتر": km,
        "مسیر": user_inputs[msg.chat.id]["route"],
        "همراهان": user_inputs[msg.chat.id]["partner"],
        "هزینه": total,
        "حق بیمه": insurance,
        "خالص پرداختی": final
    }
    save_data(data)

    bot.send_message(msg.chat.id, f"""✅ اطلاعات امروز ذخیره شد:
    
📅 تاریخ: {today}
🕒 ساعات کاری: {round(hours,1)} ساعت
🚗 کیلومتر: {km}
🛣 مسیر: {user_inputs[msg.chat.id]["route"]}
‍‍‍‍‍‍‍‍‍👥 همراهان: {user_inputs[msg.chat.id]["partner"]}

💰 مبلغ ناخالص: {total:,} تومان
➖ حق بیمه (۷٪): {insurance:,} تومان
✅ خالص پرداختی: {final:,} تومان
""")

    del user_inputs[msg.chat.id]

# گزارش روزانه
@bot.message_handler(func=lambda m: m.text == "📊 گزارش کامل امروز")
def daily_report(msg):
    today = JalaliDate.today().strftime("%Y-%m-%d")
    user_id = str(msg.from_user.id)
    data = load_data()
    if user_id in data and today in data[user_id]:
        entry_data = data[user_id][today]
        bot.send_message(msg.chat.id, f"""
📅 تاریخ: {today}
🕒 ساعات کاری: {entry_data['ساعت']} ساعت
🚗 کیلومتر: {entry_data['کیلومتر']}
🛣 مسیر: {entry_data['مسیر']}
👥 همراهان: {entry_data['همراهان']}
💰 مبلغ ناخالص: {entry_data['هزینه']:,} تومان
➖ حق بیمه (۷٪): {entry_data['حق بیمه']:,} تومان
✅ خالص پرداختی: {entry_data['خالص پرداختی']:,} تومان
""")
    else:
        bot.send_message(msg.chat.id, "اطلاعاتی برای امروز ثبت نشده است.")

# گزارش ماهانه و تولید PDF
@bot.message_handler(func=lambda m: m.text == "📄 تولید PDF پایان ماه")
def generate_monthly_report(msg):
    user_id = str(msg.from_user.id)
    data = load_data()
    if user_id in data:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(200, 10, txt="گزارش ماهانه راننده", ln=True, align='C')
        pdf.ln(10)

        total_month = 0
        insurance_month = 0
        final_month = 0
        for date, entry in data[user_id].items():
            pdf.cell(200, 10, txt=f"تاریخ: {date} | ساعات کاری: {entry['ساعت']} ساعت | مبلغ ناخالص: {entry['هزینه']:,} تومان | خالص پرداختی: {entry['خالص پرداختی']:,} تومان", ln=True)

            total_month += entry["هزینه"]
            insurance_month += entry["حق بیمه"]
            final_month += entry["خالص پرداختی"]

        pdf.ln(10)
        pdf.cell(200, 10, txt=f"مجموع کل ماه: {total_month:,} تومان", ln=True)
        pdf.cell(200, 10, txt=f"حق بیمه (۷٪): {insurance_month:,} تومان", ln=True)
        pdf.cell(200, 10, txt=f"خالص پرداختی کل ماه: {final_month:,} تومان", ln=True)

        pdf_output_path = f"monthly_report_{user_id}.pdf"
        pdf.output(pdf_output_path)

        bot.send_document(msg.chat.id, open(pdf_output_path, "rb"))
    else:
        bot.send_message(msg.chat.id, "اطلاعاتی برای این ماه ثبت نشده است.")

# اجرای ربات
bot.polling()
