import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

DB_PATH = "hotspot.db"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "VOTRE_TOKEN_ICI")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        username = context.args[0]
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT daily_bytes, monthly_bytes, status FROM clients WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        
        if row:
            daily = round(row[0] / 1073741824, 2)
            monthly = round(row[1] / 1073741824, 2)
            status = "🟢 Actif" if row[2] == "active" else "🔴 Coupé"
            msg = (
                f"📊 <b>Compte : {username}</b>\n\n"
                f"📅 Aujourd'hui : <b>{daily} Go</b> / 30 Go\n"
                f"📆 Ce mois : <b>{monthly} Go</b>\n"
                f"⏰ Coupure auto à 00h00\n\n"
                f"Statut : {status}"
            )
        else:
            msg = "❌ Compte introuvable."
    else:
        msg = "👋 Bienvenue ! Cliquez depuis votre portail WiFi pour voir vos stats."
    
    await update.message.reply_text(msg, parse_mode="HTML")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
