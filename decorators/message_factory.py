from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from utils import logInfo, logException, config, mongoDBClient


def getMessage(message, action, errorMsg=""):
    try:
        extra_options = {
            "-video": "在視頻聊天中串流傳輸視頻文件。",
            "-audio": "僅串流傳輸音頻。",
            "-repeat": "以重複模式播放歌曲/視頻。",
            "-res720": "以提供的質量/分辨率流式傳輸音頻/視頻。",
            "-lipsync": "如果音頻與視頻不同步，請使用此選項",
        }
        if action == "start-private-message":
            send_message = f"**Hi 🎵 {message.chat.first_name if hasattr(message.chat, 'first_name') else 'User'}**"
            send_message = (
                send_message
                + f"\n\n**[語音聊天音樂播放器]({config.get('BOT_URL')})** 是一個[SkTechHub 產品]({config.get('PARENT_URL')})。"
            )
            send_message = (
                send_message
                + f"\n__通過 Telegram 引入的**新語音聊天**在您的群組中盡可能簡單地播放音樂/視頻。__"
            )
            send_message = (
                send_message
                + f"\n\n**所以為什麼要等待🌀 將機器人添加到組中並開始🎧**\n\n**源代碼：** [存儲庫]({config.get('GITHUB_REPO')})"
            )
            return send_message, getReplyKeyBoard(message, action)
        elif action == "start-group-message":
            send_message = f"**感謝您添加[語音聊天音樂播放器]({config.get('BOT_URL')})🎵**"
            send_message = (
                send_message
                + f"\n\n**[語音聊天音樂播放器]({config.get('BOT_URL')})** 是一個[SkTechHub 產品]({config.get('PARENT_URL')})。"
            )
            send_message = (
                send_message
                + f"\n__通過 Telegram 引入的**新語音聊天**在您的群組中盡可能簡單地播放音樂/視頻。__"
            )
            if not mongoDBClient.client:
                send_message = (
                    send_message
                    + f"\n\n**開始之前的一些事情**\n`• 確保機器人是該群組中的管理員`\n`• 確保您在 env 中提供了 USERBOT_SESSION 值`"
                )
            else:
                send_message = (
                    send_message
                    + f"\n\n**開始之前的一些事情**\n`• 確保機器人是該群組中的管理員`\n`• 確保群組管理員已授權給機器人`"
                )
            send_message = send_message + f"\n\n發送 /help 以獲取可用選項."
            return send_message, getReplyKeyBoard(message, action)
        elif action == "no-auth-docs":
            send_message = f"__哎呀！ 我無法找到並啟動授權。 請注意，僅在 10 分鐘內有效.__"
            send_message = (
                send_message
                + f"\n\n將機器人添加到您的群組，在群組中發送/start，然後點擊該群組中的授權按鈕。"
            )
            return send_message, getReplyKeyBoard(message, "no-auth-docs")

        elif action == "help-private-message":
            send_message = f"**VoiceChat 音樂播放器**\n**源代碼：** [資料庫]({config.get('GITHUB_REPO')})"
            send_message = (
                send_message
                + f"\n\n**[語音聊天音樂播放器]({config.get('BOT_URL')})** 是一個 [SkTechHub 產品]({config.get('PARENT_URL')})。"
            )
            send_message = send_message + f"\n\n__**可用指令**__"
            send_message = (
                send_message
                + f"\n• **/start : **__顯示歡迎消息並添加到群組按鈕.__"
            )
            if mongoDBClient.client:
                send_message = (
                    send_message
                    + f"\n• **/auth : ** __授權機器人，強製播放歌曲/視頻.__"
                )
            send_message = (
                send_message + f"\n• **/help : ** __顯示可用指令.__"
            )
            if mongoDBClient.client:
                send_message = (
                    send_message
                     + f"\n\n__• 您首先將機器人添加到群組/頻道。__\n"
                     + f"__• 為群組/頻道中的機器人提供管理員權限。__\n"
                     + f"__• 在該群組/頻道中發送/開始並單擊**授權按鈕**。__\n"
                     + f"__• Bot 將向您發送包含後續步驟的消息，按照它們進行操作即可。__\n"
                     + f"__• 在群組/頻道發送`/help`查看播放指令.__"
                )
            else:
                send_message = (
                    send_message
                     + f"\n\n__• 您首先將機器人添加到群組/頻道。__\n"
                     + f"__• 為群組/頻道中的機器人提供管理員權限。__\n"
                     + f"__• 在群組/頻道發送`/help`查看播放指令.__"
                )
            send_message = (
                send_message + f"\n\n**__如有任何問題，請聯繫@Kevin_RX__**"
            )
            return send_message, getReplyKeyBoard(message, action)

        elif action == "help-group-message":
            send_message = f"**語音聊天音樂播放器**\n**源代碼：** [資料庫]({config.get('GITHUB_REPO')})"
            send_message = (
                send_message
                + f"\n\n**[語音聊天音樂播放器]({config.get('BOT_URL')})** 是一個[SkTechHub 產品]({config.get('PARENT_URL')})。"
            )
            send_message = send_message + f"\n\n__**可用指令**__"
            send_message = (
                send_message
                + f"\n• **/start : ** __顯示授權步驟（強制性）.__"
            )
            send_message = (
                send_message
                + f"\n• **/play 音樂名稱|網址 : ** __播放指定的音樂__"
            )
            for k, v in extra_options.items():
                send_message = send_message + f"\n\t\t\t\t **{k}** : __{v}__"
            send_message = (
                send_message
                + f"\n`/play coldplay -video -res480` → __以 480p 播放視頻。__"
            )
            send_message = send_message + f"\n• **/stop : ** __停止播放。__"
            send_message = send_message + f"\n• **/pause : ** __暫停播放。__"
            send_message = send_message + f"\n• **/resume : ** __恢復播放。__"
            send_message = (
                send_message
                + f"\n• **/skip : ** __跳過並播放隊列中等待的下一個媒體。__"
            )
            send_message = (
                send_message + f"\n• **/help : ** __顯示可用命令。__"
            )
            send_message = (
                send_message + f"\n\n**__如有任何問題，請聯繫@Kevin_RX__**"
            )
            return send_message, getReplyKeyBoard(message, action)

        elif action == "chat-not-allowed":
            send_message = f"**😖 抱歉，此聊天尚不允許訪問該服務。 您可以隨時查看演示 [支援群組]({config.get('SUPPORT_GROUP')}).**"
            send_message = (
                send_message
                + f"\n\n**為什麼 ❓**\n- __由於使用率很高，我們僅在我們的網站上限制了機器人的使用[支援群組]({config.get('SUPPORT_GROUP')}) __"
            )
            send_message = (
                send_message
                + f"\n- __加入 [支援群組]({config.get('SUPPORT_GROUP')}) 訪問機器人或部署您自己的機器人 __ **源代碼：** [Github]({config.get('GITHUB_REPO')})"
            )

            return send_message, getReplyKeyBoard(message, action)

        elif action == "start-voice-chat":
            send_message = (
                f"**請開始語音聊天，然後再次發送指令**"
            )
            send_message = (
                send_message
                + f"\n1. __要開始群聊，您可以前往群組的描述頁面。__"
            )
            send_message = (
                send_message
                + f"\n2.__然後點擊靜音和搜索旁邊的三點按鈕開始語音聊天.__"
            )
            return send_message, getReplyKeyBoard(message, action)

    except Exception as ex:
        logException(f"**__getMessages 中的錯誤： {ex}__**", True)


def getReplyKeyBoard(message, action):
    try:
        if action in ["start-private-message", "help-private-message"]:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ 將機器人添加到群組 ➕",
                            url=f"{config.get('BOT_URL')}?startgroup=bot",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "👥 支援群組", url=f"{config.get('SUPPORT_GROUP')}"
                        ),
                        InlineKeyboardButton(
                            "📔 源代碼", url=f"{config.get('GITHUB_REPO')}"
                        ),
                    ],
                ]
            )
            return keyboard
        elif action == "start-group-message":
            rows = [
                [
                    InlineKeyboardButton(
                        "👥 支援群組p", url=f"{config.get('SUPPORT_GROUP')}"
                    ),
                    InlineKeyboardButton(
                        "📔 源代碼", url=f"{config.get('GITHUB_REPO')}"
                    ),
                ]
            ]
            if mongoDBClient.client:
                rows.insert(
                    0,
                    [
                        InlineKeyboardButton(
                            "🤖 授權機器人 🤖",
                            callback_data=f"授權用戶機器人",
                        ),
                    ],
                )
            keyboard = InlineKeyboardMarkup(rows)
            return keyboard
        elif action == "chat-not-allowed":
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏁 在演示群組中使用", url=f"{config.get('SUPPORT_GROUP')}"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "📔 源代碼", url=f"{config.get('GITHUB_REPO')}"
                        ),
                    ],
                ]
            )
            return keyboard
        return None
    except Exception as ex:
        logException(f"**__getReplyKeyBoard 錯誤： {ex}__**", True)
