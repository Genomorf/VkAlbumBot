import vk_module
import re
import time

class VKManyAlbumsSearcher:

    def __init__(self, query, event):
        self.query = query
        self.event = event
        self.is_sliced = False
        self.words: list = []
        self.words_str: str = ''
        self.group_id: str = ''
        self.url: str = ''
        self.slices: list = [0, 0]
        self.amount_of_albums = 0
        self.repeats: list = []
        self.MAX_MESSAGES: int = 50
        self.album_titles: dict = {}
        self.response_comments: dict = {}

    def split_query(self):
        splitted_query = self.query.split()
        if len(splitted_query) < 2:
            vk_module.send_message(self.event, "Неккоректный запрос. Пример корректного запроса:"
                                          " https://vk.com/albums-104169151 питер"
                                   )
            raise ValueError("Split failed")
        print(self.query, splitted_query)

        return splitted_query
    def get_url(self, splitted_query):
        self.url = splitted_query[0]
        # check if url is similar to "https://vk.com/ (albums) - (104169151) " pattern
        re_check = re.match(r'.+(albums)-(\d+)', self.url)
        if not re_check:
            vk_module.send_message(self.event, "Неккоректная ссылка на альбомы группы."
                                          " Пример корректной ссылки: https://vk.com/albums-104169151"
                                   )
            raise ValueError("Invalid url")
        print(self.url, re_check)
    def get_group_id(self):
        # find group id: "https://vk.com/albums- (104169151)"
        re_group_id = re.search(r'albums-(\w+)', self.url)
        self.group_id = '-' + re_group_id.groups(0)[0]
        print(re_group_id, self.group_id)
    def find_slice(self):
        re_find_slice = re.match(r'.+\s(\[(\d+)-(\d+)\])\s.+', self.query)
        self.slices = []
        if re_find_slice:
            self.is_sliced = True
            self.slices += [int(re_find_slice.groups()[1]), int(re_find_slice.groups()[2])]
        print(re_find_slice, self.slices)
    def get_words(self, splitted_query):
        if self.is_sliced:
            self.words += splitted_query[2:]
        else:
            self.words += splitted_query[1:]
        for i in self.words:
            self.words_str += i.lower() + " "
        print(self.words, self.words_str)
    def make_slice(self, query, event):

        slice_1 = self.slices[0]
        slice_2 = self.slices[1]
        is_sliced = False

        # if slice is found - init slice variables and words
        if self.is_sliced:

            # check if slice variables are in the correct order
            # words and f-string need to help user fix his query
            if slice_1 > slice_2:
                vk_module.send_message(event, "Неккоретный запрос. "
                                              "Пример корректного запроса: " +
                                       f"https://vk.com/albums-104169151 "
                                       f"[{slice_2}-{slice_1}] {self.words}")
                raise ValueError("Slice failed")

    def make_response(self):

        response = vk_module.vk.photos.getAlbums(owner_id=self.group_id)

        for i in response['items']:
            self.album_titles[str(i['id'])] = str(i['title'])
        query_list = []

        # choose only required albums if slice exists
        # dict: {"https://vk.com/album-(group_id)_(photo_id) query_words" : album_title}
        # e.g.: {"https://vk.com/album-6923031_2494266731 moscow spb" : album1}
        if self.is_sliced:
            for i in response['items'][self.slices[0]: self.slices[1]]:
                query_list.append(i["id"])
                self.amount_of_albums += 1
        # choose all
        else:
            for i in response['items']:
                query_list.append(i["id"])
                self.amount_of_albums += 1

        for i in query_list:
            print(i)
        # check if amount of albums is to high to not spam
        if len(query_list) > 50:
            vk_module.send_message(self.event,
                                   "Слишком много альбомов - больше 50. Используйте выборку, например: "
                                   f"{self.url} [0-30] {self.words_str}")
            raise ValueError("Too many albums")

        return query_list

    def make_many_responses(self, query_list):

        # search_counter needs to change message if nothing was found
        search_counter = 0

        response_photos = {}
        iterator = (self.amount_of_albums // 10) + 1
        counter = [0, 10]
        for i in range(iterator):
            with vk_module.vk_api.VkRequestsPool(vk_module.vk_admin) as pool:
                for album in query_list[counter[0]: counter[1]]:
                    self.response_comments[str(album)] = pool.method('photos.getAllComments',
                                             {'owner_id': self.group_id, 'album_id': album, 'max_count': 100})
                    response_photos[str(album)] = pool.method('photos.get',
                                              {'owner_id': self.group_id, 'album_id': album, 'count': 900})
            counter[0] += 10
            counter[1] += 10
            print(counter)
        for album, response in self.response_comments.items():
            self.response_comments[album] = response.result

        for album, response in response_photos.items():
            response_photos[album] = response.result

        self.response_comments.update(response_photos)
        for i, j in self.response_comments.items():
            print(i, j)
        print(len(self.response_comments))
        for i in self.response_comments.values():
            for j in i['items']:
                print(j['text'])

    def find_comments(self):
        counter = 1
        final_message: list = []
        for word in self.words:
            for album_id, comments in self.response_comments.items():
                for comment in comments['items']:
                    r = re.findall(str(word).lower(), comment['text'].lower())
                    if r and (comment['text'].lower() not in self.repeats):
                        final_message.append(f"Альбом: {self.album_titles[album_id]}"
                                             f"&#128204; {counter}:\n&#128270; "
                                             f"Запрос: {word}\n&#128196; Текст: {str(comment['text'].lower())}\n"
                                             f"&#128206; Url: 'https://vk.com/photo-'"
                                             f"{self.group_id}_{str(album_id)}\n\n")

                        # append commend to repeats list to not send similar messages
                        self.repeats.append(comment['text'].lower())
                        counter += 1
                        if len(final_message) > self.MAX_MESSAGES:
                            final_message = [(f""
                                             f"Комментариев слишком много (больше {self.MAX_MESSAGES}),"
                                              f" попробуйте сузить запрос.")]
                            return final_message
        if len(final_message) < 1:
            tmp = ''
            for word in self.words:
                tmp += word + ', '
            final_message.append(f"Комментарии по запросу '{tmp[0:-2]}' не найдены.")

        print(final_message)
        return final_message

        # vk_module.send_message(self.event, f"Выполняется поиск по "
        #                                    f"{self.slices[1] if self.is_sliced else 'всем'}"
        #                                    f" альбомам группы...")
        # vk_module.send_message(self.event, f"\n\nПоиск по "
        #                                    f"{self.slices[1] if self.is_sliced else 'всем'} "
        #                                    f"альбомам завершен. "
        #                                    f"{'' if search_counter > 0 else 'Ничего не найдено.'}")
    def find(self):
        q = self.split_query()
        self.get_url(q)
        self.get_group_id()
        self.find_slice()
        self.get_words(q)
        query = self.make_response()
        self.make_many_responses(query)
        return self.find_comments()
