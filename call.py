import os
import requests
import pymysql
from pymysql.cursors import DictCursor
from contextlib import closing
from bot import bot
import asyncio
import aiohttp
import time

url = "https://calltools.ru/lk/cabapi_external/api/v1/phones/call/"
#URL для создания звонка
token = "YOUR_TOKEN"
#Публичный токен, получаем на сайте https://zvonok.com/

def call(chat_id, campaign_id, number, order_id):
    status = None
    #Статус звонка
    attempt = 0
    #Количество попыток дозвона
    
    bot.send_message(chat_id, "Звонок поставлен в очередь. \nВ течение минуты будет выполнен дозвон.")
    #Отправляем уведомление

    data = {"public_key": token,
            "phone": number,
            "campaign_id": campaign_id}

    call = requests.post(url, data = data)
    #Добавляем звонок в очередь
    
    call_info = call.json()
    #Получаем информацию
    call_id = call_info["call_id"]
    #ID созданного звонка
    
    params = {"public_key": token, 
              "call_id": call_id}
    
    while status != "compl_finished":
        call_details = requests.get("https://calltools.ru/lk/cabapi_external/api/v1/phones/call_by_id/", params = params).json()
        #Получаем информацию о звонке
        print(call_details)
        status = call_details[0]["status"]
        #Получаем статус
        attempt += 1
        #Проверяем кол-во запрсов к API
        if attempt > 8:
            bot.send_message(chat_id, "Мы не смогли дозвониться. Попробуйте указать другой номер.")
            break
        if call_details[0]["recorded_audio"] and call_details[0]["dial_status"] in (10, 5):
            record_url = call_details[0]["recorded_audio"]
            #Получаем URL записи звонка
            trace = "records\\" + str(call_id) + ".mp3"
            #Указываем путь к папке с записями
            r = open(trace, "wb")
            #Открываем директорию
            record = requests.get(record_url)
            #Получаем запись звонка
            r.write(record.content)
            r.close()
            #Сохраняем аудио и закрываем
            
            bot.send_voice(chat_id, open(trace, "rb"), caption = "Запись разговора:")
            #Отправляем запись разговора
            os.remove(trace)
            #Удаляем аудиозапись
            
            with closing(pymysql.connect(host="localhost", user="root", password="", db="callprank", charset="utf8mb4")) as conn:
                with conn.cursor() as cursor:
                    query = "UPDATE orders SET done=1 WHERE id=%s" % str(order_id)
                    cursor.execute(query)
                    conn.commit()
            #Меняем поле заказа в БД на "Выполнено"
            
            break
            
        time.sleep(15)
        
    return 1