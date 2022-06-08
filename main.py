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


class ConsultationStates(Helper):
    mode = HelperMode.snake_case

    SELECT_ACTIVITY = Item()
    CONSULTATION = Item()
    PROFILE = Item()


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


def get_made_dialogs_requests(dialog_type):
    db = firebase.database()
    dialogs = db.child("dialogs").child("general").child(dialog_type).get()

    return [{"request": dialog.val()['request'], "response": dialog.val()['response']} for dialog in dialogs]


def get_courses_names():
    res = f'Курсы института ИРиТ-РТФ:\n \n'
    for item in sorted(get_upper_titles()):
        res += str(item) + ';\n'
    return res


def get_one_course(command):
    parsed_courses_names = list(map(lambda title: title.split(' '), get_titles()))
    res = get_keywords_answer(command, parsed_courses_names, 0.75)
    if res is None:
        return None
    db = firebase.database()
    course_id = db.child("refs").child(res).get().val()
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
    print(courses)
    return courses


def get_courses():
    courses = get_upper_titles()
    return '\n'.join(courses)


@dp.request_handler(state=ConsultationStates.CONSULTATION)
async def selecting_course(alice_request):
    command = alice_request.request.command.lower()

    if len(command) < 1:
        return alice_request.response('Ну привет, чего ты такой неразговорчивый?',
                                      buttons=['Все дисциплины', 'Команды'])

    # text = 'Извините, данная образовательная дисциплина в данный момент отсутствует, либо же была названна ' \
    #        'некорректно. Если вам необходим список команд, то можете сказать "Команды"'
    text = 'Извините, я вас немного не поняла, попробуйте еще раз, либо воспользуйтесь списком команд.'
    temp_text = None
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
        return alice_request.response(res_text, buttons=['Все дисциплины', 'Команды'])

    elif course is not None:
        text = get_brief_info(course)
        temp_text = get_param_info(course, command)

    elif re.search(r'команд\w*', command):
        text = '"Институты" - для доступа к списку имеющихся институтов УрФУ\n \n' \
               '"Дисциплины/Направления" - для получения списка доступных образовательных дисциплин\n \n' \
               '"Команды" - для получения списка команд'

    elif re.search(r'направл\w*|дисципл\w*|курс\w*', command):
        text = get_courses_names()

    elif custom_dialog is not None:
        text = custom_dialog

    res_text = f'{temp_text}\n \nМожет быть вам что-то еще интересно?' \
        if temp_text else text
    await db_push_user_request(alice_request.session.user_id, {"request": command, "response": res_text,
                                                               "date": datetime.datetime.now().strftime(
                                                                   "%d/%m/%Y %H:%M:%S")})
    return alice_request.response(res_text, buttons=['Все дисциплины', 'Команды'])


@dp.request_handler(state=ConsultationStates.SELECT_ACTIVITY)
async def select_activity(alice_request):
    user_id = alice_request.session.user_id
    new_state = ConsultationStates.SELECT_ACTIVITY
    command = alice_request.request.command
    text = 'Такая функция пока мне неизвестна, попробуй одну из уже имеющихся!' \
        if len(command) > 0 \
        else 'Привет! Я твой личный консультант по учебным дисциплинам твоего института. Спрашивай всё, что интересно, не стесняйся!".'
    # buttons = ACTIVITIES_LIST
    if re.search(r'консультац\w+', alice_request.request.command.lower()):
        new_state = ConsultationStates.CONSULTATION
        text = 'Для того, чтобы узнать подробнее о направлении обучения, спросите о нем, например, для информации о ' \
               'программной инженерии, вы можете сказать "Расскажи о программной инженерии". Для доступа к списку ' \
               'команд, скажите "Команды"'
        buttons = ['Все дисциплины', 'Команды']
    if re.search(r'профил\w+', alice_request.request.command.lower()):
        new_state = ConsultationStates.PROFILE
        text = 'Добро пожаловать в ваш профиль, тут отображается список интересующих вас направлений, ваши заметки ' \
               'и т.д.'
        buttons = ['Все дисциплины', 'Команды']
    await dp.storage.set_state(user_id, new_state)
    temp_text = get_custom_dialog(command)
    return alice_request.response(temp_text if temp_text else text, buttons=buttons)


@dp.request_handler(state=ConsultationStates.SELECT_ACTIVITY)
async def select_not_listed_activity(alice_request):
    return alice_request.response(

        # buttons=ACTIVITIES_LIST
        buttons=[]
    )


@dp.request_handler()
async def handle_all_requests(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.set_state(user_id, ConsultationStates.CONSULTATION)
    # text = 'Привет! Чтобы приступить к консультации, достаточно сказать, написать или нажать на кнопку ' \
    #        '"Консультация". Чтоб перейти в свой профиль, нужно попросить ассистента перейти туда. '
    # text = 'Привет! Чтобы приступить к консультации, достаточно сказать, написать или нажать на кнопку ' \
    #        '"Консультация".'
    text = 'Привет! Я твой личный консультант по учебным дисциплинам твоего института. Спрашивай всё, что интересно, ' \
           'не стесняйся!". '
    return alice_request.response(text, buttons=['Все дисциплины', 'Команды'])


if __name__ == '__main__':
    app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_URL_PATH)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
