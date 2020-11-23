import vk_module
import re


class VKBoardSearcher:

    def __init__(self, query, event):

        self.offset: int = 0
        self.group_id: str = ''
        self.topic_id: str = ''
        self.query: str = query.lower()
        self.comments: dict = {}
        self.url: str = ''
        self.words: list = []
        self.words_str = ''
        self.event = event
        self.repeats: list = []
        self.MAX_MESSAGES: int = 50
        self.is_sliced: bool = False
        self.splitted_query: list = []

    def split_query(self):

        self.splitted_query = self.query.split()

        # must be 2 words in query: "url query"
        if len(self.splitted_query) < 2:
            vk_module.send_message(self.event,
                                   "Неккоректный запрос. Пример корректного запроса:"
                                   " https://vk.com/topic-104169151_32651830 мск питер"
                                   )
            raise ValueError("Split failed board")

        self.url = self.splitted_query[0]


    def find_slice(self):
        re_find_slice = re.match(r'.+\s(\[(\d+)\])\s.+', self.query)
        if re_find_slice:
            if int(re_find_slice.groups()[1]) == 0:
                vk_module.send_message(self.event, 'Нумерация страниц в обсуждении начинается'
                                                   ' с 1.Пример: https://vk.com/topic-104169151_38767969'
                                                   f' [1] запрос')
                raise ValueError("Slice is 0")
            self.offset = (int(re_find_slice.groups()[1]) - 1) * 20
            self.is_sliced = True

    def fill_words_list(self):
        if self.is_sliced:
            self.words += self.splitted_query[2:]
        else:
            self.words += self.splitted_query[1:]
        for i in self.words:
            self.words_str += i + ' '

    def find_group_and_board(self):

        re_group_topic = re.match(r'.+topic-(\d+)_(\d+)', self.url)

        if not re_group_topic:
            vk_module.send_message(self.event,
                                   "Неккоректная ссылка на альбом. Пример корректной ссылки:"
                                   " https://vk.com/topic-104169151_32651830 мск питер."
                                   )
            raise ValueError("Not valid URL board")

        self.group_id = re_group_topic.groups()[0]
        self.topic_id = re_group_topic.groups()[1]

    def make_response(self):

        try:
            service_response = vk_module.vk.board.getComments(group_id=self.group_id, topic_id=self.topic_id)
        except Exception as e:
            vk_module.send_message(self.event,
                                   "Не удалось получить комментарии к обсуждению."
                                   )
            raise ValueError("Get board comments failed with: ", e)
        number_of_pages = int((service_response['count'] - 1) / 20) + 1
        if int((self.offset + 21) / 20) > number_of_pages:
            vk_module.send_message(self.event, 'Такой страницы не существует. '
                                               f'Всего страниц в обсуждении:'
                                               f' {number_of_pages}.')
            raise ValueError("Page doesn't exist")
        all_comments_amount = service_response['count']
        iterator: int = (all_comments_amount // 100) + 1
        for i in range(iterator):
            try:
                response = vk_module.vk.board.getComments(group_id=self.group_id,
                                                          topic_id=self.topic_id,
                                                          count=100, offset=self.offset
                                                          )
            except Exception as e:
                vk_module.send_message(self.event,
                                       "Не удалось получить комментарии к обсуждению."
                                       )
                raise ValueError("Get board comments failed with: ", e)

            for item in response['items']:
                self.comments[item['text'].lower()] = f"https://vk.com/topic-" \
                                              f"{self.group_id}_{self.topic_id}?post="\
                                              + str(item['id'])
            if all_comments_amount - self.offset < 100:
                self.offset += all_comments_amount - self.offset
            else:
                self.offset += 100
        c = 1


    def find_words_in_comments(self):
        final_message: list = []
        counter = 1
        for word in self.words:
            for comment, url in self.comments.items():
                r = re.findall(word, comment)
                if r and (comment not in self.repeats):
                    final_message.append(f"&#128204; {counter}:\n&#128270; "
                                          f"Запрос: {word}\n&#128196; Текст: {str(comment)}\n"
                                          f"&#128206; Url: {str(url)}\n\n")
                    counter += 1
                    self.repeats.append(comment)
                    if len(final_message) > self.MAX_MESSAGES:
                        final_message = [(f"Комментариев слишком много (больше {self.MAX_MESSAGES}),"
                                          f" попробуйте сузить запрос.")]
                        return final_message
        if len(final_message) < 1:
            tmp = ''
            for word in self.words:
                tmp += word + ', '
            final_message.append(f"Комментарии по запросу '{tmp[0:-2]}' не найдены.")

        return final_message

    def find(self):
        self.split_query()
        self.find_slice()
        self.fill_words_list()
        self.find_group_and_board()
        self.make_response()
        return self.find_words_in_comments()


