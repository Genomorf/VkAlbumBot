import vk_module
import re


# main class of comment searcher
class VKAlbumSearcher:

    def __init__(self, query_string, event):

        self.MAX_MESSAGES: int = 50
        self.group: str = ''
        self.album: str = ''
        self.url: str = ''
        self.query_string: str = query_string
        self.comments: dict = {}
        self.words: list = []
        self.words_str: str = ''
        self.repeats: list = []
        self.event = event

    def split_query(self) -> list:

        splitted_query_string: list = self.query_string.split()

        # must be 2 words in query: "url query"
        if len(splitted_query_string) < 2:
            vk_module.send_message(self.event,
                                   "Неккоректный запрос. Пример корректного запроса:"
                                   " https://vk.com/album-6923031_249426673 мск питер"
                                   )
            raise ValueError("Split failed")

        return splitted_query_string

    def get_url_from_query(self, splitted_query_string: list) -> None:
        # get url from query
        self.url = splitted_query_string[0]

    def get_words_from_query(self, splitted_query_string: list) -> None:
        # get query words from query
        self.words = splitted_query_string[1:]
        for i in self.words:
            self.words_str += i

    def find_group_and_album_url(self) -> None:

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

    def get_album_comments(self) -> None:

        group_id = '-' + self.group
        album_id = self.album

        # main request from vk.com API
        try:
            comments_under_photos: dict = {}
            comments_from_photos: dict = {}
            with vk_module.vk_api.VkRequestsPool(vk_module.vk_admin) as pool:

                comments_under_photos['first'] = pool.method('photos.getAllComments',
                                                             {'owner_id': group_id, 'album_id': album_id,
                                                              'max_count': 100})
                comments_from_photos['second'] = pool.method('photos.get',
                                                             {'owner_id': group_id, 'album_id': album_id,
                                                              'count': 900})
        except Exception as e:
            vk_module.send_message(self.event,
                                   "Не удалось получить комментарии к альбому."
                                   )
            raise ValueError("Get album comments failed with: ", e)

        final_response: dict = {}

        # VkRequestPoll returns dict that should be converted
        # to a normal response with .result
        for album, res in comments_under_photos.items():
            comments_under_photos[album] = res.result

        for album, res in comments_from_photos.items():
            comments_from_photos[album] = res.result

        response_part_1: dict = comments_under_photos['first']
        response_part_2: dict = comments_from_photos['second']

        # dictionary: {comment_text: https://vk.com/photo-(group_id)_(photo_id)}
        for i in response_part_1['items']:
            final_response[f" \"{i['text'].lower()}\" "] = f"https://vk.com/photo-{str(self.group)}" \
                                                     f"_{str(i['pid'])}"
        for i in response_part_2['items']:
            final_response[f" \"{i['text'].lower()}\" "] = f"https://vk.com/photo-{str(self.group)}" \
                                                     f"_{str(i['id'])}"

        # check if album has no comments
        if len(final_response) < 1:
            vk_module.send_message(self.event,
                                   f"Комментарии в альбоме не найдены."
                                   )
            raise ValueError("Response is empty")

        self.comments = final_response

    def find_in_comments(self) -> list:

        final_message: list = []

        # counter - is a number at the beginning of final message
        counter: int = 1

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
        # check if empty
        if len(final_message) < 1:
            tmp: str = ''
            for word in self.words:
                tmp += word + ', '
            final_message.append(f"Комментарии по запросу '{tmp[0:-2]}' не найдены.")

        return final_message

    def find(self) -> list:
        # main function
        splitted_query: list = self.split_query()
        self.get_url_from_query(splitted_query)
        self.get_words_from_query(splitted_query)
        self.find_group_and_album_url()
        self.get_album_comments()
        return self.find_in_comments()
