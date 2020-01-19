import telebot
from telebot import types
import pymysql
from pymysql.cursors import DictCursor
from contextlib import closing
import re
import time
from call import *

campaigns = [1]
#ID кампаний по обзвону

TOKEN = "YOUR_TOKEN"
#Токен бота в Telegram
bot = telebot.TeleBot(TOKEN)
#Авторизуемся по токену

hello_text = "Привет! 👋 \n\nСо мной ты можешь оригинально разыграть своих друзей и знакомых, и как следует посмеяться 😄 \n\nКак заказать звонок: \n\n1. Выбери понравившийся розыгрыш среди аудиозаписей 🎉 \n\n2. Введи номер телефона человека, которого хочешь разыграть 📞 \n\n3. Пополни баланс на 15 рублей при помощи удобной ссылки ⚡️ \n\n4. Ожидай в течение 2 минут голосовое сообщение с записью разговора  \n\nЕсли человек не берёт трубку, деньги не спишутся, и у вас будет возможность выбрать другой номер телефона"
#Приветственный текст

def getJokesKeyboard(chat_id):
    #Функция получения доступных розыгрышей
    with closing(pymysql.connect(host='localhost', user='root', password='', db='callprank', charset='utf8mb4', cursorclass=DictCursor)) as conn:
        with conn.cursor() as cur:
            sql = ("SELECT * FROM jokes ORDER BY id")
            cur.execute(sql)
            jokes = cur.fetchall()
            
    jokesKeyboard = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard = True)
    #Клавиатура выбора пранка

    for joke in jokes:
        choose_joke_button = types.KeyboardButton(text = str(jokes.index(joke)+1))
        jokesKeyboard.add(choose_joke_button)
        bot.send_audio(chat_id, open('jokes/' + joke["name"], 'rb'), performer = "CallPrankBot", title = joke["title"])
        #Отправляем аудио доступных розыгрышей

    jokesKeyboard.add(back_button)
    return jokesKeyboard

users = []
#Список пользователей

commandSet = ['start']
#Доступные команды

back_button = types.KeyboardButton(text = "Назад ↩️")
#Кнопка назад

mainKeyboard = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard = True)
available_jokes_button = types.KeyboardButton(text = 'Розыгрыши 🥳')
#Основная клавиатура
mainKeyboard.add(available_jokes_button)

backKeyboard = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard = True)
#Клавиатура с кнопкой назад
backKeyboard.add(back_button)

def identification(id):
    user = None
    for u in users:
        if u["id"] == id:
            user = u
    #Проверяем пользователя на нахождение в списке бота
    
    if user == None:
        #Новый пользователь
        newArray = {'id': id, "extensions": {"chosenButton": "", "prank_id": 0}}
        users.append(newArray)
        user = users[-1]
        
    return user

@bot.message_handler(commands=commandSet)
def send_welcome(message):
    user = identification(message.chat.id)
        
    if message.text in ("/start", "/help"):
        #Отправляем приветственное сообщение и клавиатуру
        bot.send_message(message.chat.id, hello_text, reply_markup = mainKeyboard)
        
@bot.message_handler(content_types=['text'])
def joking(message):
    user = identification(message.chat.id)
    
    if message.text == "Розыгрыши 🥳":
        user["extensions"]["chosenButton"] = "Все розыгрыши"
        jokesKeyboard = getJokesKeyboard(message.chat.id)
        bot.send_message(message.chat.id, "Выберите пранк для звонка", reply_markup = jokesKeyboard)
    
    elif user["extensions"]["chosenButton"] == "Все розыгрыши":
        if message.text == "Назад ↩️":
            user["extensions"]["chosenButton"] = ""
            bot.send_message(message.chat.id, "Возвращаю...", reply_markup = mainKeyboard)
        else:
            try:
                prank_id = int(message.text)
                user["extensions"]["prank_id"] = prank_id
                user["extensions"]["chosenButton"] = "Ввод телефона"
                bot.send_message(message.chat.id, "Введи номер человека, которому хочешь заказать звонок в формате +7xxxxxxxxxx", reply_markup = backKeyboard)
            except Exception as e:
                pass
            
    elif user["extensions"]["chosenButton"] == "Ввод телефона":
        if message.text == "Назад ↩️":
            jokesKeyboard = getJokesKeyboard(message.chat.id)
            user["extensions"]["chosenButton"] = "Все розыгрыши"
            bot.send_message(message.chat.id, "Возвращаю...", reply_markup = jokesKeyboard)
        else:
            user["extensions"]["chosenButton"] = "Оплата и звонок"
            phone = re.search("^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$", message.text)
            #Проверяем телефон с помощью регулярного выражения
            if phone:
                with closing(pymysql.connect(host='localhost', user='root', password='', db='callprank', charset='utf8mb4', cursorclass=DictCursor)) as conn:
                    with conn.cursor() as cursor:
                        data = [(message.chat.id, message.text, 0, user["extensions"]["prank_id"], 0)]
                        query = 'INSERT INTO orders (chat_id, phone, isPaid, prank_id, done) VALUES (%s, %s, %s, %s, %s)'
                        cursor.executemany(query, data)
                        conn.commit()
                        
                        sql = ("SELECT * FROM orders ORDER BY id")
                        cursor.execute(sql)
                        orders = cursor.fetchall()
                payment_id = orders[-1]["id"]
                bot.send_message(message.chat.id, "Оплатите звонок одним кликом: http://127.0.0.1/pay/%s" % payment_id, reply_markup = backKeyboard)
        
    elif user["extensions"]["chosenButton"] == "Оплата и звонок":
        if message.text == "Назад ↩️":
            user["extensions"]["chosenButton"] = "Ввод телефона"
            bot.send_message(message.chat.id, "Введи номер человека, которому хочешь заказать звонок", reply_markup = backKeyboard)
        else:
            phone = re.search("^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$", message.text)
            #Проверяем телефон с помощью регулярного выражения
            undone_order = None
            if phone:
                with closing(pymysql.connect(host = "localhost", user = "root", password = "", db = "callprank", charset = "utf8mb4")) as conn:
                    with conn.cursor() as cursor:
                        query = ("SELECT * FROM orders WHERE done=0 AND isPaid=1 AND chat_id=%s") % message.chat.id
                        cursor.execute(query)
                        undone_orders = cursor.fetchall()
                #Получаем оплаченные, но не выполненные заказы пользователя
                
                if len(undone_orders) != 0:
                    undone_order = undone_orders[0]
                    call(undone_order["chat_id"], campaigns[undone_order["prank_id"]-1], undone_order["phone"], undone_order["id"])
                    #Добавляем звонок в очередь
                    
if __name__ == '__main__':
    bot.polling(none_stop = False, interval = 0, timeout = 20)