import os

from advisor.alerts.discord import send_discord_alert

if __name__ == "__main__":
    send_discord_alert(
        os.environ["DISCORD_WEBHOOK_URL"],
        "테스트 메시지 — 폰 디스코드 알림 확인용입니다. 이 메시지가 보이면 알림 설정이 정상입니다.",
    )
