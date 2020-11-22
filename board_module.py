import vk_module


import re


class VKBoardSearcher:

    def __init__(self, query, event):

        self.group_id: str = ''
        self.topic_id: str = ''
        self.query: str = query.lower()
        self.comments: dict = {}
        self.url: str = ''
        self.words: list = []
        self.event = event
        self.repeats: list = []
        self.MAX_MESSAGES: int = 50

    def split_query(self):

        splitted_query: list = self.query.split()

        # must be 2 words in query: "url query"
        if len(splitted_query) < 2:
            vk_module.send_message(self.event,
                                   "Неккоректный запрос. Пример корректного запроса:"
                                   " https://vk.com/topic-104169151_32651830 мск питер"
                                   )
            raise ValueError("Split failed board")

        self.url = splitted_query[0]
        self.words += splitted_query[1:]

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

        comments_dict: dict = {}

        try:
            response = vk_module.vk.board.getComments(group_id=self.group_id, topic_id=self.topic_id)
        except Exception as e:
            vk_module.send_message(self.event,
                                   "Не удалось получить комментарии к обсуждению."
                                   )
            raise ValueError("Get board comments failed with: ", e)

        for i in response['items']:
            comments_dict[i['text']] = i['id']

        for comment, Id in comments_dict.items():
            self.comments[comment] = f"https://vk.com/topic-" \
                                     f"{self.group_id}_{self.topic_id}" \
                                     f"?post={Id}"
        for i in comments_dict.keys():
            print(i)
    def find_words_in_comments(self):
        final_message: list = []
        counter = 1
        for word in self.words:
            for comment, url in self.comments.items():
                r = re.findall(f'{word}', comment)
                if r and (comment not in self.repeats):
                    final_message.append((f"&#128204; {counter}:\n&#128270; "
                                          f"Запрос: {word}\n&#128196; Текст: {str(comment)}\n"
                                          f"&#128206; Url: {str(url)}\n\n"))
                    counter +=1
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
        self.find_group_and_board()
        self.make_response()
        return self.find_words_in_comments()


