# coding: utf-8
import uuid
import tdfin
import os
import json
import pandas as pd
from datetime import datetime as dt

def replace_date(timestamp):
    # createdDate                      2017-07-13 11:49:43
    return int(dt.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%s"))

def replace_instrument(shorttitle, data):
    for instrument in data["instrument"]:
        if instrument["shortTitle"] == shorttitle: return instrument["id"]
    raise Exception("Unknown shortTitle of instrument {}".format(shorttitle))

def replace_account(acname, data):
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
csv_data = pd.read_csv(tdfin.config["csv_to_diff_in"], encoding="utf-8")

## Пример строчки из файла
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
    created_ts = replace_date(line["createdDate"])
    changed_ts = replace_date(line["changedDate"])
    # проверка на дубли
    if (created_ts, changed_ts, line["income"], line["outcome"]) in known_trans :
        raise Exception("Duplicate:\n{}".format(str(line)))
    else:
        transactions.append({
            "comment": line["comment"], 
            "opOutcomeInstrument": None, 
            "tag": replace_tag(line["categoryName"], created_ts, data, tags), 
            "opOutcome": None, 
            "outcomeAccount": replace_account(line["outcomeAccountName"], data), 
            "id": tdfin.newid(), 
            "incomeAccount": replace_account(line["incomeAccountName"], data), 
            "incomeBankID": None, 
            "incomeInstrument": replace_instrument(line["incomeCurrencyShortTitle"], data), 
            "outcomeBankID": None, 
            "opIncomeInstrument": None, 
            "income": line["income"], 
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
            "outcome": line["outcome"], 
            "outcomeInstrument": replace_instrument(line["outcomeCurrencyShortTitle"], data)
        })
        known_trans.add((created_ts, changed_ts, line["income"], line["outcome"]))
    # много транзакций сразу не пролазят
    if i > 200: break
    
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

