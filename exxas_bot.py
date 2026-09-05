
import os
import logging
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from google import genai
from google.genai import types

# Logging aktivieren
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Gemini API-Schlüssel direkt setzen und Client initialisieren
os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6LhTujx6JTqUyuEcfecLDWa4KwM_5CgA7IYxy-54Fd6-Q"
gemini_client = genai.Client()

# Gmail SMTP Zugangsdaten
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "graf89.rg@gmail.com"
SENDER_PASSWORD = "xjvdvanyleoregur"
RECEIVER_EMAIL = "rechnungen@fairservice.ch"

# --- E-MAIL VERSAND ÜBER GMAIL ---
def exxas_serviceauftrag_per_mail_senden(
    kunden_name: str, 
    maschinen_typ: str, 
    arbeitsbeschreibung: str, 
    material: str, 
    arbeitsstunden: float
) -> str:
    """Sendet den Servicebericht formatiert als E-Mail via Gmail SMTP an rechnungen@fairservice.ch."""
    try:
        titel_text = f"Servicebericht: {kunden_name} - {maschinen_typ} ({arbeitsstunden}h)"
        
        mail_inhalt = f"""Neuer Servicebericht aus Telegram-Bot:

Kunde: {kunden_name}
Maschinentyp: {maschinen_typ}
Arbeitsstunden: {arbeitsstunden} h

Arbeitsbeschreibung:
{arbeitsbeschreibung}

Verwendetes Material / Ersatzteile:
{material}
"""

        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = titel_text
        msg.attach(MIMEText(mail_inhalt, "plain", "utf-8"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        
        return f"Erfolg! Servicebericht für {kunden_name} ({maschinen_typ}) wurde per E-Mail an rechnungen@fairservice.ch gesendet."
        
    except Exception as e:
        return f"Fehler beim E-Mail-Versand über Gmail: {str(e)}"

tools = [exxas_serviceauftrag_per_mail_senden]

system_instruction = (
    "Du bist ein intelligenter Assistent für den CNC-Service (FairService GmbH). "
    "Deine Aufgabe ist es, diktierte Serviceberichte von Technikern zu analysieren (egal ob Text oder transkribierte Sprache). "
    "Extrahiere die folgenden Informationen: "
    "1. Kundenname, 2. Maschinentyp (z.B. HOLZ-HER, MAKA, Biesse, Caelus), "
    "3. Beschreibung der geleisteten Arbeit, 4. Verwendetes Material/Ersatzteile, "
    "5. Arbeitsstunden (als Dezimalzahl). "
    "Sobald du diese Infos hast, rufe sofort die Funktion 'exxas_serviceauftrag_per_mail_senden' auf "
    "und gib EXAKT das zurück, was die Funktion as Ergebnis liefert."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Servus! Schick mir deinen Servicebericht als Sprachnachricht oder Text, ich maile ihn direkt an rechnungen@fairservice.ch.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.voice:
            await update.message.reply_text("Höre Sprachnachricht ab und verarbeite den Servicebericht...")
            voice_file = await update.message.voice.get_file()
            
            # Temporäre Datei im System-Temp-Ordner (garantiert Schreibrechte)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_voice:
                voice_path = temp_voice.name
                
            await voice_file.download_to_drive(voice_path)
            
            with open(voice_path, "rb") as f:
                audio_bytes = f.read()
                
            prompt_content = [
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
                "Analysiere diesen gesprochenen Servicebericht und versende ihn."
            ]
            
            if os.path.exists(voice_path):
                os.remove(voice_path)
                
        elif update.message.text:
            await update.message.reply_text("Verarbeite Servicebericht...")
            prompt_content = update.message.text
        else:
            return

        chat = gemini_client.chats.create(
            model="gemini-3.6-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools,
                temperature=0.1,
            )
        )
        
        response = chat.send_message(prompt_content)
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("Bericht wurde verarbeitet und versendet.")
            
    except Exception as e:
        await update.message.reply_text(f"Fehler bei der Verarbeitung: {str(e)}")

if __name__ == '__main__':
    TELEGRAM_TOKEN = "8773281295:AAGSsb81-w83f_gMOBt4ShBRzf6D2yyqtcA"
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_message))
    
    print("Bot gestartet. Warte auf Nachrichten...")
    app.run_polling()