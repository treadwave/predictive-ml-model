from dataclasses import dataclass

import httpx

from ..core.circuit_breaker import circuit_breaker


@dataclass
class Alert:
    title: str
    message: str
    severity: str = "info"

emojis = {"info": "ℹ️", "warning": "⚠️", "critical":"🚨"}

def format_message(alert: Alert) -> str:
    emoji = emojis.get(alert.severity, "ℹ️")

    return (f"{emoji} {alert.title} \n"
            f"{alert.message}\n")

async def send_telegram_alert(bot_token: str, chat_id: str, alert: Alert):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": format_message(alert)
    }

    try:
        async with httpx.AsyncClient() as client:
            if circuit_breaker.allow_request():
                r = await client.post(url, json=payload, timeout=3)
                r.raise_for_status()
                if r.status_code==200:
                    print(f"SENT {alert.severity.upper()} {alert.title}")
                    circuit_breaker.set_closed()
            else:
                pass

    except httpx.HTTPStatusError as e:
        if e.response.is_client_error and e.response.status_code != 429:
            print(e)
            circuit_breaker.set_closed()

        elif e.response.is_server_error or e.response.status_code == 429:
            circuit_breaker.check_half_open()
            circuit_breaker.errors_counter()
            print(e)
        else:
            print(e)

    except httpx.TransportError as e:
            circuit_breaker.check_half_open()
            circuit_breaker.errors_counter()
            print(e)





