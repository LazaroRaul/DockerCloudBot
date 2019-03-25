from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests
import telebot
import tinydb
import ssl

reposDB = tinydb.TinyDB("repos.json")
userDB = tinydb.TinyDB("users.json")
q = tinydb.Query()

API_KEY = '<apikey>'
BOT_HOST = "/%s" % API_KEY 
DOCKER_HOST = "/docker"
BOT_URL = "https://api.telegram.org/bot%s/sendMessage" % API_KEY


class RequestHandler(BaseHTTPRequestHandler):

    def isKnowUser(self, chat_id):
        return len(userDB.search(q.id == chat_id)) != 0

    def addUser(self, chat_id, params):
        if not self.isKnowUser(chat_id):
            userDB.insert({'id': chat_id})
        params['text'] = "now you can use /repo <id> to recive your builds status"
        requests.get(url=BOT_URL, params=params)

    def addRepo(self, chat_id, repo, params):
        if self.isKnowUser(chat_id) and reposDB.search(q.id == chat_id and q.repo == repo):
            userDB.insert({'id': chat_id, 'repo': repo})
            params['text'] = "repo added correctly"
        else:
            params['text'] = "You are not allow to do this action right now"
        requests.get(url=BOT_URL, params=params)

    def sendInfo(self, repo, status):
        l = reposDB.search(q.repo == repo)
        for chat in l:
            params = {'chat_id': chat['id'], 'text': "Last build is '%s'" % status}
            requests.get(url=BOT_URL, params=params)

    def do_POST(self):
        json_string = self.rfile.read(int(self.headers['content-length']))

        self.send_response(200)
        self.end_headers()

        if self.path == BOT_HOST:
            upd = telebot.types.Update.de_json(json_string)
            text = upd.message.text
            chat_id = upd.message.chat.id
            params = {'chat_id': chat_id, 'text': "Sorry, I'am not talkative"}
            if '/start' in text:
                self.addUser(chat_id, params)
            elif '/repo' in text:
                self.addRepo(chat_id, text[6:], params)
            else:
                requests.get(url=BOT_URL, params=params)
        elif self.path == DOCKER_HOST:
            hook = json.loads(json_string)
            repo = hook["push_data"]["pushed_at"]
            status = hook["repository"]["status"]
            self.sendInfo(repo, status)
        else:
            print("unknown connection")


def run(addr='0.0.0.0', port=8443):
    #GENERATE AN SSL CERTIFICATE
    # openssl genrsa -out key.pem 2048
    # openssl req -new -x509 -days 3650 -key key.pem -out cert.pem
    server = HTTPServer((addr, port), RequestHandler)
    httpd.socket = ssl.wrap_socket (httpd.socket, server_side=True, certfile='./cert.pem', keyfile='./key.pem', ssl_version=ssl.PROTOCOL_TLSv1)
    server.serve_forever()


if __name__ == '__main__':
    run()
