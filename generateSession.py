"""
生成熱圖會話字符串的小腳本
"""
from pyrogram import Client

try:
    print(
        "請確認您有 API ID 和API HASH，如果沒有，請到 my.telegram.org 並申請。\n\n"
    )
    API_ID = input("輸入您的 API ID -")
    API_HASH = input("輸入您的 API HASH -")

    print(
        "\n\n現在它會要求您輸入您的電話號碼（國際格式），然後按照步驟操作"
    )

    client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)

    with client:
        session = client.export_session_string()
        print(
            "\n完成!您的會話字符串將保存在您保存的消息中！ 不要與其他任何人分享。"
        )
        client.send_message(
            "me",
            f"您的會話字符串：\n\n`{session}`\n\n@vcplayerbot | [SkTechHub 產品](https://t.me/sktechhub)",
        )
except Exception as ex:
    print(f"\n發生了一些錯誤： {ex}")
