#  === message type ===
# 通知消息
NOTIFICATION_MESSAGE = 0
# 聊天消息
CHAT_MESSAGE = 1
# 私聊
PRIVATE_CHAT = 1
# 群聊
GROUP_CHAT = 2


# === group manager ===

INVITE_JOIN_GROUP = 0
APPLY_JOIN_GROUP = 1


#  === message context type ===
TEXT = 0
IMAGE = 1
VIDEO = 2
AUDIO = 3
LINK = 4

#  === redis config ===

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2


IS_TEST_ENV = True


#  === redis key (new record) ===
NEW_MESSAGE = 'NEW-MESSAGE'
NEW_HISTORICAL_CONTACTS_RECORD = 'NEW-HISTORICAL-CONTACTS-RECORD'
