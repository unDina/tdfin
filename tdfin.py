# coding: utf-8
from requests_oauthlib import OAuth2Session
import datetime
import sys
import os.path
import json
import io
import uuid
import yaml

# Чтобы выдать приложению доступ к нашим данным используются эти технологические URL-ы
the_authorization_url = 'https://api.zenmoney.ru/oauth2/authorize/'
access_token_url = 'https://api.zenmoney.ru/oauth2/token/'

# Адрес API синхронизации
protected_url = 'https://api.zenmoney.ru/v8/diff/'

# Имя конфигурационного файла по умолчанию
config_name = "tdfin.yaml"

# https://github.com/zenmoney/ZenPlugins/wiki/ZenMoney-API -- правильная дока

config = config_data()

def load_config(path):
    if os.path.exists(path):
        with open(path) as f:
            return yaml.load(f)

def config_data():
    if len(sys.argv) > 1:
        data = load_config(sys.argv[1])
        if data:
            return data
        else:
            raise Exception("Problem loading specified config '{}'".format(sys.argv[1])) 
    data = load_config(config_name)
    if data:
        return data    
    data = load_config(os.path.join(os.path.expanduser("~"), ".config", config_name))
    if data:
        return data
    raise Exception("No config found")

def oauthorize():
    "Получить объект oauth с новым токеном"

    # Сперва мы получаем адрес по которому подтвеждаем, что разрешаем выдать доступ к нашим данным
    # После подтверждения браузер сделает редирект на redirect_uri со спецпараметрами в адресе

    oauth = OAuth2Session(config["client_key"], redirect_uri=config["redirect_url"])
    authorization_url, _ = oauth.authorization_url(the_authorization_url)

    print 'Authorize %s' % authorization_url
    authorization_response = raw_input('Enter the full callback URL: ')

    # Fetch an access token from the provider using the authorization code obtained during user authorization.
    return oauth, oauth.fetch_token(access_token_url, authorization_response=authorization_response, client_secret=config["client_secret"])

def oauth():
    """
    Получить объект oauth

    Если в параметрах командной строки передан файл с токеном, создаётся объект с имеющимся токеном.
    Иначе получаем новый токен (с запросом подтверждения пользователя).
    Если в параметрах командной строки передано имя файла (которого нет или в нём нет токена), новый токен сохраняется туда.
    """

    if "token_filename" in config and os.path.exists(config["token_filename"]):
        try:
            with open(config["token_filename"]) as f:
                oauth = OAuth2Session(config["client_key"], token=json.load(f))
                return oauth
        except:
            pass

    oauth, token = oauthorize()
    if "token_filename" in config:
        with open(config["token_filename"], "w") as f:
            json.dump(dict(token), f)

    return oauth

def save_file(result_data, filename):
    with io.open(filename, 'w', encoding='utf8') as json_file:
        newdata = json.dumps(result_data, ensure_ascii=False, indent=4)
        # unicode(data) auto-decodes data to unicode if str
        json_file.write(unicode(newdata))

def tdfin(data, filename):
    json_data={"currentClientTimestamp": int(datetime.datetime.now().strftime("%s")), "serverTimestamp": 0}
    json_data.update(data)
    # oauth -- объект, сходный с requests (точнее с requests.Session). позволяет делать HTTP-запросы.
    # POST-запрос синхронизации. Передаём наш таймстемп и таймстемп сервера, который нам известен. 0 -- никакого неизвестно.
    r = oauth().post(protected_url, json=json_data)

    # Результат огромен. Сохраняем его в файл.
    save_file(r.json(), filename)

def newid():
    return str(uuid.uuid4())

def get_dump():
    tdfin({}, "tmpdump.json")
    with open("tmpdump.json") as f:
        data = json.load(f)
    os.unlink("tmpdump.json")
    return data

if __name__ == "__main__":
    tdfin({}, config["tdfin_out"])