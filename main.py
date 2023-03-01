import logging
from pydnevnikruapi import dnevnik
from datetime import date, datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
import asyncio
from aiogram.dispatcher.filters import CommandHelp
from aiogram.dispatcher.filters import Text
import aioschedule
import sqlite3


class HomeWork:
    Subject: str
    Work: str
    TargetDate: datetime
    SentDate: datetime

    def __str__(self):
        return str(f"{self.Subject} {self.Work} {self.TargetDate} {self.SentDate}")
class Mark:
    Mark: str
    Lesson: str

class User:
    id: int
    telegram_id: str
    dnevnik_id: str
    person_id: str
    login: str
    password: str
    join_date: str
    school_id: str

class MarkSubject:
    Mark: str
    Subject: str



API_TOKEN = "5892918359:AAHht8Iw9qx4GpzrlnH4oHk9DdtfwCc8XLI"


logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
sqlConnect = sqlite3.Connection
sqlCursor = sqlite3.Cursor



def get_dnevnik(login: str, password: str):
    return dnevnik.DiaryAPI(login, password)


def parse_user(user: tuple):
    if len(user) == 0: return
    retUser = User()
    retUser.id = user[0]
    retUser.telegram_id = user[1]
    retUser.dnevnik_id = user[2]
    retUser.person_id = user[3]
    retUser.login = user[4]
    retUser.password = user[5]
    retUser.join_date = user[6]
    retUser.school_id = user[7]
    return retUser




def parse_homework(fromDate: datetime, forDate: datetime, dn: dnevnik.DiaryAPI):
    homeworks = dn.get_school_homework(1000019007939, fromDate, forDate)
    homeworks_list = list()
    subjects = dict()
    for i in homeworks["subjects"]:
        subjects[i["id"]] = i["name"]
    for i in homeworks["works"]:
        homework = HomeWork()
        homework.Work = i["text"]
        homework.Subject = subjects[i["subjectId"]]
        homeworks_list.append(homework)
        homework.TargetDate = i["targetDate"]
    return homeworks_list



@dp.message_handler(content_types=[types.ContentType.NEW_CHAT_MEMBERS])
async def cmd_new_member(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    start_button = types.KeyboardButton("/start")
    keyboard.add(start_button)

    await bot.send_message(message.chat["id"], "Добро пожаловать!", reply_markup=keyboard)

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message, command: CommandHelp.CommandObj):
    ChatID = message.chat["id"]

    user = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()

    if len(user) == 0:
        await message.answer("Введите /login логин пароль")
        return


    login = types.KeyboardButton("Скинь дз")
    marks = types.KeyboardButton("Оценки за сегодня")
    school_scheduler = types.KeyboardButton("Скинь расписание")
    marks_week = types.KeyboardButton("Оценки за неделю")
    marks_month = types.KeyboardButton("Оценки за месяц")
    marks_semester = types.KeyboardButton("Оценки за полугодие")
    help_button = types.KeyboardButton("Помощь")

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(help_button)
    keyboard.add(login)
    keyboard.add(marks)
    keyboard.add(school_scheduler)
    keyboard.add(marks_week)
    keyboard.add(marks_month)
    keyboard.add(marks_semester)


    await message.answer("Что вы хотите сделать?", reply_markup=keyboard)





@dp.message_handler(commands="login")
async def cmd_login(message: types.Message, command: CommandHelp.CommandObj):
    ChatID = message.chat["id"]
    if len(sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()) != 0:
        await message.answer("Вы уже вошли")
        return

    if command.args is None:
        await message.answer("Введите логин и пароль")
        return
    args = command.args.split(" ")
    if len(args) != 2:
        await message.answer("Введите логин и пароль")
        return
    login = args[0]
    password = args[1]
    try:
        dn = get_dnevnik(login, password)
    except:
        await message.answer("Логин или пароль неверны")
    user = dn.get(f"users/me")
    PersonId = user["personId_str"]
    UserId = user["id_str"]
    ChatId = message.chat["id"]
    SchoolId = dn.get_school()[0]["id_str"]
    sqlCursor.execute("INSERT OR IGNORE INTO `users` (`telegram_id`, `dnevnik_id`,`person_id`, `login`, `password`, `school_id`) VALUES( ?, ?, ?, ?, ?, ?)", (ChatId, UserId, PersonId, login, password, SchoolId,))
    sqlConnect.commit()
    await message.answer(f"ID пользователя - {PersonId}")
    await message.answer("Вход успешен")
    await message.answer(ChatId)
    await cmd_start(message, command)



@dp.message_handler(Text("Помощь"))
async def help(message: types.Message):
    await message.answer("Если у вас возникли какие-то вопросы, пожалуйста, напишите на почту \nnahmurin.dima65@gmail.com")


@dp.message_handler(commands="help")
async def cmd_help(message: types.Message):
    await help(message)

@dp.message_handler(commands="mark_today")
async def cmd_mark_today(message: types.Message):
    await mark_today(message)

@dp.message_handler(commands="homework")
async def cmd_homework(message: types.Message):
    await homework(message)

@dp.message_handler(commands="mark_toweek")
async def cmd_mark_toweek(message: types.Message):
    await mark_toweek(message)

@dp.message_handler(commands="mark_tosemester")
async def cmd_mark_toweek(message: types.Message):
    await marks_for_semester(message)

@dp.message_handler(commands="mark_tomonth")
async def cmd_mark_toweek(message: types.Message):
    await mark_tomonth(message)

@dp.message_handler(commands="scheduler")
async def cmd_scheduler(message: types.Message):
    await get_scheduler(message)


@dp.message_handler(Text("Оценки за сегодня"))
async def mark_today(message: types.Message):
    ChatID = message.chat["id"]
    users = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()
    if len(users) == 0:
        await message.answer("Вы не вошли в аккаунт пожалуйста введите: /login")
        return
    user = parse_user(users[0])

    dn = get_dnevnik(user.login, user.password)
    lessons = dict()
    marks_list = dn.get_marks_by_date(int(user.person_id), datetime.today())
    if len(marks_list) == 0:
        await message.answer("Оценок сегодня нету")
        return
    marks = list()
    for i in marks_list:
        mark = Mark()
        lesson = dn.get_lesson_info(i["lesson"])
        mark.Lesson = lesson["subject"]["name"]
        mark.Mark = i["textValue"]
        marks.append(mark)

    await message.answer("Оценки за сегодня:")

    for i in marks:
        await message.answer(f"{i.Lesson} - {i.Mark}")

    #print(dn.get_marks_by_date(int(PersonId), datetime(2023, 2, 9)))



# noinspection PyUnresolvedReferences
@dp.message_handler(Text("Скинь дз"))
async def homework(message: types.Message):
    ChatID = message.chat["id"]
    users = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()
    if len(users) == 0:
        await message.answer("Вы не вошли в аккаунт пожалуйста введите: /login")
        return
    user = parse_user(users[0])

    dn = get_dnevnik(user.login, user.password)
    today = datetime.today()
    if today.weekday() == 4 or today.weekday() == 5:
        today = today + timedelta(days=(6 - today.weekday()))
    tommorow = today + timedelta(days=1)
    homeworks = parse_homework(today, tommorow, dn)
    if len(homeworks) == 0:
        await message.answer("дз не задали")
        return
    for i in homeworks:
        await message.answer(str(i.Subject + " - " + i.Work))
    feed = dn.get_feed()



@dp.message_handler(Text("Оценки за неделю"))
async def mark_toweek(message: types.Message):
    ChatID = message.chat["id"]
    users = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()
    if len(users) == 0:
        await message.answer("Вы не вошли в аккаунт пожалуйста введите: /login")
        return
    user = parse_user(users[0])
    dn = get_dnevnik(user.login, user.password)
    marks = dn.get_person_marks(user.person_id, user.school_id, datetime.now()- timedelta(days=7), datetime.now())

    for i in marks:
        subject = dn.get_lesson_info(i["lesson"])["subject"]["name"]
        date = datetime.strptime(i['date'], '%Y-%m-%dT%X.%f')

        await message.answer(f"{subject} - {i['textValue']} - {date.date()}")


@dp.message_handler(Text("Оценки за месяц"))
async def mark_tomonth(message: types.Message):
    ChatID = message.chat["id"]
    users = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()
    if len(users) == 0:
        await message.answer("Вы не вошли в аккаунт пожалуйста введите: /login")
        return
    user = parse_user(users[0])
    dn = get_dnevnik(user.login, user.password)
    marks = dn.get_person_marks(user.person_id, user.school_id, datetime.now()- timedelta(days=30), datetime.now())

    for i in marks:
        subject = dn.get_lesson_info(i["lesson"])["subject"]["name"]
        date = datetime.strptime(i['date'], '%Y-%m-%dT%X.%f')

        await message.answer(f"{subject} - {i['textValue']} - {date.date()}")


@dp.message_handler(Text("Оценки за полугодие"))
async def marks_for_semester(message: types.Message):
    ChatID = message.chat["id"]
    users = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()
    if len(users) == 0:
        await message.answer("Вы не вошли в аккаунт пожалуйста введите: /login")
        return
    user = parse_user(users[0])
    dn = get_dnevnik(user.login, user.password)

    dateNow = datetime.now()
    dateFrom = datetime.now()
    if dateNow.month < 6:
        dateFrom = datetime(dateNow.year, 1, 1)
    else:
        dateFrom = datetime(dateNow.year, 9, 1)

    marks = dn.get_person_marks(user.person_id, user.school_id, dateFrom, dateNow)

    for i in marks:
        subject = dn.get_lesson_info(i["lesson"])["subject"]["name"]
        date = datetime.strptime(i['date'], '%Y-%m-%dT%X.%f')

        await message.answer(f"{subject} - {i['textValue']} - {date.date()}")




@dp.message_handler(Text("Итоги"))
async def cmd_marks_for_semester(message: types.Message):
    if message.chat.id == 1000010969040:
        await homeworkOnTime()

async def homeworkOnTime():
    users = sqlCursor.execute("SELECT * FROM `users`").fetchall()

    for i in users:
        user = parse_user(i)
        await bot.send_message(chat_id=user.telegram_id, text="Итоги за сегодня:")


        dn = get_dnevnik(user.login, user.password)
        lessons = dict()
        marks_list = dn.get_marks_by_date(int(user.person_id), datetime.today())
        if len(marks_list) == 0:
            await bot.send_message(chat_id=user.telegram_id, text="Оценок сегодня нет")
        else:
            marks = list()
            for i in marks_list:
                mark = Mark()
                lesson = dn.get_lesson_info(i["lesson"])
                mark.Lesson = lesson["subject"]["name"]
                mark.Mark = i["textValue"]
                marks.append(mark)

            await bot.send_message(chat_id=user.telegram_id, text="Оценки:")

            for i in marks:
                await bot.send_message(chat_id=user.telegram_id, text=f"{i.Lesson} - {i.Mark}")

        feed = dn.get_feed()


        nextDay = feed['days'][0]['nextWorkingDayDate']

        nextDateTime = datetime.strptime(nextDay, "%Y-%m-%dT%H:%M:%S")


        nextDay = f"{nextDateTime.day}/{nextDateTime.month}/{nextDateTime.year}"
        await bot.send_message(chat_id=user.telegram_id, text=f"ДЗ на {nextDay}:")

        today = datetime.today()
        if today.weekday() == 4 or today.weekday() == 5:
            today = today + timedelta(days=(6 - today.weekday()))
        tommorow = today + timedelta(days=1)
        homeworks = parse_homework(today, tommorow, dn)
        if len(homeworks) == 0:
            await bot.send_message(chat_id=user.telegram_id, text="ДЗ не задали")
        else:
            for i in homeworks:
                await bot.send_message(chat_id=user.telegram_id, text=str(i.Subject + " - " + i.Work))


        await bot.send_message(chat_id=user.telegram_id, text = f"Расписание на {nextDay}:")


        for i in feed["days"][0]["nextDaySchedule"]:
            subjectName = i["subjectName"]
            await bot.send_message(chat_id=user.telegram_id, text=f"{i['number']}.{subjectName}")


@dp.message_handler(Text("Скинь расписание"))
async def get_scheduler(message: types.Message):
    ChatID = message.chat["id"]
    users = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()
    if len(users) == 0:
        await message.answer("Вы не вошли в аккаунт пожалуйста введите: /login")
        return
    user = parse_user(users[0])
    dn = get_dnevnik(user.login, user.password)
    feed = dn.get_feed()




    timenow = datetime.today().time()
    if timenow.hour > 15:
        nextDay = feed['days'][0]['nextWorkingDayDate']
        nextDateTime = datetime.strptime(nextDay, "%Y-%m-%dT%H:%M:%S")
        nextDay = f"{nextDateTime.day}/{nextDateTime.month}/{nextDateTime.year}"
        await message.answer(f"Расписание на {nextDay}")
        for i in feed["days"][0]["nextDaySchedule"]:
            await message.answer(f"{i['number']}.{i['subjectName']}")
    else:
        toDay = feed['days'][0]['date']
        toDayTime = datetime.strptime(toDay, "%Y-%m-%dT%H:%M:%S")
        toDay = f"{toDayTime.day}/{toDayTime.month}/{toDayTime.year}"
        await message.answer(f"Расписание на {toDay}")
        for i in feed["days"][0]["todaySchedule"]:
            await message.answer(f"{i['number']}.{i['subjectName']}")


@dp.message_handler(Text("Feed"))
async def cmd_feed(message: types.Message):
    ChatID = message.chat["id"]
    user = parse_user(sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()[0])
    dn = get_dnevnik(user.login, user.password)
    feed = dn.get_feed()

    for i in feed["days"]:
        await message.answer(i)


@dp.message_handler(Text("Test"))
async def test(message: types.Message):
    ChatID = message.chat["id"]
    users = sqlCursor.execute("SELECT * FROM `users` WHERE (`telegram_id` = ?)", (ChatID,)).fetchall()
    if len(users) == 0:
        await message.answer("Вы не вошли в аккаунт пожалуйста введите: /login")
        return
    user = parse_user(users[0])
    dn = get_dnevnik(user.login, user.password)
    # groups = dn.get_person_average_marks(user.person_id, d)
    # print(groups)



async def scheduler():
    aioschedule.every().day.at("18:00").do(homeworkOnTime)
    #aioschedule.every(1).second.do(homeworkOnTime)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


def shutdown(loop):
    sqlConnect.commit()
    sqlConnect.close()
    loop.stop()

async def main():
    asyncio.create_task(scheduler())

    loop = asyncio.get_event_loop()
   # loop.add_signal_handler(signal.SIGTERM, functools.partial(shutdown, loop))
    await dp.start_polling(bot)

def start():
    global sqlConnect
    global sqlCursor
    sqlConnect= sqlite3.connect('datebases/acounts.db');
    sqlCursor = sqlConnect.cursor()


if __name__ == "__main__":
    start()
    asyncio.run(main())
