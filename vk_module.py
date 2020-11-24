import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

import configparser

# init config
config = configparser.ConfigParser()
config.sections()
config.read('C:\\Users\\Alex\\PycharmProjects\\VkAlbumBot\\config.ini')


def auth_handler():
    # two factor auth
    key = input("Enter authentication code: ")
    remember_device = True
    return key, remember_device


# Album Bot group and token
GROUP = -6923031
TOKEN_GROUP = config['TOKEN']['TOKEN_GROUP']

# Vk admin login
PASS = config['AUTH']['PASS']
LOGIN = config['AUTH']['LOGIN']

# Vk admin auth
vk_admin = vk_api.VkApi(login=LOGIN, password=PASS, auth_handler=auth_handler)
vk_admin.auth()
vk = vk_admin.get_api()

# longpoll auth
vk_group = vk_api.VkApi(token=TOKEN_GROUP)
vk_group_bot = vk_group.get_api()
longpoll = VkBotLongPoll(vk_group, 199772710)


def send_message(event, text):
    vk_group_bot.messages.send(
        user_id=event.obj.from_id,
        random_id=event.obj.random_id,
        peer_id=GROUP,
        message=text
    )

