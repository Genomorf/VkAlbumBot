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