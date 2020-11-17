import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import re
import time
import configparser
config = configparser.ConfigParser()
config.sections()
config.read('config.ini')
# Levenstein algorithm
# from fuzzywuzzy import fuzz

GROUP = -6923031
TOKEN_GROUP = config['TOKEN']['TOKEN_GROUP']
TOKEN_USER = config['TOKEN']['TOKEN_USER']
LOGIN = config['AUTH']['LOGIN']
vk_admin = vk_api.VkApi(login=LOGIN, token=TOKEN_USER)
vk_admin.auth(token_only=True)
vk = vk_admin.get_api()

# longpoll auth
vk_group = vk_api.VkApi(token=TOKEN_GROUP)
vk_group_bot = vk_group.get_api()
longpoll = VkBotLongPoll(vk_group, 199772710)

class VKAlbumSearcher:

    def __init__(self, query_string, event):

        self.group = ''
        self.album = ''
        self.url = ''
        self.query_string = query_string
        self.comments = {}
        self.words = []
        self.repeats = []
        self.event = event

    def split_url(self):

        splitted_query_string = self.query_string.split()

        if len(splitted_query_string) < 2:
            vk_group_bot.messages.send(
                user_id=self.event.obj.from_id,
                random_id=self.event.obj.random_id,
                peer_id=GROUP,
                message="Неккоректный запрос. Пример корректного запроса: https://vk.com/album-6923031_249426673 шум korg"
            )
            raise ValueError("Split failed")

        self.url = splitted_query_string[0]

        for i in range(1, len(splitted_query_string)):
            self.words.append(splitted_query_string[i])

        print("String: ", self.query_string, '\n',
              "Url: ", self.url, '\n',
              "Word: ", self.words, '\n')

    def find_group_and_album_url(self):

        # find any letters after "-" like "-111111_222222"
        re_group_and_album = re.search(r'-\w+', self.url)
        re_group_and_album_match = re_group_and_album.group(0)

        # find 2 groups of letters in re_group_and_album like "111111" and "222222"
        re_group_and_album_parts = re.match(r'-(\w+)_(\w+)', re_group_and_album_match)

        # raise if both reg exp are empty
        if not re_group_and_album or not re_group_and_album_parts:
            vk_group_bot.messages.send(
                user_id=self.event.obj.from_id,
                random_id=self.event.obj.random_id,
                peer_id=GROUP,
                message="Неккоректная ссылка. Пример корректной ссылки: https://vk.com/album-6923031_249426673."
            )
            raise ValueError("Not valid URL")

        self.group = re_group_and_album_parts.groups()[0]
        self.album = re_group_and_album_parts.groups()[1]

        print("Group: ", self.group, '\n',
              "Album: ", self.album, '\n')

    def get_album_comments(self):

        # check if group and album are convertable
        try:
            group_id = int('-' + self.group)
            album_id = int(self.album)
        except ValueError as VE:
            vk_group_bot.messages.send(
                user_id=self.event.obj.from_id,
                random_id=self.event.obj.random_id,
                peer_id=GROUP,
                message="Неккоректная ссылка. Пример корректной ссылки: https://vk.com/album-6923031_249426673."
            )
            raise ValueError("can't change int to str: ", VE)

        tools = vk_api.VkTools(vk)
        response = {}

        try:
            response = tools.get_all('photos.getAllComments', 100, {'owner_id': group_id, 'album_id': album_id})
        except Exception as e:
            vk_group_bot.messages.send(
                user_id=self.event.obj.from_id,
                random_id=self.event.obj.random_id,
                peer_id=GROUP,
                message="Не удалось получить комментарии к альбому."
            )
            raise ValueError("Get album comments failed with: ", e)

        # check if response is empty
        if len(response['items']) < 1:
            vk_group_bot.messages.send(
                user_id=self.event.obj.from_id,
                random_id=self.event.obj.random_id,
                peer_id=GROUP,
                message="Комментарии в альбоме не найдены."
            )
            raise ValueError("Response is empty")

        result_dict = {}
        for i in response['items']:
            result_dict[i['text'].lower()] = "https://vk.com/photo-" + str(self.group)\
                                           + '_' + str(i['pid'])

        for j in result_dict.items():
            print(j)

        self.comments = result_dict

    def check_len(self, string):
        return len(string) < 4095

    def find_in_comments(self):

        final_message = []
        for word in self.words:
            for comment, url in self.comments.items():
                r = re.findall(f'{word}', comment)
                if r and (comment not in self.repeats):
                    if len(final_message) > 20:
                        final_message = [("Комментариев слишком много (больше 20), попробуйте сузить запрос.")]
                        return final_message
                    final_message.append(f"Запрос: {word}\nТекст: {str(comment)}\nUrl: {str(url)}\n\n")
                    self.repeats.append(comment)

        if len(final_message) < 1:
            tmp = ''
            for word in self.words:
                tmp += word + ', '
            final_message.append(f"Комментарии по запросу '{tmp[0:-2]}' не найдены.")

        return final_message


    def find(self):
        self.split_url()
        self.find_group_and_album_url()
        self.get_album_comments()
        return self.find_in_comments()


def is_url_valid(url):
    r = re.search(r'album', url)
    return r


def listen():

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if is_url_valid(event.obj.text):
                searcher = VKAlbumSearcher(str(event.obj.text).lower(), event)
                msg = searcher.find()
                for i in msg:
                    vk_group_bot.messages.send(
                        user_id=event.obj.from_id,
                        random_id=event.obj.random_id,
                        peer_id=GROUP,
                        message=i
                    )

            else:
                vk_group_bot.messages.send(
                    user_id=event.obj.from_id,
                    random_id=event.obj.random_id,
                    peer_id=GROUP,
                    message='Неправильная ссылка на альбом. Корректный пример: https://vk.com/album-6923031_249426673'
                )


while True:
    try:
        time.sleep(1)
        listen()
    except Exception as e:
        print("App crashed with ", e)