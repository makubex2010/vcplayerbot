import re
from decorators.extras import (
    get_chat_member_count,
    get_chat_member_list,
    parseIncomingCommand,
)
from typing import Callable
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, Chat

from utils import logException, logInfo, config


def validate_command_pre_check(func: Callable) -> Callable:
    async def decorator(client: Client, incomingPayload, current_client):
        try:
            if isinstance(incomingPayload, CallbackQuery) is True:
                message: Message = incomingPayload.message
            else:
                message: Message = incomingPayload
            isPlayCommand = (
                message.command
                and re.match("play", message.command[0], flags=re.I) is not None
            )
            current_chat: Chat = message.chat
            reason = None

            if isPlayCommand is True:
                parsed_command = parseIncomingCommand(
                    message.text,
                    current_client.get("extras").get("max_video_res"),
                    current_client.get("extras").get("max_audio_res"),
                )
                current_client["parsed_command"] = parsed_command

            if current_client.get("error") or not current_client.get("active"):
                reason = (
                    current_client.get("error")
                    if current_client.get("error")
                    else "管理員禁止/不允許。"
                )
            elif not current_client.get("userBot") or not current_client.get(
                "userBot"
            ).get("sessionId"):
                reason = "您還沒有給機器人權限，請發送 /start 點擊授權按鈕。"
            elif (
                isPlayCommand is True
                and parsed_command["is_video"] is True
                and current_client.get("extras").get("allow_video") is False
            ):
                reason = f"視頻播放已被管理員禁用。"
            elif (
                isPlayCommand is True
                and parsed_command["is_video"] is False
                and current_client.get("extras").get("allow_audio") is False
            ):
                reason = f"管理員禁用了音頻播放。"
            elif (
                isPlayCommand is True
                and parsed_command["is_youtube"] is False
                and current_client.get("extras").get("allow_others") is False
            ):
                reason = f"您的帳戶中只允許播放 youtube。"
            elif current_client.get("extras").get("min_members", 0) > 0:
                num_members = await get_chat_member_count(client, current_chat.id)
                current_client["num_members"] = num_members
                required = current_client.get("extras").get("min_members", 0)
                if num_members and num_members < required:
                    reason = f"群組/頻道至少需要 **{required}** 成員。"

            if reason:
                msg = f"😕很抱歉打擾你，但由於以下原因你無法訪問機器人：__\n\n**__{reason}__**\n\n__聯繫[群組]（{config.get（'SUPPORT_GROUP' )}) 對於任何查詢"
                return await client.send_message(
                    message.chat.id, f"{msg}", disable_web_page_preview=True
                )

            requested_by = (
                {
                    "chat_id": message.from_user.id,
                    "title": message.from_user.first_name
                    if hasattr(message.from_user, "first_name")
                    else (
                        message.from_user.username
                        if hasattr(message.from_user, "username")
                        else "User"
                    ),
                    "is_sender_chat": False,
                    "group_username": current_chat.username
                    if hasattr(current_chat, "username")
                    else None,
                }
                if message.from_user is not None
                else {
                    "chat_id": message.chat.id,
                    "title": message.chat.title
                    if hasattr(message.chat, "title")
                    else "Chat",
                    "is_sender_chat": True,
                    "group_username": current_chat.username
                    if hasattr(current_chat, "username")
                    else None,
                }
            )
            current_client["requested_by"] = requested_by
            return await func(client, incomingPayload, current_client)
        except Exception as ex:
            logException(f"Error in validate_command_pre_check : {ex}")

    return decorator
