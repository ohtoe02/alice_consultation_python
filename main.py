import logging
import re

from all_courses import Courses_RTF

from aiohttp import web
from aioalice import Dispatcher, get_new_configured_app, types
from aioalice.dispatcher import MemoryStorage, SkipHandler
from aioalice.utils.helper import Helper, HelperMode, Item

WEBHOOK_URL_PATH = '/consultation-service/'  # webhook endpoint

WEBAPP_HOST = 'localhost'
WEBAPP_PORT = 3001

logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO)

dp = Dispatcher(storage=MemoryStorage())

CANCEL_TEXTS = ['отмени', "отмена", 'прекрати', 'выйти', 'выход', 'назад']
PARAMS_WORDS = ['цена', 'стоимость', 'денег', 'деньги', 'мест', 'места', '']
ACTIVITIES_LIST = ['Профиль', 'Консультация']


class ConsultationStates(Helper):
    mode = HelperMode.snake_case

    SELECT_ACTIVITY = Item()
    CONSULTATION = Item()
    PROFILE = Item()


@dp.request_handler()
async def take_all_requests(alice_request):
    # Логгируем запрос. Можно записывать в БД и тд
    logging.debug('New request! %r', alice_request)
    # Поднимаем исключение, по которому обработка перейдёт
    # к следующему хэндлеру, у которого подойдут фильтры
    raise SkipHandler


def get_lower_courses():
    courses = map(lambda x: x.lower(), Courses_RTF().get_titles())
    return courses


def get_courses():
    courses = Courses_RTF().get_titles()
    return '\n'.join(courses)


@dp.request_handler(state=ConsultationStates.CONSULTATION)
async def selecting_course(alice_request):
    user_id = alice_request.session.user_id
    text = 'Извините, данная образовательная дисциплина в данный момент отсутствует, либо же была названна ' \
           'некорректно. Если вам необходим список команд, то можете сказать "Команды" '
    temp_text = None

    if re.search(r'программн\w* инженер\w*', alice_request.request.command.lower()):
        text = str(Courses_RTF().courses[0].get_brief_info())
        temp_text = Courses_RTF().courses[0].get_param_info(alice_request.request.command.lower())

    if re.search(r'информационн\w* безопасност\w*', alice_request.request.command.lower()):
        text = str(Courses_RTF().courses[1].get_brief_info())
        temp_text = Courses_RTF().courses[1].get_param_info(alice_request.request.command.lower())
        print(temp_text)

    if re.search(r'команд\w*', alice_request.request.command.lower()):
        text = '"Институты" - для доступа к списку имеющихся институтов УрФУ\n' \
               '"Дисциплины/Направления" - для получения списка доступных образовательных дисциплин\n' \
               '"Команды" - для получения списка команд\n'

    if re.search(r'направл\w* | дисципл\w*', alice_request.request.command.lower()):
        return alice_request.response(Courses_RTF().get_courses_names())

    if re.search(r'институт\w*', alice_request.request.command.lower()):
        return alice_request.response_items_list('Институты', 'Институты УрФУ', [
            {
                "image_id": '1521359/e03c6d224fa1dcdca183',
                "title": 'ИРИТ-РТФ',
                "description": "Специальности ИРИТ-РТФ",
                "button": {
                    "text": 'Образовательные программы',
                    "url": 'https://priem-rtf.urfu.ru/ru/baccalaureate/'
                }
            },
            {
                "image_id": '1521359/e03c6d224fa1dcdca183',
                "title": 'ИнФО',
                "description": "Специальности ИнФО",
                "button": {
                    "text": 'Образовательные программы',
                    "url": 'https://info.urfu.ru/ru/entrant-info/bakalavriatspecialitet/'
                }
            },
            {
                "image_id": '1521359/e03c6d224fa1dcdca183',
                "title": 'УГИ',
                "description": "Специальности УГИ",
                "button": {
                    "text": 'Образовательные программы',
                    "url": 'https://urgi.urfu.ru/ru/kak-postupit/napravlenija-podgotovki/'
                }
            },
            {
                "image_id": '1521359/e03c6d224fa1dcdca183',
                "title": 'ИнЭУ',
                "description": "Специальности ИнЭУ",
                "button": {
                    "text": 'Образовательные программы',
                    "url": 'https://gsem.urfu.ru/ru/applicants/bakalavriat-i-specialitet/obrazovatelnye-programmy-bakalavriata-i-specialiteta/'
                }
            },
            {
                "image_id": '1521359/e03c6d224fa1dcdca183',
                "title": 'ХТИ',
                "description": "Специальности ХТИ",
                "button": {
                    "text": 'Образовательные программы',
                    "url": 'https://hti.urfu.ru/ru/abiturientam/bakalavriat/'
                }
            }
        ], buttons=['Далее'])

    return alice_request.response(temp_text if temp_text else text, buttons=['Все дисциплины', 'Команды'])


@dp.request_handler(state=ConsultationStates.SELECT_ACTIVITY)
async def select_activity(alice_request):
    user_id = alice_request.session.user_id
    new_state = ConsultationStates.CONSULTATION
    text = 'Такая функция пока мне неизвестна, попробуй одну из уже имеющихся!'
    buttons = ACTIVITIES_LIST
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
    return alice_request.response(text, buttons=buttons)


@dp.request_handler(state=ConsultationStates.SELECT_ACTIVITY)
async def select_not_listed_activity(alice_request):
    return alice_request.response(

        buttons=ACTIVITIES_LIST
    )


@dp.request_handler()
async def handle_all_requests(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.set_state(user_id, ConsultationStates.SELECT_ACTIVITY)
    text = 'Привет! Чтобы приступить к консультации, достаточно сказать, написать или нажать на кнопку ' \
           '"Консультация". Чтоб перейти в свой профиль, нужно попросить ассистента перейти туда. '
    return alice_request.response(text, buttons=ACTIVITIES_LIST)


if __name__ == '__main__':
    app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_URL_PATH)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
