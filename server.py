from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests
import telebot
from tinydb import TinyDB, where
import ssl

reposDB = TinyDB("repos.json")
userDB = TinyDB("users.json")

API_KEY = '<apikey>'
BOT_HOST = "/%s" % API_KEY 
DOCKER_HOST = "/tl"
BOT_URL = "https://api.telegram.org/bot%s/sendMessage" % API_KEY

INFO = '''
I'm a Docker Cloud Bot. I can notify you about builds of your repositories.

Available commands:
/link - Add new repository to receive notifications from Docker Cloud
/list - List all current repositories
/delete - Delete repository
/help - Print this message

Use https://dockerbot.simelo.tech:8443/tl as your Docker webhook to receive notifications
'''


class RequestHandler(BaseHTTPRequestHandler):

    def isKnowUser(self, chat_id):
        return len(userDB.search(where('id') == chat_id)) != 0

    def addUser(self, chat_id, params, add=True):
        if add:
            userDB.insert({'id': chat_id})
        params['text'] = INFO
        requests.get(url=BOT_URL, params=params)

    def sendInfo(self, repo, status):
        l = reposDB.search(where('repo') == repo)
        for chat in l:
            params = {'chat_id': chat['id'], 'text': "Last build on %s is '%s'" % (repo, status)}
            requests.get(url=BOT_URL, params=params)

    def botAction(self, chat_id, text, params):
        if isKnowUser(chat_id):
            if text == '/help' or text == '/start':
                self.addUser(chat_id, params, False)
            elif text[:6] == '/link ':
                self.addRepo(chat_id, text[6:], params)
            elif text == '/list':   
                self.ShowRepos(chat_id, params)
            elif text[:8] == '/delete ':   
                self.DeleteRepo(chat_id, text[8:], params)
            else
                requests.get(url=BOT_URL, params=params)
        elif text == '/help' or text == '/start':
            self.addUser(chat_id, params)
        else:
            params['text'] = "You are not allow to do this action right now. Use /start and try again"
            requests.get(url=BOT_URL, params=params)

    def addRepo(self, chat_id, repo, params):
        if len(reposDB.search(where('id') == chat_id and where('repo') == repo)) == 0:
           reposDB.insert({'id': chat_id, 'repo': repo})
           params['text'] = "repository added correctly"
        else:
            params['text'] = "you already has that repository" 
        requests.get(url=BOT_URL, params=params)

    def ShowRepos(self, chat_id, params):
        l = reposDB.search(where('id') == chat_id)
        repos = list(map(lambda x: x['repo'], l))
        params['text'] = "\n".join(repos) if len(repos) != 0 else "you don't have any repository yet"
        requests.get(url=BOT_URL, params=params)

    def DeleteRepo(chat_id, chat_id, repo, params):
        old = len(reposDB)
        reposDB.remove(where('id') == chat_id and where('repo') == repo)
        if old != len(reposDB):
            params['text'] = "Repository removed"
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
            params = {'chat_id': chat_id, 'text': "Sorry, I'm not talkative"}
            self.botAction(chat_id, text, params)
        elif self.path == DOCKER_HOST:
            print("docker connection")
            hook = json.loads(json_string)
            repo = hook["repository"]["repo_name"]
            status = hook["repository"]["status"]
            self.sendInfo(repo, status)
        else:
            print("unknown connection")


def run(addr='0.0.0.0', port=8443):
    server = HTTPServer((addr, port), RequestHandler)
    server.socket = ssl.wrap_socket (server.socket, server_side=True, certfile='<yourcert>.pem', keyfile='<yourkey>.pem', ssl_version=ssl.PROTOCOL_TLSv1)
    server.serve_forever()


if __name__ == '__main__':
    run()

