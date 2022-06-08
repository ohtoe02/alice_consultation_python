import re

introductions = {
    'edu_form': 'Форма обучения: ',
    'price': 'Контрактное обучение стоит: ',
    'budget_places': 'Всего бюджетных мест: ',
    'leader': 'Руководитель направления: ',
    'pass_score': 'Проходной балл ЕГЭ в прошлом году был: ',
    'number': 'Номер направления: ',
}


def get_brief_info(course):
    text = [[f'{course["title"]}\n \n'],
            [f'{course["short_description"]}\n\n'],
            [f'{introductions["edu_form"]}', f'{course["params"]["edu_form"]}\n\n'],
            [f'{introductions["price"]}', f'{course["params"]["price"]}', f' ₽\n\n'],
            [f'{introductions["budget_places"]}', f'{course["params"]["budget_places"]}\n\n'],
            [f'{introductions["pass_score"]}', f'{course["params"]["pass_score"]}']]
            # [f'{introductions["leader"]}', f'{course["params"]["leader"]}']]

    res = []
    for item in text:
        if len(item) > 1 and item[1].replace('\n', '') == '':
            continue
        res.append(''.join(item))

    return ''.join(res)


def get_param_info(course, phrase):
    text_params = [
        (r'подробн\w* описан\w*|подробне\w*|поподробн\w*',
         [f'{course["title"]}:\n\n', f'{course["full_description"]}']),
        (r'цен\w*|стоимост\w*|стои\w*|денег|деньг\w*',
         [f'{course["title"]}:\n\nСтоимость обучения обойдется в ', f'{course["params"]["price"]}', ' ₽']),
        (r'ном\w*',
         [f'{course["title"]}:\n\nНомер направления: ', f'{course["number"]}']),
        (r'бюдж\w* мест\w*|мест\w*',
         [f'{course["title"]}:\n\nБюджетных мест на направлении: ', f'{course["params"]["budget_places"]}']),
        (r'прох\w* бал\w*|бал\w*',
         [f'{course["title"]}:\n\nПроходной балл в прошлом году был: ', f'{course["params"]["pass_score"]}']),
        (r'форм\w* обуч\w*',
         [f'{course["title"]}:\n\nФорма обучения на направлении: ', f'{course["params"]["edu_form"]}']),
        (r'руковод\w*|заведующ\w*|главн\w*',
         [f'{course["title"]}:\n\nРуководитель направления: ', f'{course["params"]["leader"]}']),
    ]

    for pattern, value in text_params:
        if re.search(pattern, phrase):
            return ''.join(value) if value[1] != '' else 'У выбранной дисциплины отсутствует такой параметр'
    return None
