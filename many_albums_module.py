import vk_module
import re


class VKManyAlbumsSearcher:

    def __init__(self, query: str, event):
        self.query: str = query
        self.event = event
        self.is_sliced: bool = False
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

        self.ERROR_MSG_URL: str = "Неккоректная ссылка на альбомы группы." \
                                  "Пример корректной ссылки: https://vk.com/albums-104169151"
        self.ERROR_MSG_QUERY: str = "Неккоректный запрос. Пример корректного запроса:"\
                                    " https://vk.com/albums-104169151 питер"
        self.ERROR_MSG_QUERY_SLICE: str = f"Неккоретный запрос. "\
                                          f"Пример корректного запроса: "\
                                          f"https://vk.com/albums-104169151 "


    def split_query(self) -> list:
        splitted_query: list = self.query.split()
        if len(splitted_query) < 2:
            vk_module.send_message(self.event, self.ERROR_MSG_QUERY)
            raise ValueError("Split failed")

        return splitted_query

    def get_url(self, splitted_query: list) -> bool:

        self.url = splitted_query[0]

        # check if url is similar to "https://vk.com/ (albums) - (104169151) " pattern
        re_check = re.match(r'.+(albums)-(\d+)', self.url)

        if not re_check:
            vk_module.send_message(self.event, self.ERROR_MSG_URL)
            raise ValueError("Invalid url")

        return True

    def get_group_id(self) -> bool:

        # find group id: "https://vk.com/albums- (104169151)"
        re_group_id = re.search(r'albums-(\w+)', self.url)

        if not re_group_id:
            vk_module.send_message(self.event, self.ERROR_MSG_URL)
            raise ValueError("Invalid url")

        self.group_id = '-' + re_group_id.groups(0)[0]

        return True

    def find_slice(self) -> bool:
        re_find_slice = re.match(r'.+\s(\[(\d+)-(\d+)\])\s.+', self.query)
        re_find_slice_error = re.match(r'.+\s(\[(\d+)-(\d+)\])', self.query)

        # check for an invalid query: "https://vk.com/albums-104169151 [0-10]"
        if re_find_slice_error and not re_find_slice:
            vk_module.send_message(self.event, self.ERROR_MSG_QUERY_SLICE +
                                   f"[0-20]")
            raise ValueError("Invalid url")

        if re_find_slice:
            self.is_sliced = True
            self.slices = [int(re_find_slice.groups()[1]), int(re_find_slice.groups()[2])]

        return True

    def get_words(self, splitted_query: list) -> bool:
        # self.words depends on slice factor
        if self.is_sliced:
            self.words += splitted_query[2:]
        else:
            self.words += splitted_query[1:]

        for i in self.words:
            self.words_str += f"{i.lower()} "

        # check the correct order of slices:
        # Correct: [0-10]
        # Incorrect: [10-0]
        if self.is_sliced:
            if self.slices[0] > self.slices[1]:
                vk_module.send_message(self.event, self.ERROR_MSG_QUERY_SLICE +\
                                       f"[{self.slices[1]}-{self.slices[0]}] {self.words_str}")
                raise ValueError("Slice failed")

        return True

    def make_response(self) -> list:

        try:
            response: dict = vk_module.vk.photos.getAlbums(owner_id=self.group_id)
        except Exception as e:
            vk_module.send_message(self.event, "Не удалось получить комментарии к альбому.")
            raise ValueError('Response failed with ', e)

        max_albums: int = response['count']
        if self.is_sliced:
            if self.slices[0] > max_albums + 1 or self.slices[1] > max_albums + 1:
                vk_module.send_message(self.event, f"Выбрано больше, альбомов, чем есть в группе. "
                                                   f"Всего альбомов {max_albums}.")
                raise ValueError('Slice is bigger than max albums ')

        # get album titles from response
        for i in response['items']:
            self.album_titles[str(i['id'])] = str(i['title'])
        query_list: list = []

        '''
        choose only required albums if slice exists
        dict: {"https://vk.com/album-(group_id)_(photo_id) query_words" : album_title}
        e.g.: {"https://vk.com/album-6923031_2494266731 moscow spb" : album1}
        amount of albums needs to make response later
        '''
        if self.is_sliced:
            for i in response['items'][self.slices[0]: self.slices[1]]:
                query_list.append(i["id"])
                self.amount_of_albums += 1
        # choose all
        else:
            for i in response['items']:
                query_list.append(i["id"])
                self.amount_of_albums += 1

        # check if amount of albums is to high to avoid spam and captcha
        if len(query_list) > 50:
            vk_module.send_message(self.event,
                                   "Слишком много альбомов - больше 50. Используйте выборку, например: "
                                   f"{self.url} [0-30] {self.words_str}")
            raise ValueError("Too many albums")

        return query_list

    def make_many_responses(self, query_list: list) -> bool:

        response_photos: dict = {}

        '''
        VkRequestPool can only make 25 responses at one iteration.
        Here pool makes 20 responses per iteration.
        Counter slices query_list to 10 urls.
        Iterator moves counter values.
        If amount of albums = 35, than iterator = 4 and
        there will be 4 VkRequestPoll calls.
        '''
        iterator: int = (self.amount_of_albums // 10) + 1
        counter: list = [0, 10]

        for i in range(iterator):
            try:
                with vk_module.vk_api.VkRequestsPool(vk_module.vk_admin) as pool:
                    for album in query_list[counter[0]: counter[1]]:
                        self.response_comments[str(album)] = pool.method('photos.getAllComments',
                                                 {'owner_id': self.group_id, 'album_id': album, 'max_count': 100})
                        response_photos[str(album)] = pool.method('photos.get',
                                                  {'owner_id': self.group_id, 'album_id': album, 'count': 900})
                counter[0] += 10
                counter[1] += 10
            except Exception as e:
                if str(e) == '[13] Runtime error occurred during code invocation: response size is too big':
                    vk_module.send_message(self.event, 'Не удалось получить комментарии к альбому. '
                                                       'Альбомы слишком большие. Попробуйте искать '
                                                       'в каждом альбоме отдельно.')
                else:
                    vk_module.send_message(self.event, 'Не удалось получить комментарии к альбому. ')
                raise ValueError('Many responses failed with', str(e))

        # Need to convert result from VkRequestPool to dict
        for album, response in self.response_comments.items():
            self.response_comments[album] = response.result

        for album, response in response_photos.items():
            response_photos[album] = response.result

        self.response_comments.update(response_photos)

        return True

    def find_comments(self) -> list:
        # counter is a number of comment in final message
        counter: int = 1

        final_message: list = []

        '''
        word in words_list "питер москва сочи"
        album_id, comments in {'album_id' : {'count': 23, 'items' : {...}, ... } }
        comment in [{'id': 2, 'text': 'питер'}, {'id': 3, 'text': 'сочи'}, ...]
        find 'питер' in comment['text': 'питер']
        add to final message and repeats_list
        raise error if final_message is to long
        '''
        for word in self.words:
            for album_id, comments in self.response_comments.items():
                for comment in comments['items']:
                    r = re.findall(str(word).lower(), comment['text'].lower())
                    if r and (comment['text'].lower() not in self.repeats):
                        final_message.append(f"Альбом: {self.album_titles[album_id]}"
                                             f"&#128204; {counter}:\n&#128270; "
                                             f"Запрос: {word}\n&#128196; Текст: {str(comment['text'].lower())}\n"
                                             f"&#128206; Url: https://vk.com/photo"
                                             f"{self.group_id}_{str(comment['id'])}\n\n")

                        # append commend to repeats list to not send similar messages
                        self.repeats.append(comment['text'].lower())
                        counter += 1

                        if len(final_message) > self.MAX_MESSAGES:
                            final_message = [(f""
                                             f"Комментариев слишком много (больше {self.MAX_MESSAGES}),"
                                              f" попробуйте сузить запрос.")]
                            return final_message
        if len(final_message) < 1:
            tmp: str = ''
            for word in self.words:
                tmp += word + ', '
            final_message.append(f"Комментарии по запросу '{tmp[0:-2]}' не найдены.")

        return final_message

    def find(self) -> list:
        q: list = self.split_query()
        assert self.get_url(q), 'Get url failed'
        assert self.get_group_id(), 'Get group failed'
        assert self.find_slice(), 'Find slice failed'
        assert self.get_words(q), 'Get words failed'
        query = self.make_response()
        assert self.make_many_responses(query), 'Make response failed'
        return self.find_comments()
