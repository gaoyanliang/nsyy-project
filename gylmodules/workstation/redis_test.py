import redis

# Connecting to Redis
redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=2, decode_responses=True)

message_id = -1


# pool = redis.ConnectionPool(host='127.0.0.1', port=6379, db=2, decode_responses=True)
# redis_client = redis.Redis(connection_pool=pool)

print(redis_client)


def get_message_id():
    global message_id

    if message_id == -1:
        print("========" + str(message_id))
        message_id += 1
    else:
        print("ssssss" + str(message_id))

# Trying to set a key with an invalid name
try:
    # redis_client.rpush('test-list-key', 'value1')
    # redis_client.rpush('test-list-key', 'value2')
    # redis_client.rpush('test-list-key', 'value3')
    # redis_client.rpush('test-list-key', 'value4')
    # redis_client.rpush('test-list-key', 'value5')
    # redis_client.rpush('test-list-key', 'value6')
    # print(redis_client.llen('test-list-key'))
    # print(redis_client.lrange('test-list-key', redis_client.llen('test-list-key')-2, redis_client.llen('test-list-key')-1))

    # redis_client.sadd('test-set-key', 1)
    # redis_client.sadd('test-set-key', 2)
    # redis_client.sadd('test-set-key', 3)
    # redis_client.sadd('test-set-key', 4)
    # print('1test-set-key len: ')
    # print(redis_client.scard('test-set-key'))
    # print(redis_client.smembers('test-set-key'))
    # print('2test-set-key len: ')
    # print(redis_client.scard('test-set-key'))
    #
    # redis_client.srem('test-set-key', 1)
    # print(redis_client.smembers('test-set-key'))

    # print(redis_client.smembers('test-set-key'))
    # redis_client.srem('test-set-key', 4)
    # print(redis_client.smembers('test-set-key'))

    # redis_client.set("key", 2)
    # print(redis_client.get('key'))
    #
    # redis_client.set("key", int(redis_client.get('key')) + 1)
    # print(redis_client.get('key'))

    # print(redis_client.lrange('NotificationMessage[2]', -10, -1))
    # print(redis_client.lrange('NotificationMessage[2]', -2, -1))

    # redis_client.flushdb()
    # print("--")

    get_message_id()
    get_message_id()


except UnicodeError as e:
    print(f'UnicodeError: {e}')





