# ===========================================================
# =============         message         =====================
# ===========================================================
# 通知消息
NOTIFICATION_MESSAGE = 0
# 私聊
PRIVATE_CHAT = 1
# 群聊
GROUP_CHAT = 2


# msg cache redis key
msg_cache_key = {
    "group_member": "MESSAGE:GroupMember:{}",
    "group_info": "MESSAGE:GroupInfo:{}",
    "messages": "MESSAGE:Messages:{}",
}



