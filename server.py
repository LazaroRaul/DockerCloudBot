from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests
import telebot
from tinydb import TinyDB, where
import ssl

reposDB = TinyDB("repo.json")
linkDB = TinyDB("link.json")
userDB = TinyDB("users.json")

API_KEY = '<apikey>'
BOT_HOST = "/%s" % API_KEY
BOT_URL = "https://api.telegram.org/bot%s/sendMessage" % API_KEY
GH_COMMIT = "https://github.com/%s/commit/%s"
GH_BRANCH = "https://github.com/%s/tree/%s"
DCK_REPO = "https://hub.docker.com/r/%s"
DCK_BLD = "https://cloud.docker.com/u/%s/repository/docker/%s/builds/%s"
LINK = "[%s](%s)"

EMOJIS = {'Success':u'\U00002705', 'Failed':u'\U00002757', 'Canceled':u'\U000023F9', 'whale': u'\U0001F433', "Queued":u'\U000023F0'}

INFO = '''
I'm a Docker Cloud Bot. I can notify you about builds of your repositories.

Available commands:
/link - Add new repository to receive notifications from Docker Cloud
/list - List all current repositories
/delete - Delete repository
/help - Print this message
'''


class RequestHandler(BaseHTTPRequestHandler):

    def isKnowUser(self, chat_id):
        return len(userDB.search(where('id') == chat_id)) != 0

    def addUser(self, chat_id, params, add=True):
        if add:
            userDB.insert({'id': chat_id})
        params['text'] = INFO
        requests.get(url=BOT_URL, params=params)

    def sendInfo(self, data):
        repo = data['repo']
        for chat in linkDB.search(where('repo') == repo):
            action = data['action']
            branch = action[action.index("'") + 1: action.rindex("'")]

            commit = GH_COMMIT % (data['source'], data['commit'])
            github = GH_BRANCH % (data['source'], branch)
            docker = DCK_REPO % repo
            build = DCK_BLD % (repo[:repo.index("/")], repo, data['uuid'])
            
            commitId = action[action.index("(") + 1: action.index(")")]
            action = action[:action.index("(") + 1] + LINK % (commitId, commit) + action[action.index(")"):]
            action = action[:action.index("'") + 1] + LINK % (branch, github) + action[action.rindex("'"):]
            action = action.replace("Build in", "Build [[%s](%s)] in" % (data['uuid'][:8], build))

            elapsed = int(data['time'])
            h = elapsed // 3600
            elapsed -= h * 3600
            m = elapsed // 60
            s = elapsed - m * 60
            duration = ""
            if h > 0:
                duration += "%d h " % h
            if m > 0:
                duration += "%d min " % m
            if s > 0:
                duration += "%d sec " % s

            msg = EMOJIS['whale'] + " " + EMOJIS[data['status']] 
            msg += " [%s](%s):%s: \n%s \nResult %s in %s" % (repo, docker, data['tag'], action, data['status'], duration)
            params['text'] = msg
            requests.get(url=BOT_URL, params=params)

    def botAction(self, chat_id, text, params):
        if self.isKnowUser(chat_id):
            if text == '/help' or text == '/start':
                self.addUser(chat_id, params, False)
            elif text[:6] == '/link ':
                self.addRepo(chat_id, text[6:], params)
            elif text == '/list':   
                self.ShowRepos(chat_id, params)
            elif text[:8] == '/delete ':   
                self.DeleteRepo(chat_id, text[8:], params)
            else:
                requests.get(url=BOT_URL, params=params)
        elif text == '/help' or text == '/start':
            self.addUser(chat_id, params)
        elif text[:6] == '/link ' or text == '/list' or text[:8] == '/delete ':
            params['text'] = "You are not allow to do this action right now. Use /start and try again"
            requests.get(url=BOT_URL, params=params)
        else:
            requests.get(url=BOT_URL, params=params)

    def addRepo(self, chat_id, repo, params):
        if len(linkDB.search(where('id') == chat_id and where('repo') == repo)) == 0:
            linkDB.insert({'id': chat_id, 'repo': repo})
            info = reposDB.search(where('name') == repo)
            if len(info) == 0:
                reposDB.insert({"name": repo, "id": "null", "status": "null", "cant":"1"})
            else:
                reposDB.update({"cant":str(int(info[0]["cant"]) + 1)}, where('name') == repo)
            params['text'] = "repository added correctly"
        else:
            params['text'] = "you already has that repository" 
        requests.get(url=BOT_URL, params=params)

    def ShowRepos(self, chat_id, params):
        l = linkDB.search(where('id') == chat_id)
        repos = list(map(lambda x: LINK % (x['repo'], DCK_REPO % x['repo']), l))
        params['text'] = "\n".join(repos) if len(repos) != 0 else "you don't have any repository yet"
        requests.get(url=BOT_URL, params=params)

    def DeleteRepo(self, chat_id, repo, params):
        old = len(linkDB)
        linkDB.remove(where('id') == chat_id and where('repo') == repo)
        if old != len(linkDB):
            params['text'] = "Repository removed"
            cant = int(reposDB.search(where('name') == repo)[0]["cant"]) - 1
            if cant > 0:
                reposDB.update({"cant":str(cant)}, where('name') == repo)
            else:
                reposDB.remove(where('name') == repo)
        else:
            params['text'] = "You don't have that repository"
        requests.get(url=BOT_URL, params=params)

    def do_POST(self):
        json_string = self.rfile.read(int(self.headers['content-length']))
        print(self.path)
        print(json_string)
        self.send_response(200)
        self.end_headers()

        if self.path == BOT_HOST:
            print("bot connection")
            upd = telebot.types.Update.de_json(json_string.decode())
            text = upd.message.text
            chat_id = upd.message.chat.id
            params = {'chat_id': chat_id, 'text': "Sorry, I'm not talkative", "parse_mode":"Markdown"}
            self.botAction(chat_id, text, params)
        elif self.path == '/update':
            self.sendInfo(json.loads(json_string))
        else:
            print("unknown connection")


def run(addr='0.0.0.0', port=8443):
    server = HTTPServer((addr, port), RequestHandler)
    server.socket = ssl.wrap_socket (server.socket, server_side=True, certfile='<yourcert>.pem', keyfile='<yourkey>.pem', ssl_version=ssl.PROTOCOL_TLSv1)
    server.serve_forever()


if __name__ == '__main__':
    run()

