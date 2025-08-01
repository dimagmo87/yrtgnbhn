from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import sqlite3
import re

# Подключение к базе данных SQLite и создание таблицы cash при необходимости
conn = sqlite3.connect('cashbox.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS cash (
    date TEXT PRIMARY KEY,
    amount REAL
)
''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Привет! Отправь дату и сумму в формате "YYYY-MM-DD сумма",\n'
        'например: 2024-04-25 1500\n\n'
        'Команды:\n'
        '/month YYYY-MM — посчитать и показать кассу за месяц\n'
        '/delete_month YYYY-MM — удалить записи за месяц\n'
        '/sum_range YYYY-MM-DD YYYY-MM-DD — посчитать и показать кассу за период'
    )

async def save_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.match(r'^(\d{4}-\d{2}-\d{2})\s+(\d+(\.\d+)?)$', text)
    if not match:
        await update.message.reply_text('Неправильный формат. Используйте: YYYY-MM-DD сумма')
        return
    date, amount = match.group(1), float(match.group(2))
    cursor.execute('REPLACE INTO cash (date, amount) VALUES (?, ?)', (date, amount))
    conn.commit()
    await update.message.reply_text(f'Касса на {date} сохранена: {amount}')

async def month_sum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or not re.match(r'^\d{4}-\d{2}$', context.args[0]):
        await update.message.reply_text('Используйте: /month YYYY-MM')
        return
    month = context.args[0]
    cursor.execute('SELECT date, amount FROM cash WHERE date LIKE ? ORDER BY date', (f'{month}-%',))
    records = cursor.fetchall()
    if not records:
        await update.message.reply_text(f'Записей за {month} не найдено.')
        return
    lines = [f"{date}: {amount}" for date, amount in records]
    total = sum(amount for _, amount in records)
    message = "Касса за месяц:\n" + "\n".join(lines) + f"\n\nИтого: {total}"
    await update.message.reply_text(message)

async def delete_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or not re.match(r'^\d{4}-\d{2}$', context.args[0]):
        await update.message.reply_text('Используйте: /delete_month YYYY-MM')
        return
    month = context.args[0]
    cursor.execute('SELECT COUNT(*) FROM cash WHERE date LIKE ?', (f'{month}-%',))
    count = cursor.fetchone()[0]
    if count == 0:
        await update.message.reply_text(f'За месяц {month} нет записей для удаления.')
        return
    cursor.execute('DELETE FROM cash WHERE date LIKE ?', (f'{month}-%',))
    conn.commit()
    await update.message.reply_text(f'Удалено {count} записей за месяц {month}.')

async def sum_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text('Используйте: /sum_range YYYY-MM-DD YYYY-MM-DD')
        return
    start_date, end_date = context.args
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
        await update.message.reply_text('Даты должны быть в формате YYYY-MM-DD')
        return
    if start_date > end_date:
        await update.message.reply_text('Начальная дата должна быть меньше или равна конечной.')
        return
    cursor.execute('SELECT date, amount FROM cash WHERE date BETWEEN ? AND ? ORDER BY date', (start_date, end_date))
    records = cursor.fetchall()
    if not records:
        await update.message.reply_text(f'Записей за период с {start_date} по {end_date} не найдено.')
        return
    lines = [f"{date}: {amount}" for date, amount in records]
    total = sum(amount for _, amount in records)
    message = f"Касса за период с {start_date} по {end_date}:\n" + "\n".join(lines) + f"\n\nИтого: {total}"
    await update.message.reply_text(message)

def main():
    app = ApplicationBuilder().token("8004897703:AAEuK06Z6xxqP97-2Y-1h6V7IdsUASy6LYg").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("month", month_sum))
    app.add_handler(CommandHandler("delete_month", delete_month))
    app.add_handler(CommandHandler("sum_range", sum_range))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), save_cash))

    print("Бот запущен...")
    app.run_polling()

if __name__ == '__main__':
    main()