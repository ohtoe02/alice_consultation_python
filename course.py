import re


class Course:
    introductions = {
        'edu_form': 'Форма обучения: ',
        'price': 'Контрактное обучение стоит: ',
        'budget_places': 'Всего бюджетных мест: ',
        'leader': 'Руководитель направления: ',
        'pass_score': 'Проходной балл ЕГЭ в прошлом году был: ',
        'number': 'Номер направления: ',
    }



    def __init__(
            self,
            title=None,
            short_description=None,
            full_description=None,
            tags=None,
            budget_places=None,
            pass_score=None,
            edu_form=None,
            number=None,
            price=None,
            exams=None,
            leader=None,
            professions=None,
            special_addons=None
    ):
        self.title = title
        self.number = number
        self.short_description = short_description
        self.full_description = full_description
        self.price = price
        self.tags = tags
        self.budget_places = budget_places
        self.pass_score = pass_score
        self.exams = exams
        self.edu_form = edu_form
        self.leader = leader
        self.professions = professions
        self.special_addons = special_addons

    def get_brief_info(self):
        return f'{self.title}\n\n' \
               f'{self.short_description}\n\n' \
               f'{self.introductions["edu_form"]}{self.edu_form}\n\n' \
               f'{self.introductions["price"]}{self.price} ₽\n\n' \
               f'{self.introductions["budget_places"]}{self.budget_places}\n\n' \
               f'{self.introductions["pass_score"]}{self.pass_score} '

    def get_professions_string(self):
        return ";\n".join(self.professions)

    def get_param_info(self, phrase):
        text_params = [
            (r'подробн\w* описан\w* | подробне\w* | поподробн\w*', f'{self.title}\n\nПодробное описание:\n{self.full_description}'),
            (r'цен\w* | стои\w* | денег | деньг\w*', f'{self.title}\n\nСтоимость обучения обойдется в \n{self.price} ₽'),
            (r'ном\w*', f'{self.title}\n\nНомер направления: {self.number}'),
            (r'бюдж\w* мест\w*', f'{self.title}\n\nБюджетных мест на направлении: {self.budget_places}'),
            (r'прох\w* бал\w*', f'{self.title}\n\nПроходной балл в прошлом году был: {self.pass_score}'),
            (r'форм\w* обуч\w*', f'{self.title}\n\nФорма обучения на направлении: {self.edu_form}')
        ]

        for pattern, value in text_params:
            if re.search(pattern, phrase):
                return value
        return None

    def get_params(self):
        return {
            "price": self.price,
            "budget_place": self.budget_places,
            "pass_score": self.pass_score,
            "exams": self.exams,
            "edu_form": self.edu_form
        }

    def __str__(self):
        return self.title
