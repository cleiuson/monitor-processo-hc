import imaplib
import email
import sqlite3
import requests
import os
from email.header import decode_header

# --- Configurações ---
IMAP_HOST = "imap.gmail.com"
IMAP_USER = os.environ["drastic-lazy-karma@duck.com"]
IMAP_PASS = os.environ["4B7$4^np*WMjc1$rMdbxWs40"]  # use uma "senha de app", não a senha normal
TELEGRAM_TOKEN = os.environ["9085887506:AAGT_a1yvmJERbgCO2dgByDg1GBuoSKcckw"]
TELEGRAM_CHAT_ID = os.environ["673844298"]

# Filtros: ajuste conforme os remetentes reais dos e-mails de alerta
REMETENTES_ALVO = ["stj.jus.br", "tjce.jus.br"]
TERMOS_ALVO = ["1.084.875", "2026/0115963-2", "0621650-07.2026.8.06.0000",
               "0272594-80.2023.8.06.0001", "0204967-41.2023.8.06.0298"]

DB_PATH = "enviados.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS enviados (msg_id TEXT PRIMARY KEY)")
    con.commit()
    return con

def ja_enviado(con, msg_id):
    return con.execute("SELECT 1 FROM enviados WHERE msg_id=?", (msg_id,)).fetchone()

def marcar_enviado(con, msg_id):
    con.execute("INSERT INTO enviados VALUES (?)", (msg_id,))
    con.commit()

def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "HTML"})

def decode_str(s):
    partes = decode_header(s)
    return "".join(
        p.decode(enc or "utf-8") if isinstance(p, bytes) else p
        for p, enc in partes
    )

def corpo_texto(msg):
    if msg.is_multipart():
        for parte in msg.walk():
            if parte.get_content_type() == "text/plain":
                return parte.get_payload(decode=True).decode(errors="ignore")
        return ""
    return msg.get_payload(decode=True).decode(errors="ignore")

def main():
    con = init_db()
    imap = imaplib.IMAP4_SSL(IMAP_HOST)
    imap.login(IMAP_USER, IMAP_PASS)
    imap.select("inbox")

    # busca e-mails não lidos (ou ajuste para SINCE uma data)
    status, dados = imap.search(None, "UNSEEN")
    ids = dados[0].split()

    for msg_id in ids:
        status, msg_dados = imap.fetch(msg_id, "(RFC822)")
        msg = email.message_from_bytes(msg_dados[0][1])

        remetente = decode_str(msg.get("From", ""))
        assunto = decode_str(msg.get("Subject", ""))
        corpo = corpo_texto(msg)
        texto_completo = f"{assunto}\n{corpo}"

        if not any(r in remetente for r in REMETENTES_ALVO):
            continue
        if not any(t in texto_completo for t in TERMOS_ALVO):
            continue

        chave = msg.get("Message-ID", msg_id.decode())
        if ja_enviado(con, chave):
            continue

        resumo = corpo.strip()[:1000]
        enviar_telegram(f"<b>Atualização de processo</b>\n\n<b>{assunto}</b>\n\n{resumo}")
        marcar_enviado(con, chave)

    imap.logout()

if __name__ == "__main__":
    main()
