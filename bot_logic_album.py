# -*- coding: utf-8 -*-
import re
import time
import vk_module
import threading
import album_module
import board_module
import many_albums_module

def find_in_one_album(query, event):

    searcher = album_module.VKAlbumSearcher(str(query).lower(), event)
    msg = searcher.find()
    words = searcher.words_str
    vk_module.send_message(event, f"Выполняется поиск '{words}' в альбоме...")
    buffer = ''
    for i in msg:
        buffer += i
        if len(buffer) > 3000:
            vk_module.send_message(event, buffer)
            buffer = ''
    if buffer:
        vk_module.send_message(event, buffer)
    vk_module.send_message(event, "Поиск завершен.")

def find_in_many_albums(query, event):
    searcher = many_albums_module.VKManyAlbumsSearcher(str(query).lower(), event)
    msg = searcher.find()
    words = searcher.words_str
    vk_module.send_message(event, f"Выполняется поиск '{words}' в "
                                  f"{searcher.slices[1] if searcher.is_sliced else ''}"
                                  f" альбомах...")
    buffer = ''
    for i in msg:
        buffer += i
        if len(buffer) > 3000:
            vk_module.send_message(event, buffer)
            buffer = ''
    if buffer:
        vk_module.send_message(event, buffer)
    vk_module.send_message(event, "Поиск завершен.")

def find_in_one_topic(query,  event):

    searcher = board_module.VKBoardSearcher(str(query).lower(), event)
    msg = searcher.find()
    words = searcher.words_str
    vk_module.send_message(event, f"Выполняется поиск '{words}' в обсуждении...")
    buffer = ''
    for i in msg:
        buffer += i
        if len(buffer) > 3000:
            vk_module.send_message(event, buffer)
            buffer = ''
    if buffer:
        vk_module.send_message(event, buffer)
    vk_module.send_message(event, "Поиск завершен.")


# def find_in_many_albums(query, event):
#
#     splitted_query = query.split()
#     if len(splitted_query) < 2:
#         vk_module.send_message(event, "Неккоректный запрос. Пример корректного запроса:"
#                                       " https://vk.com/albums-104169151 питер"
#                                )
#         raise ValueError("Split failed")
#
#     # "https://vk.com/albums-104169151"
#     url = splitted_query[0]
#
#     # check if url is similar to "https://vk.com/ (albums) - (104169151) " pattern
#     re_check = re.match(r'.+(albums)-(\d+)', url)
#     if not re_check:
#         vk_module.send_message(event, "Неккоректная ссылка на альбомы группы."
#                                       " Пример корректной ссылки: https://vk.com/albums-104169151"
#                                )
#         raise ValueError("Invalid url")
#
#     # find in query slice signs: "https://vk.com/albums-104169151 ( [ (0) - (10) ] ) query_words"
#     re_find_slice = re.match(r'.+\s(\[(\d+)-(\d+)\])\s.+', query)
#
#     words = []
#     slice_1 = 0
#     slice_2 = 0
#     is_sliced = False
#
#     # if slice is found - init slice variables and words
#     if re_find_slice:
#         words += splitted_query[2:]
#         slice_1 += int(re_find_slice.groups()[1])
#         slice_2 += int(re_find_slice.groups()[2])
#
#         # check if slice variables are in the correct order
#         # words and f-string need to help user fix his query
#         words_in_message = ''
#         for i in words:
#             words_in_message += i.lower() + ', '
#         if slice_1 > slice_2:
#             vk_module.send_message(event, "Неккоретный запрос. "
#                                           "Пример корректного запроса: " +
#                                           f"https://vk.com/albums-104169151 "
#                                           f"[{slice_2}-{slice_1}] {words_in_message[0:-2]}")
#             raise ValueError("Slice failed")
#         # bool flag to change settings later
#         is_sliced = True
#     else:
#         words += splitted_query[1:]
#     words_str = ''
#     for i in words:
#         words_str += ' ' + i.lower()
#
#     # find group id: "https://vk.com/albums- (104169151)"
#     re_group_id = re.search(r'albums-(\w+)', url)
#     group_id = '-' + re_group_id.groups(0)[0]
#
#     response = vk_module.vk.photos.getAlbums(owner_id=group_id)
#     query_list = {}
#
#     # choose only required albums if slice exists
#     # dict: {"https://vk.com/album-(group_id)_(photo_id) query_words" : album_title}
#     # e.g.: {"https://vk.com/album-6923031_2494266731 moscow spb" : album1}
#     if is_sliced:
#         for i in response['items'][slice_1: slice_2]:
#             query_list[(f'https://vk.com/album{group_id}_' + str(i['id']) + words_str)] \
#                 = i['title']
#     # choose all
#     else:
#         for i in response['items']:
#             query_list[(f'https://vk.com/album{group_id}_' + str(i['id']) + words_str)] \
#                 = i['title']
#
#     # for i in query_list:
#     #     print(i)
#     # check if amount of albums is to high to not spam
#     if len(query_list.items()) > 50:
#         vk_module.send_message(event,
#                                "Слишком много альбомов - больше 50. Используйте выборку, например: "
#                                f"{url} [0-30] {words_str}")
#         raise ValueError("Too many albums")
#
#     vk_module.send_message(event, f"Выполняется поиск по {slice_2 if is_sliced else 'всем'} альбомам группы...")
#
#     # search_counter needs to change message if nothing was found
#     search_counter = 0
#     # find comments with VKAlbumSearcher class in query_list.keys()
#     # query_list.values() are album titles and they need in information messages to user
#     for url_key, album_title_value in query_list.items():
#         searcher = album_module.VKAlbumSearcher(str(url_key).lower(), event, True, album_title_value)
#         msg = searcher.find()
#
#         buffer = ''
#         for i in msg:
#             search_counter += 1
#             buffer += i
#             if len(buffer) > 3000:
#                 vk_module.send_message(event, buffer)
#                 buffer = ''
#         if buffer:
#             vk_module.send_message(event, buffer)
#
#
#         time.sleep(1)
#
#     vk_module.send_message(event, f"\n\nПоиск по {slice_2 if is_sliced else 'всем'} альбомам завершен. "
#                                   f"{'' if search_counter > 0 else 'Ничего не найдено.'}")


def type_of_request(url):
    r1 = re.search(r'album-', url)
    if r1: return 'album'
    r2 = re.search(r'albums-', url)
    if r2: return 'albums'
    r3 = re.search(r'topic-', url)
    if r3: return 'topic'


# longpoll vk listener loop
def answer(event):

    if type_of_request(event.obj.text) == 'album':
        find_in_one_album(event.obj.text, event)

    elif type_of_request(event.obj.text) == 'albums':
        find_in_many_albums(event.obj.text, event)

    elif type_of_request(event.obj.text) == 'topic':
        find_in_one_topic(event.obj.text, event)
    else:
        vk_module.send_message(event, 'Неправильная ссылка на альбом. Корректный пример:'
                                      ' https://vk.com/album-6923031_249426673')


def listen():

    for event in vk_module.longpoll.listen():
        if event.type == vk_module.VkBotEventType.MESSAGE_NEW:
            t1 = threading.Thread(target=answer, args=(event,))
            t1.start()


# infinite loop for random crashes with error ignoring
while True:
    try:
        time.sleep(1)
        listen()
    except Exception as e:
        print("App crashed with ", e)