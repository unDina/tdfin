# coding: utf-8
import uuid
import tdfin
import os
import json

# Вначале удалить всё через интерфейс, потом запустить этот скрипт

data = tdfin.get_dump()

deletion = []
if "tag" in data:
    deletion += [
    {'id': tag["id"],
    'object': 'tag',
    'user': tdfin.config["userid"],
    'stamp': 1490008039
    }
    for tag in data["tag"]
    ] 
if "account" in data:
    deletion += [{'id': account["id"],
    'object': 'account',
    'user': tdfin.config["userid"],
    'stamp': 1490008039
    }
    for account in data["account"]
    ]

if "merchant" in data:
    deletion += [{'id': merchant["id"],
    'object': 'merchant',
    'user': tdfin.config["userid"],
    'stamp': 1490008039
    }
    for merchant in data["merchant"]
    ]

data = {'deletion': deletion}

tdfin.tdfin(data, tdfin.config["minus_all_answer"])