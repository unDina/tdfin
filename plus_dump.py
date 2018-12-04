# coding: utf-8
import uuid
import tdfin
import os
import json
import io
import sys

# Заливка данных с одного аккаунта на другой
# Заменяет все айдишники на случайные (userid на нужный)

userid = tdfin.config["userid"]

# открываем дамп, из которого будем делать дифф
with open(tdfin.config["plus_dump_in"]) as f:
    data = json.load(f)

# Проверяем, какие теги и мерчанты есть в транзакциях, и оставляем в дампе только их
tagdict = {t["id"]: t for t in data["tag"]}
tagsweneed = set([])
merchdict = {m["id"]: m for m in data["merchant"]}
merchweneed = set([])

for tr in data["transaction"]:
    for tg in tr["tag"]:
        tagsweneed.add(tg)
    for mr in tr["merchant"]:
        merchweneed.add(mr)

for tg in tagsweneed:
    if tg["parent"]:
        tagsweneed.add(tg["parent"])

data["tag"] = [tagdict[i] for i in tagsweneed]
data["merchant"] = [merchdict[i] for i in merchweneed]

# создаём новые id аккаунтам, тэгам, мерчантам и транзакциям, меняем их во всех ссылках, меняем юзеров
debtid = None

for i, account in enumerate(data["account"]):
    newid = str(uuid.uuid4())
    for transaction in data["transaction"]:
        if transaction["incomeAccount"] == account["id"]:
            transaction["incomeAccount"] = newid
        if transaction["outcomeAccount"] == account["id"]:
            transaction["outcomeAccount"] = newid
    account["id"] = newid
    if userid:
        account["user"] = userid  # меняет userid для тестовой базы
    if account["type"] == "debt": debtid = i

if debtid is not None:
    del data["account"][debtid]

for tag in data["tag"]:
    newid = str(uuid.uuid4())
    for transaction in data["transaction"]:
        if transaction["tag"]:
            for i, tr_tag in enumerate(transaction["tag"]):
                if tr_tag == tag["id"]:
                    transaction["tag"][i] = newid
    for child_tag in data["tag"]:
        if child_tag["parent"] == tag["id"]:
            child_tag["parent"] = newid
    tag["id"] = newid
    if userid:
        tag["user"] = userid # меняет userid для тестовой базы

for merchant in data["merchant"]:
    newid = str(uuid.uuid4())
    for transaction in data["transaction"]:
        if transaction["merchant"] == merchant["id"]:
            transaction["merchant"] = newid
    merchant["id"] = newid
    if userid:
        merchant["user"] = userid # меняет userid для тестовой базы

for transaction in data["transaction"]:
    transaction["id"] = str(uuid.uuid4())
    if userid:
        transaction["user"] = userid # меняет userid для тестовой базы


# удаляем из дампа неизменяемые сущности
del data["user"]

del data["country"]

del data["company"]

del data["instrument"]

# сохраняем дифф
tdfin.save_file(data, tdfin.config["plus_dump_out"])

# заливаем дифф на сервер, ответ сервера сохраняем
tdfin.tdfin(data, tdfin.config["plus_dump_answer"])