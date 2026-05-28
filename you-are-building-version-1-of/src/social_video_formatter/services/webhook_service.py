import requests


class WebhookNotifier:
    def send(self, url: str, payload: dict) -> tuple[str, int | None]:
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return ("sent" if resp.ok else "failed", resp.status_code)
        except Exception:
            return ("failed", None)
