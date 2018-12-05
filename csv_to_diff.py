# coding: utf-8
import uuid
import tdfin
import os
import json
import pandas as pd
import sys
from datetime import datetime as dt

def check_and_propagate(a, b, name):
    if a is None and b is None:
        raise Exception("Both transaction {} are missing".format(name))
    if a is None:
        a = b
    if b is None:
        b = a
    return a, b

def replace_date(timestamp):
    # createdDate                      2017-07-13 11:49:43
    return int(dt.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%s"))

def replace_double(value):
    if value is None:
        return 0
    if isinstance(value, basestring):
        value = value.replace(",", ".")
    return float(value)

def replace_instrument(shorttitle, data):
    if shorttitle is None:
        return None
    for instrument in data["instrument"]:
        if instrument["shortTitle"] == shorttitle: return instrument["id"]
    raise Exception("Unknown shortTitle of instrument {}".format(shorttitle))

def replace_account(acname, data):
    if acname is None:
        return None
    for account in data["account"]:
        if account["title"] == acname:
            return account["id"]
    raise Exception("Unknown account name {}".format(acname.encode("utf-8")))

def replace_merchant(merchname, ts, data, merchants):
    if not merchname:
        return None

    for merchant in data["merchant"] + merchants:
        if merchant["title"] == merchname:
            return merchant["id"]

    new_id = tdfin.newid()
    merchants.append({
        "title": merchname, 
        "changed": ts, 
        "id": new_id, 
        "user": tdfin.config["userid"]
    })

    return new_id

small_letter_set = set(u"ёйцукенгшщзхъфывапролджэячсмитьбюqwertyuiopasdfghjklzxcvbnm")

def replace_tag(tagname, ts, data, newtags):
    """
    Получение списка id категорий по строке

    tagname -- Строка с категориями.
    ts -- Время создания категории если её не было.
    data -- Данные дампа.
    newtags -- Список новых категорий.
    Возвращает список идентификаторов категорий.
    Может добавить диффы для новых категорий в newtags.

    Пример строки: "Еда / Продукты, Путешествия / Россия 2018"
    Здесь две категории, обе имеют родителей.
    """
    if not tagname:
        return None

    # Извлекаем список отдельных категорий. Например "Еда / Продукты"
    tagsplit = tagname.split(", ")
    tags = [tagsplit[0]]
    for tagpiece in tagsplit[1:]:
        if tagpiece[0] in small_letter_set:
            tags[-1] += ", " + tagpiece
        else:
            tags.append(tagpiece)

    # Сюда складываем идентификаторы искомых тегов
    results = []

    # Перебираем категории
    for tag in tags:
        tagseq = tag.split(" / ")

        # Для каждого элемента (например "Еда" или "Продукты") ищем или создаём тег 
        # В current_id будем хранить его идентификатор
        current_id = None
        for tagitem in tagseq:
            # Ищем среди имеющихся
            for data_tag in data["tag"] + newtags:
                # Нужный тег должен иметь то же название и такого же родителя
                if data_tag["parent"] == current_id and data_tag["title"] == tagitem:
                    current_id = data_tag["id"]
                    break
            # Если не нашли, добавляем
            else:
                new_id = tdfin.newid()
                newtags.append({
                    "id": new_id,
                    "user": tdfin.config["userid"],
                    "changed": ts,
                    "icon": None,
                    "budgetIncome": False,
                    "budgetOutcome": False,
                    "required": None,
                    "color": None,
                    "picture": None,
                    "title": tagitem,
                    "showIncome": True,
                    "showOutcome": True,
                    "parent": current_id                    
                })
                current_id = new_id

        results.append(current_id)
    return results



# скачиваем актуальный дамп с сервера, сохраняем результат в data
data = tdfin.get_dump()

# загружаем csv
csv_data = pd.read_csv(tdfin.config["csv_to_diff_in"], header = tdfin.config["csv_to_diff_header"], encoding="utf-8")

## Пример строчки из файла с дампом из телефона
# date                                      2017-07-13
# categoryName                          Еда / Продукты
# payee                            MAGAZIN  N1, MOSCOW
# comment                                          NaN
# outcomeAccountName                           BANK N1
# outcome                                         1234
# outcomeCurrencyShortTitle                        RUB
# incomeAccountName                            BANK N1
# income                                             0
# incomeCurrencyShortTitle                         RUB
# createdDate                      2017-07-13 11:49:43
# changedDate                      2018-06-24 16:38:21
## В csv с сайта отличие в формате income/outcome (там "," в качестве плавающей точки)

# создаём список транзакций по загруженному csv
transactions = []

# создаём список новых мерчантов (которых не было в дампе)
merchants = []

# создаём список новых тегов (которых не было в дампе)
tags = []


# заменяем в csv nan на None
csv_data = csv_data.where(csv_data.notnull(), None)

known_trans = set([(t["created"], t["changed"], t["income"], t["outcome"]) for t in data["transaction"]]) if "transaction" in data else {}

# обрабатываем транзакции из csv 
for i, line in csv_data.iterrows():
    try:
        created_ts = replace_date(line["createdDate"])
        changed_ts = replace_date(line["changedDate"])
        income_account = replace_account(line["incomeAccountName"], data)
        outcome_account = replace_account(line["outcomeAccountName"], data)
        income_instrument = replace_instrument(line["incomeCurrencyShortTitle"], data)
        outcome_instrument = replace_instrument(line["outcomeCurrencyShortTitle"], data) 
        # проверка на отсутствие обоих аккаунтов транзакциии и дозаполнение
        income_account, outcome_account = check_and_propagate(income_account, outcome_account, "accounts")
        # проверка на отстутствие обоих валют и дозаполнение
        income_instrument, outcome_instrument = check_and_propagate(income_instrument, outcome_instrument, "instruments")
        # проверка на дубли
        if (created_ts, changed_ts, line["income"], line["outcome"]) in known_trans :
            # raise Exception("Duplicate:\n{}".format(str(line)))
            # print "Duplicate:\n{}".format(str(line))
            sys.stdout.write(".")
            sys.stdout.flush()
        else:
            transactions.append({
                "comment": line["comment"], 
                "opOutcomeInstrument": None, 
                "tag": replace_tag(line["categoryName"], created_ts, data, tags), 
                "opOutcome": None, 
                "outcomeAccount": outcome_account,  
                "id": tdfin.newid(), 
                "incomeAccount": income_account, 
                "incomeBankID": None, 
                "incomeInstrument": income_instrument, 
                "outcomeBankID": None, 
                "opIncomeInstrument": None, 
                "income": replace_double(line["income"]), 
                "qrCode": None, 
                "reminderMarker": None, 
                "originalPayee": line["payee"], 
                "merchant": replace_merchant(line["payee"], created_ts, data, merchants), 
                "deleted": False, 
                "latitude": None, 
                "user": tdfin.config["userid"], 
                "date": line["date"], 
                "hold": None,  # Предположительно, когда транзакция автоматически распозналась с смски, это поле True,
                # но мы решили пока везде поставить None 
                "opIncome": None, 
                "created": created_ts, 
                "changed": changed_ts, 
                "longitude": None, 
                "payee": line["payee"], 
                "outcome": replace_double(line["outcome"]), 
                "outcomeInstrument": outcome_instrument
            })
            known_trans.add((created_ts, changed_ts, line["income"], line["outcome"]))
        # много транзакций сразу не пролазят
        if len(transactions) > 200: break
    except:
        print >> sys.stderr, "line", i
        raise

print

# кладём в дифф новые транзакции, мерчанты и тэги
result_data = {"transaction": transactions}
if merchants:
    result_data["merchant"] = merchants
if tags:
    result_data["tag"] = tags

# сохраняем результат в файл
tdfin.save_file(result_data, tdfin.config["csv_to_diff_out"])

# заливаем результат на сервер, ответ сервера кладём в другой файл
tdfin.tdfin(result_data, tdfin.config["csv_to_diff_answer"])

