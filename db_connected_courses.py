import pyrebase
from main import firebase


# def fetch_courses():
#     db = firebase.database()
#     courses = [item.val() for item in db.child("dialogs").get()]
#     return courses
#
#
# def get_titles():
#     courses = fetch_courses()
#     return [item["title"] for item in courses]
#
#
# def get_courses_names():
#     res = f'Курсы института ИРиТ-РТФ:\n\n'
#     for item in get_titles():
#         res += str(item) + ';\n'
#     return res
