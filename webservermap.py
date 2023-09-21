from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import re
from urllib.parse import parse_qsl, urlparse
import redis

# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html


mapping = [
    (r"^/books/(?P<book_id>\d+)$", "get_book"),
    (r"^/$", "get_index"),
    (r"^/search$", "get_search"),
    (r"^/results$", "get_results"),
]

class WebRequestHandler(BaseHTTPRequestHandler):
    # @cached_property
    # def url(self):
    #     return urlparse(self.path)

    # @cached_property
    # def query_data(self):
    #     return dict(parse_qsl(self.url.query))

    # @cached_property
    # def post_data(self):
    #     content_length = int(self.headers.get("Content-Length", 0))
    #     return self.rfile.read(content_length)

    # @cached_property
    # def form_data(self):
    #     return dict(parse_qsl(self.post_data.decode("utf-8")))

    # @cached_property
    # def cookies(self):
    #     return SimpleCookie(self.headers.get("Cookie"))

    def do_GET(self):
        self.url = urlparse(self.path)
        method = self.get_method(self.url.path)
        if method:
            method_name, dict_params = method
            method = getattr(self, method_name)
            method(**dict_params)
            return 
        else:
            print("No se encontró el método")
            self.send_error(404, "Not Found") 
        # self.query_data = dict(parse_qsl(self.url.query))
        # self.send_response(200)
        # self.send_header("Content-Type", "text/html")
        # self.end_headers()
        # self.wfile.write(self.get_response().encode("utf-8"))

    def get_method(self, path):
        for pattern, method in mapping:
            match = re.match(pattern, path)
            if match:
                return (method, match.groupdict())
            
    def get_book(self, book_id):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
        if r.exists(f'book{book_id}'):
            f = r.get(f'book{book_id}')
            return self.wfile.write(f.encode("utf-8"))
        return self.send_error(404, "Not Found in Redis")

    def get_index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        with open ("html/index.html", "r") as f:
            response = f.read()
        return self.wfile.write(response.encode("utf-8"))

def set_redis_keys():
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    for book in os.listdir('html/books'):
        with open(f'html/books/{book}') as book_file:
            r.set(f'{book.split(".")[0]}', book_file.read())
            print(f'Key {book} set')
    r.connection_pool.disconnect()

if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 80), WebRequestHandler)
    set_redis_keys()
    server.serve_forever()
