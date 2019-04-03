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

use https://dockerbot.simelo.tech:8443/tl as your Docker webhook to recive notifications
'''


class RequestHandler(BaseHTTPRequestHandler):

    def isKnowUser(self, chat_id):
        return len(userDB.search(where('id') == chat_id)) != 0

    def addUser(self, chat_id, params):
        if not self.isKnowUser(chat_id):
            userDB.insert({'id': chat_id})
        params['text'] = "now you can use /repo <id> to recive your builds status"
        requests.get(url=BOT_URL, params=params)

    def addRepo(self, chat_id, repo, params):
        if self.isKnowUser(chat_id):
            if len(reposDB.search(where('id') == chat_id and where('repo') == repo)) == 0:
               reposDB.insert({'id': chat_id, 'repo': repo})
               params['text'] = "repository added correctly"
            else:
                params['text'] = "you already has that repository" 
        else:
            params['text'] = "You are not allow to do this action right now. Use /start and try again"
        requests.get(url=BOT_URL, params=params)

    def sendInfo(self, repo, status):
        l = reposDB.search(where('repo') == repo)
        for chat in l:
            params = {'chat_id': chat['id'], 'text': "Last build on %s is '%s'" % (repo, status)}
            requests.get(url=BOT_URL, params=params)

    def ShowRepos(self, chat_id, params):
        if self.isKnowUser(chat_id):
            l = reposDB.search(where('id') == chat_id)
            repos = list(map(lambda x: x['repo'], l))
            params['text'] = "\n".join(repos) if len(repos) != 0 else "you don't have any repository yet"
        else:
            params['text'] = "You are not allow to do this action right now. Use /start and try again"
        requests.get(url=BOT_URL, params=params)

    def DeleteRepo(chat_id, chat_id, repo, params):
        if self.isKnowUser(chat_id):
            reposDB.remove(reposDB.search(where('id') == chat_id and where('repo') == repo))
            params['text'] = "removed"
        else:
            params['text'] = "You are not allow to do this action right now. Use /start and try again"
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
            params = {'chat_id': chat_id, 'text': "Sorry, I'am not talkative"}
            if '/start' in text:
                self.addUser(chat_id, params)
            elif '/help' in text:
                params = {'chat_id': chat_id, 'text': INFO}
                requests.get(url=BOT_URL, params=params)
            elif '/link' in text:
                self.addRepo(chat_id, text[6:], params)
            elif '/list' in text:   
                self.ShowRepos(chat_id, params)
            elif '/delete' in text:   
                self.DeleteRepo(chat_id, text[8:], params)
            else:
                requests.get(url=BOT_URL, params=params)
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

