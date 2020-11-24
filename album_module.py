import vk_module
import re
# main class of comment searcher
class VKAlbumSearcher:

    def __init__(self, query_string, event):

        self.MAX_MESSAGES = 50
        self.group = ''
        self.album = ''
        self.url = ''
        self.query_string = query_string
        self.comments = {}
        self.words = []
        self.words_str = ''
        self.repeats = []
        self.event = event

    def split_query(self):

        splitted_query_string = self.query_string.split()

        # must be 2 words in query: "url query"
        if len(splitted_query_string) < 2:
            vk_module.send_message(self.event,
                                   "Неккоректный запрос. Пример корректного запроса:"
                                   " https://vk.com/album-6923031_249426673 мск питер"
                                   )
            raise ValueError("Split failed")

        return splitted_query_string

    def get_url_from_query(self, splitted_query_string):
        # get url from query
        self.url = splitted_query_string[0]

    def get_words_from_query(self, splitted_query_string):
        # get query words from query
        self.words = splitted_query_string[1:]
        for i in self.words:
            self.words_str += i


    def find_group_and_album_url(self):

        # find any letters after "-" like "-111111_222222"
        re_group_and_album = re.search(r'-\w+', self.url)
        re_group_and_album_match = re_group_and_album.group(0)

        # find 2 groups of letters in re_group_and_album like "111111" and "222222"
        re_group_and_album_parts = re.match(r'-(\w+)_(\w+)', re_group_and_album_match)

        # throw error if both reg exps are empty
        if not re_group_and_album or not re_group_and_album_parts:
            vk_module.send_message(self.event,
                                   "Неккоректная ссылка на альбом. Пример корректной ссылки:"
                                   " https://vk.com/album-6923031_249426673."
                                   )
            raise ValueError("Not valid URL")

        self.group = re_group_and_album_parts.groups()[0]
        self.album = re_group_and_album_parts.groups()[1]

        # print("Group: ", self.group, '\n',
        #       "Album: ", self.album, '\n')

    def get_album_comments(self):

        # check if group and album are convertable
        try:
            group_id = int('-' + self.group)
            album_id = int(self.album)
        except ValueError as VE:
            vk_module.send_message(self.event,
                                   "Неккоректная ссылка на альбом. Пример корректной ссылки: "
                                   "https://vk.com/album-6923031_249426673."
                                   )
            raise ValueError("can't change int to str: ", VE)

        tools = vk_module.vk_api.VkTools(vk_module.vk)
        response = {}

        # main request from vk.com API
        try:
            # for i in range(iterator):
            #     with vk_module.vk_api.VkRequestsPool(vk_module.vk_admin) as pool:
            #         for album in query_list[counter[0]: counter[1]]:
            # comments under photos
            pools1 = {}
            pools2 = {}
            with vk_module.vk_api.VkRequestsPool(vk_module.vk_admin) as pool:

                    pools1['first'] = pool.method('photos.getAllComments',
                                                                     {'owner_id': group_id, 'album_id': album_id,
                                                                      'max_count': 100})
                    pools2['second'] = pool.method('photos.get',
                                                              {'owner_id': group_id, 'album_id': album_id,
                                                               'count': 900})
            # response_part_1 = tools.get_all_iter(method='photos.getAllComments',
            #                                      max_count=100,
            #                                      values={'owner_id': group_id, 'album_id': album_id})
            #
            # # comments from photos
            # response_part_2 = vk_module.vk.photos.get(owner_id=group_id, album_id=album_id, count=900)

        except Exception as e:
            vk_module.send_message(self.event,
                                   "Не удалось получить комментарии к альбому."
                                   )
            raise ValueError("Get album comments failed with: ", e)

        response = {}
        for album, a in pools1.items():
            pools1[album] = a.result

        for album, a in pools2.items():
            pools2[album] = a.result

        response_part_1 = pools1['first']
        response_part_2 = pools2['second']

        # dictionary: {comment_text: https://vk.com/photo-(group_id)_(photo_id)}
        for i in response_part_1['items']:
            response[f" \"{i['text'].lower()}\" "] = f"https://vk.com/photo-{str(self.group)}"\
                                                     f"_{str(i['pid'])}"
        for i in response_part_2['items']:
            response[f" \"{i['text'].lower()}\" "] = f"https://vk.com/photo-{str(self.group)}"\
                                                     f"_{str(i['id'])}"

        # check if album has no comments
        if len(response) < 1:
            vk_module.send_message(self.event,
                         f"Комментарии в альбоме не найдены."
                         )
            raise ValueError("Response is empty")

        self.comments = response

    def find_in_comments(self):

        final_message = []

        # counter - is number at the beginning of final message
        counter = 1

        # for every word in list find this word in comments
        for word in self.words:
            for comment, url in self.comments.items():
                r = re.findall(f'{word}', comment)

                # if word is found and comment was never sent -
                # add comment, album title, counter and word to the final message
                if r and (comment not in self.repeats):
                    final_message.append(f"&#128204; {counter}:\n&#128270; "
                                         f"Запрос: {word}\n&#128196; Текст: {str(comment)}\n"
                                         f"&#128206; Url: {str(url)}\n\n")

                    # append commend to repeats list to not send similar messages
                    self.repeats.append(comment)
                    counter += 1

                    # check length of final message to not spam
                    if len(final_message) > self.MAX_MESSAGES:
                        final_message = [(f"Комментариев слишком много (больше {self.MAX_MESSAGES}),"
                                          f" попробуйте сузить запрос.")]
                        return final_message

        # skip this error if search in more than 1 album to prevent spam

        # check if empty
        if len(final_message) < 1:
            tmp = ''
            for word in self.words:
                tmp += word + ', '
            final_message.append(f"Комментарии по запросу '{tmp[0:-2]}' не найдены.")

        return final_message

    def find(self):
        # main function
        splitted_query = self.split_query()
        self.get_url_from_query(splitted_query)
        self.get_words_from_query(splitted_query)
        self.find_group_and_album_url()
        self.get_album_comments()
        return self.find_in_comments()

