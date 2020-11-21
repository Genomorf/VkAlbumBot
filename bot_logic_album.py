# -*- coding: utf-8 -*-
import vk_api

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import re
import time
import configparser
# init config
config = configparser.ConfigParser()
config.sections()
config.read('config.ini')

def auth_handler():
    #t wo factor auth
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


# main class of comment searcher
class VKAlbumSearcher:

    def __init__(self, query_string, event, is_multiple, album_title=None):

        self.group = ''
        self.album = ''
        self.url = ''
        self.query_string = query_string
        self.comments = {}
        self.words = []
        self.repeats = []
        self.event = event
        self.is_multiple = is_multiple
        if album_title:
            self.album_title = "Альбом: " + album_title + "\n"

    def split_url(self):

        splitted_query_string = self.query_string.split()

        # must be 2 words in query: "url query"
        if len(splitted_query_string) < 2:
            send_message(self.event,
                         "Неккоректный запрос. Пример корректного запроса:"
                         " https://vk.com/album-6923031_249426673 шум korg"
                         )
            raise ValueError("Split failed")

        # get url from query
        self.url = splitted_query_string[0]

        # get query words from query
        for i in range(1, len(splitted_query_string)):
            self.words.append(splitted_query_string[i])

    def find_group_and_album_url(self):

        # find any letters after "-" like "-111111_222222"
        re_group_and_album = re.search(r'-\w+', self.url)
        re_group_and_album_match = re_group_and_album.group(0)

        # find 2 groups of letters in re_group_and_album like "111111" and "222222"
        re_group_and_album_parts = re.match(r'-(\w+)_(\w+)', re_group_and_album_match)
        print(re_group_and_album_parts.groups()[0])
        # raise if both reg exp are empty
        if not re_group_and_album or not re_group_and_album_parts:
            send_message(self.event,
                         "Неккоректная ссылка на альбом. Пример корректной ссылки:"
                         " https://vk.com/album-6923031_249426673."
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
            send_message(self.event,
                         "Неккоректная ссылка на альбом. Пример корректной ссылки: "
                         "https://vk.com/album-6923031_249426673."
                         )
            raise ValueError("can't change int to str: ", VE)

        tools = vk_api.VkTools(vk)
        response = {}

        # main request from vk.com API
        try:
            response_part_1 = tools.get_all_iter(method='photos.getAllComments', max_count=100, values={'owner_id': group_id, 'album_id': album_id})
            response_part_2 = vk.photos.get(owner_id=group_id, album_id=album_id, count=900)
        except Exception as e:
            send_message(self.event,
                         "Не удалось получить комментарии к альбому."
                         )
            raise ValueError("Get album comments failed with: ", e)
        response = {}
        for i in response_part_1:
            response[" \"" + i['text'].lower() + "\" "] = "https://vk.com/photo-" + str(self.group)\
                                            + '_' + str(i['pid'])
        for i in response_part_2['items']:
            response[" \"" + i['text'].lower() + "\" "] = "https://vk.com/photo-" + str(self.group)\
                                            + '_' + str(i['id'])

        # check if response is empty
        if len(response) < 1:
            send_message(self.event,
                         "Комментарии в альбоме не найдены."
                         )
            raise ValueError("Response is empty")

        self.comments = response

    def find_in_comments(self):

        final_message = []

        counter = 1

        for word in self.words:
            for comment, url in self.comments.items():
                r = re.findall(f'{word}', comment)
                if r and (comment not in self.repeats):
                    if len(final_message) > 25:
                        final_message = [(f"{self.album_title + ' ' if self.album_title else ''}"
                                         "Комментариев слишком много (больше 20), попробуйте сузить запрос.")]
                        return final_message
                    #final_message.append(counter)
                    final_message.append(f"{self.album_title}&#128204; {counter}:\n&#128270; Запрос: {word}\n&#128196; Текст: {str(comment)}\n&#128206; Url: {str(url)}\n\n")
                    self.repeats.append(comment)
                    counter += 1

        # check if empty
        if not self.is_multiple:
            if len(final_message) < 1:
                tmp = ''
                for word in self.words:
                    tmp += word + ', '
                final_message.append(f"Комментарии по запросу '{tmp[0:-2]}' не найдены.")

        return final_message

    def find(self):
        # main function
        self.split_url()
        self.find_group_and_album_url()
        self.get_album_comments()
        return self.find_in_comments()

def find_all(query, event):
    splitted_query = query.split()
    if len(splitted_query) < 2:
        send_message(event, "Неккоректный запрос. Пример корректного запроса:"
                            " https://vk.com/albums-104169151 питер"
                     )
        raise ValueError("Split failed")
    url = splitted_query[0]
    re_find_slice = re.match(r'.+\s(\[(\d+)-(\d+)\])\s.+', query)
    words = []
    slice_1 = 0
    slice_2 = 0
    is_sliced = False
    if re_find_slice:
        words += splitted_query[2:]
        slice_1 += int(re_find_slice.groups()[1])
        slice_2 += int(re_find_slice.groups()[2])
        words_in_message = ''
        for i in words:
            words_in_message += i + ', '
        if slice_1 > slice_2:
            send_message(event, "Неккоретный запрос. "
                                "Пример корректного запроса: " +
                                f"https://vk.com/albums-104169151 [{slice_2}-{slice_1}] {words_in_message[0:-2]}")
            raise ValueError("Slice failed")
        is_sliced = True
    else:
        words += splitted_query[1:]
    words_str = ''
    for i in words:
        words_str += ' ' + i.lower()

    re_check = re.match(r'.+(albums)-(\d+)', url)

    if not re_check:
        send_message(event, "Неккоректная ссылка на альбомы группы."
                            " Пример корректной ссылки: https://vk.com/albums-104169151"
                     )
        raise ValueError("Invalid url")

    re_group_id = re.search(r'albums-(\w+)', url)
    group_id = '-' + re_group_id.groups(0)[0]
    response = vk.photos.getAlbums(owner_id=group_id)
    query_list = {}

    if is_sliced:
        for i in response['items'][slice_1: slice_2]:
            query_list[(f'https://vk.com/album{group_id}_' + str(i['id']) + words_str)] \
                = i['title']
    else:
        for i in response['items']:
            query_list[(f'https://vk.com/album{group_id}_' + str(i['id']) + words_str)] \
                = i['title']

    for i in query_list:
        print(i)
    print(len(query_list.items()))
    if len(query_list.items()) > 50:
        send_message(event,
                     "Слишком много альбомов - больше 50. Используйте выборку, например: "
                     f"{url} [0-30] {words_str}")
        raise ValueError("Too many albums")

    send_message(event, f"Выполняется поиск по {slice_2 if is_sliced else 'всем'} альбомам группы...")


    search_counter = 0
    for key, value in query_list.items():
        searcher = VKAlbumSearcher(str(key).lower(), event, True, value)
        msg = searcher.find()
        for j in msg:
            send_message(event, j)
            search_counter += 1

        time.sleep(1)

    send_message(event, f"\n\nПоиск по {slice_2 if is_sliced else 'всем'} альбомам завершен. "
                 f"{'' if search_counter > 0 else 'Ничего не найдено.'}")



# check if url contains "album"
def is_url_album(url):
    r = re.search(r'album-', url)
    return r


def is_url_albums(url):
    r = re.search(r'albums-', url)
    return r


# longpoll vk listener loop
def listen():

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if is_url_album(event.obj.text):

                # create searcher object and call main func
                searcher = VKAlbumSearcher(str(event.obj.text).lower(), event, False)
                msg = searcher.find()
                for i in msg:
                    send_message(event, i)

            elif is_url_albums(event.obj.text):
                find_all(event.obj.text, event)

            else:
                send_message(event, 'Неправильная ссылка на альбом. Корректный пример:'
                                    ' https://vk.com/album-6923031_249426673'
                             )


while True:
    try:
        time.sleep(1)
        listen()
    except Exception as e:
        print("App crashed with ", e)