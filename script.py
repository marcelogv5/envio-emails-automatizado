import base64
import json
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def load_credentials():
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
    token_json = os.environ.get("TOKEN_JSON")
    creds_data = json.loads(base64.b64decode(credentials_json))
    token_data = json.loads(base64.b64decode(token_json))
    creds = Credentials.from_authorized_user_info(info=token_data)
    return creds

def enviar_email(service, destinatario, assunto, corpo):
    message = MIMEText(corpo)
    message['to'] = destinatario
    message['subject'] = assunto
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={'raw': raw}).execute()

def deve_enviar(hoje, regra):
    semana = ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "DOMINGO"]
    dia_semana = semana[hoje.weekday()]
    r = regra.upper()
    if r == "TODOS OS DIAS":
        return hoje.weekday() < 5  # dias úteis
    if dia_semana in r:
        return True
    if "DIA 12 OU ÚTIL" in r:
        if hoje.day == 12:
            return True
        for dia in range(hoje.day, 13):
            d = hoje.replace(day=dia)
            if d.weekday() < 5:
                return hoje.day == dia
    return False

def main():
    creds = load_credentials()
    service = build('gmail', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)

    PLANILHA_ID = os.environ.get("PLANILHA_ID")
    RANGE = "Tarefas!A1:Z"
    result = sheets_service.spreadsheets().values().get(spreadsheetId=PLANILHA_ID, range=RANGE).execute()
    valores = result.get('values', [])
    if not valores or len(valores) < 2:
        print("Planilha vazia ou sem dados.")
        return

    header = valores[0]
    dados = valores[1:]
    idx = {col: header.index(col) for col in ["DESTINATÁRIO", "ASSUNTO", "CORPO DO E-MAIL", "DIAS", "Horário"]}

    agora = datetime.utcnow() - timedelta(hours=3)  # Ajuste para horário de Brasília
    hora_atual = agora.hour + agora.minute / 60

    for linha in dados:
        try:
            regra = linha[idx["DIAS"]]
            if not deve_enviar(agora, regra):
                continue

            horario = linha[idx["Horário"]]
            if ":" not in horario:
                continue
            h, m = map(int, horario.strip().split(":"))
            hora_regra = h + m / 60
            if abs(hora_atual - hora_regra) > 0.25:  # tolerância de 15 minutos
                continue

            destinatario = linha[idx["DESTINATÁRIO"]]
            assunto = linha[idx["ASSUNTO"]]
            corpo = linha[idx["CORPO DO E-MAIL"]]

            enviar_email(service, destinatario, assunto, corpo)
            print(f"E-mail enviado para: {destinatario}")

        except Exception as e:
            print(f"Erro ao processar linha: {e}")

if __name__ == "__main__":
    main()
