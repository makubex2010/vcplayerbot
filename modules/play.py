from decorators.validate_command_pre_check import validate_command_pre_check
from decorators.save_user_chat_db import save_user_chat_in_db
from decorators.is_bot_admin import is_bot_admin
from decorators.extras import send_message, edit_message, delayDelete
from pyrogram import Client, filters
from utils import (
    logInfo,
    logException,
    logWarning,
    helperClient,
    VideoSearch,
    config,
    loop,
)
from extras import music_player
import uuid


@Client.on_message(
    filters.command(["play", "play@vcplayerbot"]) & ~filters.bot & ~filters.private
)
@save_user_chat_in_db
@is_bot_admin
@validate_command_pre_check
async def play(client: Client, message, current_client):
    try:
        current_chat = message.chat
        # check if song url or name is provided or not
        parsed_command = current_client.get("parsed_command")
        logInfo(
            f"在聊天中播放命令 : {current_chat.id} , requested_by: {current_client['requested_by']} , command: {parsed_command}"
        )
        if not parsed_command or helperClient.isEmpty(parsed_command["song_name"]):
            await send_message(
                client,
                current_chat.id,
                f"__請提供媒體網址或名稱。\n例如 → **/play 69 歲的夏天**__",
            )
            return

        (gc_instance, err_message,) = await music_player.createGroupCallInstance(
            current_chat.id, current_client, client
        )
        if gc_instance is None:
            return await send_message(client, current_chat.id, f"{err_message}")

        sent_msg = await send_message(
            client,
            current_chat.id,
            f"__👀 抓取 {'video' if parsed_command['is_video'] is True else 'audio'} 細節... __",
        )
        if parsed_command["is_youtube"] is True:
            songDetails = await VideoSearch(
                parsed_command["song_name"],
                parsed_command["song_url"],
                parsed_command["is_video"],
                parsed_command["resolution"],
            )
        else:
            if parsed_command["song_url"] is None:
                return await send_message(
                    client,
                    current_chat.id,
                    f"✖️ __請提供一個直接的串流媒體網址。__",
                )
            songDetails = [
                {
                    "id": uuid.uuid4(),
                    "thumbnails": None,
                    "title": "串流媒體網址",
                    "long_desc": "A SkTechHub Product",
                    "channel": "SkTechHub",
                    "duration": None,
                    "views": None,
                    "link": parsed_command["song_url"],
                    "audio_link": None,
                    "resolution": "Default",
                    "is_video": True,
                }
            ]

        if songDetails is not None and len(songDetails) > 0:
            song_info = songDetails[0]
            max_duration = current_client.get("extras").get("max_duration")
            if song_info["duration"] and song_info["duration"] > int(max_duration):
                await edit_message(
                    sent_msg,
                    f"__😢 指定的歌曲太長，請使用長度小於 {max_duration} 秒的歌曲。__",
                )
                return
            song_info["is_repeat"] = parsed_command["is_repeat"]
            song_info["only_audio"] = parsed_command["only_audio"]
            song_info["lip_sync"] = parsed_command["lip_sync"]
            song_info["requested_by"] = current_client["requested_by"]
            song_info["is_youtube"] = parsed_command["is_youtube"]
            await gc_instance.add_to_queue(song_info, sent_msg)
        else:
            await edit_message(
                sent_msg, f"__😢 無法找到所需的歌曲，請重試.__"
            )

    except Exception as ex:
        await send_message(client, message.chat.id, f"__Error in play command : {ex}__")
        logException(f"Error in play command : {ex}")
