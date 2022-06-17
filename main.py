import datetime
import logging
import re
import string
from langdetect import detect

import pyrebase
import math

from aiohttp import web
from aioalice import Dispatcher, get_new_configured_app, types
from aioalice.dispatcher import MemoryStorage, SkipHandler
from aioalice.utils.helper import Helper, HelperMode, Item

from course import get_brief_info, get_param_info

WEBHOOK_URL_PATH = '/consultation-service/'  # webhook endpoint

WEBAPP_HOST = 'localhost'
WEBAPP_PORT = 3001

firebase_config = {
    "apiKey": "AIzaSyC7DIzFCt02mY2KhW8FAmw6n5qp8jTHx38",
    "authDomain": "alice-consultation-skill.firebaseapp.com",
    "databaseURL": "https://alice-consultation-skill-default-rtdb.europe-west1.firebasedatabase.app",
    "storageBucket": "alice-consultation-skill.appspot.com"
}

firebase = pyrebase.initialize_app(firebase_config)

logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO)

dp = Dispatcher(storage=MemoryStorage())

CANCEL_TEXTS = ['отмени', "отмена", 'прекрати', 'выйти', 'выход', 'назад']
PARAMS_WORDS = ['цена', 'стоимость', 'денег', 'деньги', 'мест', 'места', '']


# ACTIVITIES_LIST = ['Профиль', 'Консультация']
# ACTIVITIES_LIST = ['Консультация']


class States(Helper):
    mode = HelperMode.snake_case

    INTRO = Item()
    CONSULTATION = Item()
    PROFILE = Item()


class IntroStates(Helper):
    mode = HelperMode.snake_case
    EXAM_SUBJECTS = Item()
    LAST_EXAM = Item()
    TOTAL_SCORE = Item()


class Subjects(Helper):
    mode = HelperMode.snake_case
    PHYSICS = Item()
    INFORMATICS = Item()


async def db_push_data(path, data):
    db = firebase.database()
    db.child(path).push(data)


async def db_push_user_request(user, command):
    await db_push_data(f'requests/users/{user}', command)


def fetch_courses():
    db = firebase.database()
    courses = [item.val() for item in db.child("dialogs").child("courses").get()]
    return courses


def fetch_one_course(title):
    db = firebase.database()
    course_ref = db.child("refs").child(title).get().val()
    course = db.child("dialogs").child("courses").child(course_ref).get().val()
    return course


def get_custom_dialog(command):
    custom_dialogs = get_made_dialogs_requests("custom_dialogs")
    for item in custom_dialogs:
        keywords = item["request"].split()
        is_good = True
        for keyword in keywords:
            if keyword not in command:
                is_good = False
                break
        if not is_good:
            continue
        return item["response"]
    return None


def get_titles():
    db = firebase.database()
    refs = db.child("refs").get()

    return [item.key() for item in refs]


def get_suitable_courses(score):
    db = firebase.database()
    courses_refs = db.child("dialogs").child("courses").get()
    courses = [item.val() for item in courses_refs]
    suitable = list(filter(lambda item: int(item['params']['pass_score']) <= score, courses))
    return suitable


def get_suitable_titles(score):
    courses = get_suitable_courses(score)
    titles = [item['title'] for item in courses]
    return ';\n'.join(titles)

def get_made_dialogs_requests(dialog_type):
    db = firebase.database()
    dialogs = db.child("dialogs").child("general").child(dialog_type).get()

    return [{"request": dialog.val()['request'], "response": dialog.val()['response']} for dialog in dialogs]


def get_courses_names(score):
    return f'Курсы института ИРиТ-РТФ:\n \n {get_suitable_titles(score)}'


def get_one_course(command):
    parsed_courses_names = list(map(lambda title: title.lower().split(' '), get_titles()))
    res = get_keywords_answer(command, parsed_courses_names, 0.75)
    if res is None:
        return None
    db = firebase.database()
    course_id = db.child("refs").child(res.capitalize()).get().val()
    return db.child("dialogs").child("courses").child(course_id).get().val()


def get_keywords_answer(command, parsed_names, match_coeff):
    for course in parsed_names:
        isContains = True
        for word in course:
            length = len(word)
            substring = word[: int(math.ceil(length * match_coeff))]
            if length < 3:
                continue
            if substring not in command:
                isContains = False
                break
        if not isContains:
            continue
        return ' '.join(course)
    return None


def get_one_custom_dialog(command):
    made_dialogs = get_made_dialogs_requests("custom_dialogs")
    for dialog in made_dialogs:
        isContains = True
        for word in dialog["request"]:
            length = len(word)
            substring = str.lower(word[: int(math.ceil(length * 0.75))])
            if length < 3:
                continue
            if substring not in command:
                isContains = False
                break
        if isContains:
            return dialog
    return None


def get_one_service_dialog(command):
    made_dialogs = get_made_dialogs_requests("service_dialogs")
    command_words = command.split()
    for dialog in made_dialogs:
        dialog_words = dialog['request'].lower().split()
        if len(command_words) != len(dialog_words):
            continue
        isContains = True
        for idx in range(len(command_words)):
            word = dialog_words[idx]
            length = len(word)
            if length < 3:
                continue
            substring = word[: int(math.ceil(length * 0.75))]
            if substring not in command_words[idx]:
                isContains = False
                break
        if not isContains:
            continue
        return dialog
    return None


def isRussian(command):
    language = detect(command)
    return language == 'ru' or language == 'uk' or language == 'mk' or language == 'bg'


def get_upper_titles():
    courses = map(lambda x: x.capitalize(), get_titles())
    return courses


def get_courses():
    courses = get_upper_titles()
    return '\n'.join(courses)


@dp.request_handler(state=States.CONSULTATION)
async def selecting_course(alice_request):
    command = alice_request.request.command.lower()
    user_id = alice_request.session.user_id

    if len(command) < 1:
        dp.storage.set_state(user_id, States.INTRO)
        return alice_request.response('Привет! Я твой личный консультант по учебным дисциплинам твоего института. '
                                      'Спрашивай всё, что интересно, не стесняйся!',
                                      buttons=['Все дисциплины', 'Команды', 'Параметры'])


    text = 'Извините, я вас немного не поняла, попробуйте еще раз, либо воспользуйтесь списком команд.'
    temp_text = None
    data = await dp.storage.get_data(user_id)
    course = get_one_course(command)
    service_dialog = get_one_service_dialog(command)
    custom_dialog = get_custom_dialog(command)
    if service_dialog is not None:
        text = service_dialog["response"]

    elif str.isalpha(command) and not isRussian(command):
        res_text = 'Извините, я пока понимаю только русский язык, но возможно рано или поздно научусь и ' \
                   'вашему!\n-\nSorry, I only understand Russian so far, but maybe sooner or later I will learn your ' \
                   'language too! '
        await db_push_user_request(alice_request.session.user_id, {"request": command, "response": res_text,
                                                                   "date": datetime.datetime.now().strftime(
                                                                       "%d/%m/%Y %H:%M:%S")})
        return alice_request.response(res_text, buttons=['Все дисциплины', 'Команды', 'Параметры'])

    elif course is not None:
        text = get_brief_info(course)
        temp_text = get_param_info(course, command)

    elif re.search(r'команд\w*', command):
        text = '"Дисциплины/Направления" - для получения списка доступных образовательных дисциплин\n \n' \
               '"Параметры" - для получения списка доступных параметров образовательной дисциплины\n \n' \
               '"Команды" - для получения списка команд'

    elif re.search(r'парамет\w*', command):
        text = 'Описание всех параметров, где (*) - это название дисциплины\n \n' \
               '"Подробнее о */подробное описание *" - для получения подробного описания образовательной дисциплины;\n \n' \
               '"Стоимость */цена *" - для получения информации о стоимости образовательной дисциплины;\n \n' \
               '"Номер *" - для получения информации о номере направления образовательной дисциплины;\n \n' \
               '"Бюджетные места *" - для получения информации о количестве бюджетных мест образовательной дисциплины;\n \n' \
               '"Балл */проходной балл *" - для получения информации о проходном балле образовательной дисциплины;\n \n' \
               '"Форма обучения *" - для получения информации о форме обучения образовательной дисциплины;\n \n' \
               '"Руководитель */заведующий *" - для получения информации о руководителе образовательной дисциплины.'

    elif re.search(r'направл\w*|дисципл\w*|курс\w*', command):
        text = get_courses_names(data['total_score'])

    elif custom_dialog is not None:
        text = custom_dialog

    res_text = f'{temp_text}\n \nМожет быть вам что-то еще интересно?' \
        if temp_text else text
    await db_push_user_request(alice_request.session.user_id, {"request": command, "response": res_text,
                                                               "date": datetime.datetime.now().strftime(
                                                                   "%d/%m/%Y %H:%M:%S")})
    return alice_request.response(res_text, buttons=['Все дисциплины', 'Команды', 'Параметры'])


@dp.request_handler(state=IntroStates.TOTAL_SCORE)
async def ask_exam_subjects(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command.lower()
    new_state = States.CONSULTATION
    buttons = []
    text = 'Я тебя немножко не поняла, попробуй сказать еще раз'
    try:
        current_score = int(command)
    except ValueError:
        current_score = 0
    data = await dp.storage.get_data(user_id)
    try:
        temp_text = get_one_service_dialog(command)['response']
    except TypeError:
        temp_text = None
    if len(command) == 0:
        text = 'И чего молчим, ничего не говорим?'
    elif temp_text is None:
        temp_text = get_custom_dialog(command)
    if temp_text is not None:
        buttons = []
        new_state = IntroStates.TOTAL_SCORE
    elif current_score is None or current_score > 400 or current_score <= 0:
        if current_score is not None:
            text = 'А ты забавный, но если серьезно, то сколько баллов заработал?'
        new_state = IntroStates.TOTAL_SCORE
    elif current_score is not None:
        text = f'Ты молодец! Тогда познакомлю тебя со списком подходящих дисциплин:\n \n{get_suitable_titles(current_score)} ' \
            if current_score >= 175 \
            else 'Извини, друг, но по твоим результатам нам нечего тебе предложить, но ты можешь ознакомиться со ' \
                 'всеми имеющимися дисциплинами или же указать свои данные снова. '
        buttons = ['Все дисциплины', 'Команды', 'Параметры'] if current_score >= 175 else ['Подобрать снова', 'Хочу просто ознакомиться']
        if current_score < 175:
            new_state = States.INTRO
        data['total_score'] = current_score
        await dp.storage.update_data(user_id, data)

    await dp.storage.set_state(user_id, new_state)
    return alice_request.response(temp_text if temp_text else text, buttons=buttons)


@dp.request_handler(state=IntroStates.LAST_EXAM)
async def ask_exam_subjects(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command.lower()
    user_data = await dp.storage.get_data(user_id)
    new_state = IntroStates.EXAM_SUBJECTS
    text = 'Я тебя немножко не поняла, попробуй сказать еще раз'
    buttons = ['Да', 'Нет']
    try:
        temp_text = get_one_service_dialog(command)['response']
    except TypeError:
        temp_text = None
    if len(command) == 0:
        text = 'И чего молчим, ничего не говорим?'
    elif temp_text is None:
        temp_text = get_custom_dialog(command)
    if temp_text is not None:
        buttons = ['Да', 'Нет']
        new_state = IntroStates.LAST_EXAM
    elif re.search(r'да', command):
        new_state = Subjects.PHYSICS if user_data['exams']['physics'] is None else Subjects.INFORMATICS
        buttons = []
        text = 'И сколько баллов получилось заработать?'
    elif re.search(r'не\w+', command):
        new_state = IntroStates.TOTAL_SCORE
        buttons = []
        text = 'Тогда скажи, пожалуйста, сколько баллов набрал в сумме по всем экзаменам ЕГЭ?'

    await dp.storage.set_state(user_id, new_state)
    return alice_request.response(temp_text if temp_text else text, buttons=buttons)


@dp.request_handler(state=Subjects.PHYSICS)
async def physics_results(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command.lower()
    text = 'Немножко не поняла, попробуй еще раз'
    new_state = Subjects.PHYSICS
    try:
        current_score = int(command)
    except ValueError:
        current_score = 0
    data = await dp.storage.get_data(user_id)
    try:
        temp_text = get_one_service_dialog(command)['response']
    except TypeError:
        temp_text = None
    buttons = []
    if len(command) == 0:
        text = 'И чего молчим, ничего не говорим?'
    elif temp_text is None or current_score is None:
        temp_text = get_custom_dialog(command)
    if current_score is None or current_score > 100 or current_score <= 0:
        if current_score is not None:
            text = 'А ты забавный, но если серьезно, то сколько баллов заработал?'
        new_state = Subjects.PHYSICS
    elif data['exams']['physics'] is None:
        text = 'Нехило ты набрал, молодчинка, а информатику тебе приходилось сдавать?' if data['exams']['informatics'] is None else 'Тогда скажи, пожалуйста, сколько баллов набрал в сумме по всем экзаменам ЕГЭ?'
        data['exams']['physics'] = current_score
        buttons = ['Да', 'Нет'] if data['exams']['informatics'] is None else []
        new_state = IntroStates.LAST_EXAM
        await dp.storage.update_data(user_id, data)
    if data['exams']['physics'] is not None and data['exams']['informatics'] is not None:
        text = 'Тогда скажи, пожалуйста, сколько баллов набрал в сумме по всем экзаменам ЕГЭ?'
        new_state = IntroStates.TOTAL_SCORE
    if temp_text is not None:
        buttons = []
        new_state = Subjects.PHYSICS

    await dp.storage.set_state(user_id, new_state)
    return alice_request.response(temp_text if temp_text else text, buttons=buttons)


@dp.request_handler(state=Subjects.INFORMATICS)
async def informatics_results(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command.lower()
    text = 'Немножко не поняла, попробуй еще раз'
    new_state = Subjects.INFORMATICS
    try:
        current_score = int(command)
    except ValueError:
        current_score = 0
    data = await dp.storage.get_data(user_id)
    try:
        temp_text = get_one_service_dialog(command)['response']
    except TypeError:
        temp_text = None
    print(temp_text)
    buttons = []
    if len(command) == 0:
        text = 'И чего молчим, ничего не говорим?'
    elif temp_text is None:
        temp_text = get_custom_dialog(command)

    if current_score is None or current_score > 100 or current_score <= 0:
        if current_score is not None:
            text = 'А ты забавный, но если серьезно, то сколько баллов заработал?'
        new_state = Subjects.INFORMATICS
    elif data['exams']['informatics'] is None:
        text = 'Это очень хороший результат, ты супер! А физику приходилось сдавать?' if data['exams']['physics'] is None else 'Тогда скажи, пожалуйста, сколько баллов набрал в сумме по всем экзаменам ЕГЭ?'
        data['exams']['informatics'] = current_score
        buttons = ['Да', 'Нет'] if data['exams']['physics'] is None else []
        new_state = IntroStates.LAST_EXAM
        await dp.storage.update_data(user_id, data)
    if data['exams']['physics'] is not None and data['exams']['informatics'] is not None:
        text = 'Тогда скажи, пожалуйста, сколько баллов набрал в сумме по всем экзаменам ЕГЭ?'
        new_state = IntroStates.TOTAL_SCORE
    if temp_text is not None:
        buttons = []
        new_state = Subjects.INFORMATICS

    await dp.storage.set_state(user_id, new_state)
    return alice_request.response(temp_text if temp_text else text, buttons=buttons)


@dp.request_handler(state=IntroStates.EXAM_SUBJECTS)
async def ask_exam_subjects(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command.lower()
    new_state = IntroStates.EXAM_SUBJECTS
    buttons = []
    text = 'Я тебя немножко не поняла, попробуй сказать еще раз'
    try:
        temp_text = get_one_service_dialog(command)['response']
    except TypeError:
        temp_text = None
    if len(command) == 0:
        text = 'И чего молчим, ничего не говорим?'
    elif temp_text is None:
        temp_text = get_custom_dialog(command)
    if temp_text is not None:
        buttons = ['Физика', 'Информатика']
        new_state = IntroStates.EXAM_SUBJECTS
    elif re.search(r'физи\w+', command):
        new_state = Subjects.PHYSICS
        text = 'О, да ты прям как Эйнштейн, а сколько баллов набрал?'
    elif re.search(r'информ\w+', command):
        new_state = Subjects.INFORMATICS
        text = 'Будешь прям как Билл Гейтс. И сколько же баллов получил?'
    else:
        buttons = ['Физика', 'Информатика']
        await dp.storage.set_data(user_id, {'exams': {'physics': None, 'informatics': None}, 'total_score': None})

    await dp.storage.set_state(user_id, new_state)
    return alice_request.response(temp_text if temp_text else text, buttons=buttons)


@dp.request_handler(state=States.INTRO)
async def select_activity(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command.lower()
    new_state = States.INTRO
    buttons = []
    text = 'Я тебя немножко не поняла, попробуй сказать еще раз'
    try:
        temp_text = get_one_service_dialog(command)['response']
    except TypeError:
        temp_text = None
    if len(command) == 0:
        text = 'И чего молчим, ничего не говорим?'
    elif temp_text is None:
        temp_text = get_custom_dialog(command)
    if temp_text is not None:
        buttons = ['Давай подберём', 'Хочу просто ознакомиться']
        new_state = States.INTRO
    elif re.search(r'подбер\w+|подобр\w*', command) \
            or command == 'давай' or command == 'давай подберем' or command == 'да':
        text = 'Отлично, тогда мне очень интересно, какие ты профильные экзамены сдавал, может физику или информатику?'
        buttons = ['Физика', 'Информатика']
        new_state = IntroStates.EXAM_SUBJECTS
        await dp.storage.set_data(user_id, {'exams': {'physics': None, 'informatics': None}, 'total_score': None})
    elif re.search(r'ознаком\w+|посмотр\w*',
                   command) or command == 'хочу просто ознакомиться' or command == 'не надо' or command == 'нет':
        new_state = States.CONSULTATION
        text = 'Хорошо, тогда спрашивай меня всё, что тебе интересно о дисциплинах, я тебя слушаю!'
        buttons = ['Все дисциплины', 'Команды', 'Параметры']
        await dp.storage.set_data(user_id, {'exams': {'physics': 100, 'informatics': 100}, 'total_score': 300})

    await dp.storage.set_state(user_id, new_state)
    return alice_request.response(temp_text if temp_text else text, buttons=buttons)


@dp.request_handler()
async def handle_all_requests(alice_request):
    user_id = alice_request.session.user_id
    # text = 'Привет! Чтобы приступить к консультации, достаточно сказать, написать или нажать на кнопку ' \
    #        '"Консультация". Чтоб перейти в свой профиль, нужно попросить ассистента перейти туда. '
    # text = 'Привет! Чтобы приступить к консультации, достаточно сказать, написать или нажать на кнопку ' \
    #        '"Консультация".'
    text = 'Привет! Я твой личный консультант по учебным дисциплинам твоего института, можешь задавать мне все ' \
           'интересующие тебя вопросы!\n \nХочешь подобрать подходящие для тебя дисциплины или же желаешь просто ' \
           'ознакомиться со всеми?'
    await dp.storage.set_state(user_id, States.INTRO)
    await dp.storage.set_data(user_id, {'exams': {'physics': None, 'informatics': None}, 'total_score': None})
    return alice_request.response(text, buttons=['Давай подберём', 'Хочу просто ознакомиться'])


if __name__ == '__main__':
    app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_URL_PATH)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
