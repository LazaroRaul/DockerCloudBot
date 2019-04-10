from json import dumps
from parse import parse
import requests
from requests.auth import HTTPBasicAuth
from tinydb import TinyDB, where
from time import sleep

reposDB = TinyDB("repos.json")

BOT = "https://dockerbot.simelo.tech:8443/update"
SITE = "https://cloud.docker.com/api/audit/v1/action/"
API = "/api/repo/v1/repository/%s/"
params = {"include_related":"true", "limit":"2"}
ARGS = '{"repo":"%s", "time":"%d", "build":"%s", "source":"%s", "commit":"%s", "tag":"%s", "action":"%s", "status":"%s", "uuid":"%s"}' 
user = "<yourUser>"
password = "<yourPassword>"
date = '{}, {} {} {} {}:{}:{} {}'

def elapsedSeconds(data):
    t = parse(date, data)
    return int(t[4]) * 3600 + int(t[5]) * 60 + int(t[6])

def getUpdates():
    for repo in reposDB.all():
        print(repo)
        name = repo['name']
        p["object"] = API % name
        req = requests.get(url=SITE, params=p, auth=HTTPBasicAuth(user, password))
        if req.ok:
            print("ok")
            js = req.json()['objects'][0]
            if js['action'] == "Repository Push":
                js = req.json()['objects'][1]
            last = repo['id']
            print(js['action'])
            build = js['build_code']
            commit = js['commit']
            end = js['end_date']
            if commit != None and end != None and build != last:
                state = js['state']
                reposDB.update({'id':build, 'status':state}, where('name') == name)
                start = js['created']
                elapsed = elapsedSeconds(end) - elapsedSeconds(start)
                body = ARGS % (name, elapsed, build, js['source_repo'], commit, js['build_tag'], js['action'], state, js['uuid'])
                requests.post(url=, data=body)


while True:
    getUpdates()
    sleep(30)
