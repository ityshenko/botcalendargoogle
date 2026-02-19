import os, json, asyncio, datetime, dateparser
from aiogram import Bot
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TG_TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
GCAL_TOKEN_JSON = os.getenv('GCAL_TOKEN')

def get_gcal():
    creds = Credentials.from_authorized_user_info(json.loads(GCAL_TOKEN_JSON), ['https://www.googleapis.com/auth/calendar'])
    return build('calendar', 'v3', credentials=creds)

def parse_dt(t):
    now = datetime.datetime.now()
    p = dateparser.parse(t, settings={"PREFER_DATES_FROM":"future", "RELATIVE_BASE":now})
    if p and p.hour==0 and p.minute==0: p = p.replace(hour=9, minute=0)
    return p or (now + datetime.timedelta(days=1)).replace(hour=9, minute=0)

async def send(text):
    if TG_TOKEN and CHAT_ID:
        async with Bot(token=TG_TOKEN) as bot:
            await bot.send_message(CHAT_ID, text)

async def main():
    trigger = os.getenv('TRIGGER')
    if trigger == 'schedule':
        service = get_gcal()
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        events = service.events().list(calendarId='primary', timeMin=f'{tomorrow}T00:00:00Z', timeMax=f'{tomorrow}T23:59:59Z', singleEvents=True, orderBy='startTime').execute().get('items', [])  msg = f"📅 Планы на завтра:\n\n"
        if events:
            for e in events:
                start = e['start'].get('dateTime', e['start'].get('date'))[11:16]
                msg += f"⏰ {start} — {e['summary']}\n"
        else:
            msg += "✨ Пусто"
        await send(msg)
        return
    if trigger == 'workflow_dispatch':
        text = os.getenv('MSG')
        try:
            et = parse_dt(text)
            service = get_gcal()
            event = {
                'summary': text,
                'start': {'dateTime': et.isoformat(), 'timeZone': 'Europe/Moscow'},
                'end': {'dateTime': (et + datetime.timedelta(hours=1)).isoformat(), 'timeZone': 'Europe/Moscow'},
                'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 1440}, {'method': 'popup', 'minutes': 60}]},
            }
            service.events().insert(calendarId='primary', body=event).execute()
            await send(f"✅ Записал: {text}\n📅 {et.strftime('%d.%m %H:%M')}\n🔔 Google напомнит!")
        except Exception as e:
            await send(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
