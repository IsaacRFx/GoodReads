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
        self.query_data = dict(parse_qsl(self.url.query))
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(self.get_response())


    def validate_endpoint(self):
        
        endpoint = self.url.path.split('/')[1].lower()
        indexPath = f"index.html"
        commonPath = f'html{self.url.path}.html'
        parsedPath = f"{endpoint}{self.url.path.split('/')[-1]}.html"
        print(endpoint)
        if endpoint == "":
            return indexPath
        if os.path.isfile(commonPath):
            return parsedPath
        return parsedPath

    def get_response(self):
        isValidEndpoint = self.validate_endpoint()
        if not isValidEndpoint:
            return """404 Not Found"""
        if not isValidEndpoint.endswith('.html'):
            return """404 Not Found"""
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        keyExists = r.exists(f'{isValidEndpoint}')
        if keyExists == 1:
            print(f'Key {isValidEndpoint} exists')
            f = r.get(f'{isValidEndpoint}')
            return f
        r.connection_pool.disconnect()
        return """404 Not Found"""

def set_redis_keys():
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    for dirpath, dirs, files in os.walk('html'):
        for filename in files:
            if filename.endswith('.html'):
                with open(os.path.join(dirpath, filename)) as f:
                    r.set(f'{filename}', f.read())
                    print(f'Key {filename} set')
    r.connection_pool.disconnect()

if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 80), WebRequestHandler)
    set_redis_keys()
    server.serve_forever()
