# -*- coding: utf8 -*-

import hashlib
import requests
from flask import Flask, request, render_template, redirect
from app import app
import pymysql
from pymysql.cursors import DictCursor
from contextlib import closing
import requests
from call import *

mrh_login = "YOUR_LOGIN"
mrh_pass1 = "YOUR_PASS1"
mrh_pass2 = "YOUR_PASS2"
#Данные для авторизации, получаем при регистрации магазина на https://robokassa.com/
inv_desc = "Оплата розыгрыша звонком"
isTest = 1
out_summ = "15.00"
#Сумму указывать как строку, то есть в кавычках
payment_id = 1

campaigns = [2087771364]
#ID кампаний по обзвону
 
def generate_id(account_id):
    with closing(pymysql.connect(host='localhost', user='root', password='', db='callprank', charset='utf8mb4', cursorclass=DictCursor)) as conn:
        with conn.cursor() as cur:
            sql = ("SELECT * FROM orders WHERE id=%s") % account_id
            cur.execute(sql)
            orders = cur.fetchall()
    if len(orders) != 0:
        payment_id = orders[-1]["id"]
        #Сверяем ID с данными из БД
    return payment_id
 
def check_hash(pwd):
    answer = False
    try:
        crc = request.args["SignatureValue"]
        my_crc = hashlib.md5("{}:{}:{}".format(request.args["OutSum"],
        request.args["InvId"], mrh_pass1).encode("utf-8")).hexdigest()
        #Проверяем на свопадение хеши пользователя и магазина
        if crc != my_crc:
            print("Bad sign: <br>Хеш 1:{}<br>Хеш 2:{}".format(crc,my_crc))
        else:
            answer = True
    except KeyError:
        pass
    return answer
    
@app.route('/pay/<int:account_id>/')
def create_pay(account_id):
    inv_id = generate_id(account_id)
    payment_id = inv_id
    crc = hashlib.md5("{}:{}:{}:{}".format(mrh_login, out_summ, inv_id, mrh_pass1).encode("utf-8"))
    data = {"mrh_login" : mrh_login,
            "out_summ" : out_summ,
            "inv_id" : inv_id,
            "inv_desc" : inv_desc,
            "crc" : crc.hexdigest(),
            "isTest" : isTest}

    url = "https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=" + str(data["mrh_login"]) + "&OutSum=" + str(data["out_summ"]) + "&InvoiceID=" + str(data["inv_id"]) + "&Description=" + str(data["inv_desc"]) + "&SignatureValue=" + str(data["crc"]) + "&IsTest=" + str(data["isTest"])
    #Генерируем ссылку для оплаты и делаем редирект
    return redirect(url, code=302)

@app.route('/success')
def success():
    #Успешная оплата при переходе пользователем
    if check_hash(mrh_pass1):
        payment_id = request.args["InvId"]
        #Возвращаем пользователя обратно в Telegram
        return redirect("https://tele.gg/CallPrankBot", code=302)
    return "Refused"

@app.route('/result')
def result():
    #Успешная оплата, запрос от Робокассы с помощью CURL
    if check_hash(mrh_pass2):
        payment_id = request.args["InvId"]
        print(payment_id)
        with closing(pymysql.connect(host='localhost', user='root', password='', db='callprank', charset='utf8mb4', cursorclass=DictCursor)) as conn:
            with conn.cursor() as cursor:
                query = 'UPDATE orders SET isPaid=1 WHERE id=%s' % payment_id
                print(query)
                cursor.execute(query)
                conn.commit()
                
                sql = ("SELECT * FROM orders WHERE id=%s") % payment_id
                cursor.execute(sql)
                order = cursor.fetchall()
        
        call(order[0]["chat_id"], campaigns[order[0]["prank_id"]-1], order[0]["phone"], payment_id)
        #Ставим звонок в очередь
        return "Success"
    return "Refused"
 
if __name__ == "__main__":
    app.run(port=80, debug=True)