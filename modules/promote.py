from pyrogram import Client, filters
from decorators.extras import send_message, edit_message, send_photo
from utils import logException, logInfo, logWarning, config
import asyncio
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

"""
Only allowed by sudo user
"""


@Client.on_message(
    filters.command(["promote", "promote@vcplayerbot"]) & ~filters.bot & filters.private
)
async def promote(client, message):
    try:
        if message.from_user.id in config.get("SUDO_USER"):
            is_message_confirmed = (
                len(message.command) > 2 and message.command[2] == "confirm"
            )
            chat_ids = [c.strip() for c in message.command[1].split(",")]
            if not chat_ids:
                return await send_message(
                    client,
                    message.from_user.id,
                    "__請提供聊天 ID 作為以逗號分隔的第二個參數。__",
                )
            promotional_data = config.get("PROMOTIONAL_DATA")
            if not promotional_data:
                return await send_message(
                    client,
                    message.from_user.id,
                    "__請在數據庫中添加促銷信息作為 **PROMOTIONAL_MSG**。__",
                )
            if not is_message_confirmed:
                await send_message(
                    client,
                    message.from_user.id,
                    f"__確認以下訊息至**{len(chat_ids)} users** .__",
                )
                chat_ids = config.get("SUDO_USER")
            else:
                await send_message(
                    client,
                    message.from_user.id,
                    f"__開始發送信息給**{len(chat_ids)} users** .__",
                )
            logInfo(f"開始發送信息至 {len(chat_ids)} 用戶.")
            promotional_msg = promotional_data.get("message").replace("\\n", "\n")
            if promotional_data.get("button_text") is not None:
                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                promotional_data.get("button_text"),
                                url=promotional_data.get("button_url"),
                            ),
                        ]
                    ]
                )
            else:
                keyboard = None
            for count, chat in enumerate(chat_ids):
                logInfo(
                    f"{count} → 發送到聊天: {chat}, 剩下: {len(chat_ids)-count-1}"
                )
                if promotional_data.get("image"):
                    await send_photo(
                        client,
                        chat,
                        promotional_data.get("image"),
                        promotional_msg,
                        reply_markup=keyboard,
                    )
                else:
                    await send_message(
                        client, chat, promotional_msg, reply_markup=keyboard
                    )
                await asyncio.sleep(5)

            await send_message(
                client,
                message.from_user.id,
                f"__發送促銷信息已結束 **{len(chat_ids)} users** .__",
            )
    except Exception as ex:
        await send_message(client, message.chat.id, f"__推廣時出錯 : {ex}__")
        logException(f"推廣錯誤: {ex}", True)
