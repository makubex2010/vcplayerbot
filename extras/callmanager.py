from utils import VideoFetchFromId
from pyrogram import Client
from pyrogram.types import User
import uuid
from pyrogram.errors.exceptions import BotMethodInvalid
from pyrogram.errors.exceptions.bad_request_400 import UserAlreadyParticipant
from pytgcalls import GroupCallFactory
from pytgcalls.exceptions import GroupCallNotFoundError
from decorators.extras import (
    delayDelete,
    delete_message,
    get_chat_member,
    send_message,
    send_photo,
    validate_session_string,
)
from decorators.message_factory import getMessage
from extras import queues
import time
from utils import loop
import os
from asyncio import QueueEmpty
import asyncio

from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import EditGroupCallTitle


from utils import (
    generate_blank_cover,
    generate_cover,
    logException,
    logInfo,
    logWarning,
    Singleton,
    config,
    mongoDBClient,
)


class GroupCallInstance(object):
    def __init__(
        self,
        chat_id,
        client_doc,
        bot_client: Client,
        user_app_client: Client,
        user_app_info: User = None,
    ):
        self.user_app_client: Client = user_app_client
        self.user_app_info = user_app_info
        self.bot_client: Client = bot_client
        self.client_doc = client_doc
        self.chat_id = chat_id
        self.active = False
        self.pytgcalls = GroupCallFactory(
            self.user_app_client, GroupCallFactory.MTPROTO_CLIENT_TYPE.PYROGRAM
        ).get_group_call()

        self.logInfo = lambda msg: logInfo(f"{self.chat_id}=>{msg}")
        self.logWarn = lambda msg: logWarning(f"{self.chat_id}=>{msg}")
        self.logException = lambda msg, send=True: logException(
            f"{self.chat_id}=>{msg}", send
        )

        @self.pytgcalls.on_playout_ended
        async def media_ended(gc, source, media_type) -> None:
            try:
                self.logInfo(f"播放結束，跳到下一首歌曲")
                await self.skip_playback(user_requested=False)
            except Exception as ex:
                self.logException(f"on_stream_end 錯誤: {ex}", True)

    async def set_pause_playback(self, pause=True):
        resp_msg = None
        try:
            await self.pytgcalls.set_pause(pause)
            resp_msg = f"✅ __成功{'Paused' if pause is True else 'Resumed'}回放。__"
        except Exception as ex:
            self.logException(f"set_pause_playback 錯誤 : {ex}")
            resp_msg = f"✖️ __出錯時{'Pausing' if pause is True else 'Resuming'} : {ex}__"
        finally:
            if resp_msg:
                await send_message(self.bot_client, self.chat_id, f"{resp_msg}")

    async def thumbnail_processing(self, songInfo, fetching_media_msg=None):
        try:
            if fetching_media_msg is not None:
                await delete_message(fetching_media_msg)
            m = await send_message(
                self.bot_client, self.chat_id, f"__🖼 生成縮略圖__"
            )
            cover_file_name = None
            if (
                songInfo.get("thumbnails") is not None
                and len(songInfo["thumbnails"]) > 0
            ):
                cover_file_name = f"images/{uuid.uuid4()}.png"
                cover_file_name = await generate_cover(
                    songInfo["title"],
                    songInfo["thumbnails"][-1],
                    cover_file_name,
                )
            else:
                cover_file_name = f"images/{uuid.uuid4()}.png"
                cover_file_name = await generate_blank_cover(cover_file_name)

            footer = None
            if config.get("PLAYBACK_FOOTER"):
                footer = f"{config.get('PLAYBACK_FOOTER')}".replace("\\n", "\n")
            footer_val = (
                footer if footer else "如有任何問題，請聯繫@Kevin_RX"
            )
            if songInfo["requested_by"].get("group_username"):
                footer_val = f"[點擊這裡](https://t.me/{songInfo['requested_by']['group_username']}?voicechat) 加入語音聊天和收聽/視頻媒體。\n{footer_val}"
            req_by = f"[{songInfo['requested_by']['title']}](tg://user?id={songInfo['requested_by']['chat_id']})"
            await delete_message(m)
            if cover_file_name is not None and os.path.exists(cover_file_name):
                logInfo(
                    f"在聊天中發送封面 : {self.chat_id} : {cover_file_name}"
                )
                caption = f"**{'📹' if songInfo['is_video'] is True else '🎧'} Name:** `{(songInfo['title'].strip())[:20]}`\n**⏱ Duration:** `{songInfo['duration']}` | **📺 Res:** `{songInfo['resolution']}`\n**💡 Requester:** {req_by}\n\n{footer_val}"
                await send_photo(
                    client=self.bot_client,
                    chat_id=self.chat_id,
                    photo=cover_file_name,
                    caption=caption,
                )

                if cover_file_name is not None and os.path.exists(cover_file_name):
                    os.remove(cover_file_name)
                return
            else:
                await send_message(
                    self.chat_id,
                    f"**✅ 現在播放 **\n\n**🎧 歌名:** `{(songInfo['title'].strip())[:20]}`\n**⏱ 歌曲時間:** `{songInfo['duration']}`\n**💡 請求者:** {req_by}\n\n{footer_val}",
                )
                return
        except Exception as ex:
            self.logException(f"thumbnail_processing 出錯 : {ex}")
            raise Exception(ex)

    async def check_if_user_bot_in_group(self):
        try:
            member = await get_chat_member(
                self.user_app_client, self.chat_id, self.user_app_info["id"]
            )
            return member is not None
        except Exception as ex:
            self.logException(f"checkIfUserBotIsInGroup 出錯 : {ex}")
            raise Exception(ex)

    async def try_to_add_user_app_in_group(self):
        try:
            invitelink = await self.bot_client.export_chat_invite_link(self.chat_id)
            await self.user_app_client.join_chat(invitelink)
            return True
        except UserAlreadyParticipant:
            return True
        except Exception as ex:
            self.logException(f"try_to_add_user_app_in_group 出錯 : {ex}")
            raise Exception(ex)

    async def start_playback(self, songInfo, fetching_media_msg=None):
        isError, resp_msg = None, None
        try:
            self.logInfo(f"開始播放，歌曲 → {songInfo}")
            try:
                isMember = await self.check_if_user_bot_in_group()
                if not isMember:
                    await self.try_to_add_user_app_in_group()
            except Exception as ex:
                self.logException(f"開始播放時出錯： {ex}")
                tag = f"[{self.user_app_info['username']}](tg://user?id={self.user_app_info['id']})"
                resp_msg = f"✖️__確保用戶 {tag} 被添加為該組的管理員。 → {ex}__"
                return

            try:
                # condition when to fetch youtube url again
                if not fetching_media_msg and songInfo["is_youtube"] is True:
                    resfreshedSong = await VideoFetchFromId(
                        songInfo["id"], songInfo["is_video"], songInfo["resolution"]
                    )
                    songInfo["link"] = resfreshedSong["link"]
                    songInfo["audio_link"] = resfreshedSong["audio_link"]

                await self.thumbnail_processing(songInfo, fetching_media_msg)
                mongoDBClient.add_song_playbacks(
                    songInfo, songInfo["requested_by"], self.client_doc.get("_id")
                )

                await self.pytgcalls.join(self.chat_id)
                if songInfo["is_video"] is False or songInfo["only_audio"] is True:
                    await self.pytgcalls.start_audio(
                        songInfo["link"], repeat=songInfo["is_repeat"]
                    )
                else:
                    await self.pytgcalls.start_video(
                        songInfo["link"],
                        repeat=songInfo["is_repeat"],
                        with_audio=True,
                        enable_experimental_lip_sync=songInfo["lip_sync"],
                    )
                self.logInfo(f"開始播放")
                self.active = True
            except GroupCallNotFoundError as ex:
                msg, kbd = getMessage(None, "start-voice-chat")
                await self.stop_playback(False, False, True)
                resp_msg = msg
                return

            # edit group call title
            try:
                input_peer = await self.user_app_client.resolve_peer(self.chat_id)
                chat = await self.user_app_client.send(
                    GetFullChannel(channel=input_peer)
                )
                title_change = EditGroupCallTitle(
                    call=chat.full_chat.call, title="VC Player | By SkTechHub"
                )
                await self.user_app_client.send(title_change)
            except Exception as ex:
                logWarning(f"無法更改群組通話標題 ")

        except Exception as ex:
            self.logException(f"開始播放時出錯: {ex}", True)
            resp_msg = f"__開始播放時出錯 : {ex}__"
            isError = True
        finally:
            if resp_msg:
                await send_message(self.bot_client, self.chat_id, f"{resp_msg}")
            if isError:
                await self.skip_playback()

    async def add_to_queue(self, songInfo, fetching_media_msg=None):
        resp_msg = None
        try:
            self.logInfo(f"將歌曲添加到清單中。")
            max_queue_size = self.client_doc.get("extras").get("max_queue_size")
            if queues.size(self.chat_id) >= max_queue_size:
                resp_msg = (
                    f"✖️__目前最多 {max_queue_size} 媒體可以添加到清單中。 請稍後重試。__",
                )
            await queues.put(
                self.chat_id, songInfo=songInfo, requested_by=songInfo["requested_by"]
            )
            req_by = f"[{songInfo['requested_by']['title']}](tg://user?id={songInfo['requested_by']['chat_id']})"
            # if this was the first song, start playing it right now
            if self.active is False:
                await self.start_playback(
                    queues.get(self.chat_id)["songInfo"], fetching_media_msg
                )
            else:
                await delete_message(fetching_media_msg)
                resp_msg = f"__✅ Added to queue.__\n\n**Name:** `{(songInfo['title'].strip())[:20]}`\n**Requester:** {req_by}\n**Media in queue:** `{queues.size(self.chat_id)}`"

        except Exception as ex:
            self.logException(f"add_to_queue 錯誤： {ex}")
            resp_msg = f"✖️ __在清單中添加歌曲時出錯 : {ex}.__"
        finally:
            if resp_msg:
                await send_message(self.bot_client, self.chat_id, resp_msg)

    async def skip_playback(self, user_requested=False):
        resp_msg = None
        try:
            self.logInfo(
                f"跳過播放 : user_requested : {user_requested}, 隊列大小 : {queues.size(self.chat_id)} "
            )
            queues.task_done(self.chat_id)
            if queues.is_empty(self.chat_id) is True:
                if user_requested is False:
                    return await self.stop_playback()
                resp_msg = f"🛑 __隊列中沒有媒體等待，如果你想停止發送 /stop.__"
            else:
                new_media = queues.get(self.chat_id)
                await self.start_playback(new_media["songInfo"])
        except Exception as ex:
            self.logException(f"Error in skip_playback: {ex}")
            resp_msg = f"✖️ __Error while skipping : {ex}__"
        finally:
            if resp_msg:
                await send_message(self.bot_client, self.chat_id, f"{resp_msg}")

    async def stop_playback(
        self, user_requested=False, send_reason_msg=False, stop_silently=False
    ):
        resp_msg = None
        try:
            self.logInfo(f"停止播放 : user_requested : {user_requested} ")
            try:
                queues.clear(self.chat_id)
            except QueueEmpty as qe:
                self.logWarn(f"可以忽略 : 隊列空::stop :{qe}")
            except Exception as ex:
                self.logWarn(f"可以忽略 : 隊列清除 Error :{ex}")

            try:
                await self.pytgcalls.stop()
            except Exception as ex:
                self.logWarn(f"可以忽略 : pytgcalls.stop :{ex}")

            try:
                await self.pytgcalls.leave_current_group_call()
            except Exception as ex:
                self.logWarn(f"可以忽略 : leave_current_group_call :{ex}")

            if send_reason_msg is True:
                resp_msg = f"**播放結束 `[如果您正在播放歌曲並且收到此消息，那麼這是由於部署而發生的。 你可以過一段時間再玩。]`**\n\n__感謝您嘗試並提供您的反饋/建議@sktechhub_chat。__"
            else:
                resp_msg = f"__播放結束，請提供您的反饋/建議@voicechatsupport。__"

        except BotMethodInvalid as bi:
            self.logWarn(f"停止播放時出現預期錯誤 : {bi}")
            resp_msg = f"✖️ __停止時出錯 : {bi}__"
        except Exception as ex:
            self.logException(f"停止播放時出錯: {ex}")
            resp_msg = f"✖️ __停止時出錯 : {ex}__"
        finally:
            self.active = False
            if (
                self.user_app_client is not None
                and self.user_app_client.is_connected is True
            ):
                await self.user_app_client.stop()
            if not stop_silently and resp_msg:
                await send_message(self.bot_client, self.chat_id, f"{resp_msg}")


class MusicPlayer(metaclass=Singleton):
    def __init__(self):
        self.group_calls = {}

    def cleanTheGroupCallDict(self):
        try:
            new_gc = {}
            for chat_id, gc_instance in self.group_calls.items():
                if gc_instance.active is True:
                    new_gc[chat_id] = gc_instance
            logInfo(
                f"清理 GroupCall Dict : New {len(new_gc)} , old : {len(self.group_calls)}"
            )
            self.group_calls = new_gc
        except Exception as ex:
            logException(f"cleanTheGroupCallDict 中的錯誤 {ex}", True)

    def _getActiveGroupCalls(self):
        return len(self.group_calls)

    async def getGroupCallInstance(self, chat_id):
        try:
            logInfo(
                f"調用獲取組呼實例 : {chat_id} {len(self.group_calls)}"
            )
            self.cleanTheGroupCallDict()
            return (
                self.group_calls.get(chat_id),
                f"🤭 __請先播放媒體，然後再執行此操作。__",
            )
        except Exception as ex:
            logException(f"getGroupCallInstance 出錯 {ex}")
            return (
                None,
                f"__❌意外錯誤，請放心，我們最優秀的人才已收到通知，他們正在努力解決。__",
            )

    async def createGroupCallInstance(self, chat_id, current_client, bot_client):
        try:
            logInfo(
                f"呼叫創建新的群組呼叫實例 : {chat_id} {len(self.group_calls)}"
            )
            gc_instance, err_msg = await self.getGroupCallInstance(chat_id)
            if gc_instance is not None:
                logInfo(f"GroupCall 實例已經存在。")
                return self.group_calls.get(chat_id), ""
            else:
                # check if it can be created
                if self._getActiveGroupCalls() >= config.get("SIMULTANEOUS_CALLS"):
                    return (
                        None,
                        f"__❌ 抱歉，目前該服務正在使用中 `{self._getActiveGroupCalls()}` 群組/頻道，目前由於缺乏資源，我們最多支持 `{config.get('SIMULTANEOUS_CALLS')}` 同時播放。__\n\n__請稍後重試。__",
                    )
                logInfo(f"新建群組通話實例 : {chat_id}")
                user_app, user_app_info = None, None
                try:
                    userBotDoc = current_client["userBot"]
                    (
                        status,
                        reason,
                        user_app,
                        id,
                        username,
                    ) = await validate_session_string(
                        userBotDoc.get("apiId"),
                        userBotDoc.get("apiHash"),
                        userBotDoc.get("sessionId"),
                        getUser=True,
                    )
                    if not status:
                        raise Exception(reason)
                    user_app_info = {
                        "id": id,
                        "username": username if username else "User",
                    }
                except Exception as ex:
                    logException(f"啟動客戶端時出錯: {ex}")
                    return (
                        None,
                        f"__❌ 無法啟動用戶機器人 : {ex}\n請管理員再次授權。__",
                    )

                gc = GroupCallInstance(
                    chat_id, current_client, bot_client, user_app, user_app_info
                )
                self.group_calls[chat_id] = gc
                return gc, None

        except Exception as ex:
            logException(f"createGroupCallInstance 出錯: {ex}", True)
            return (
                None,
                "__❌ 意外錯誤，請放心，我們最優秀的人才已收到通知，他們正在努力解決.__",
            )

    async def shutdown(self):
        try:
            for chat_id, gc in self.group_calls.items():
                try:
                    if gc is not None and gc.active is True:
                        await gc.stopPlayBack(False, True)
                except Exception as ex:
                    logException(f"關機時出錯 {chat_id},  {ex}", True)

        except Exception as ex:
            logException(
                f"關閉音樂播放器的所有實例時出錯 {ex}", True
            )
