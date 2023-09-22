from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import re
from urllib.parse import parse_qsl, urlparse
import redis
from html.parser import HTMLParser
import html

# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html


class MyHTMLParser(HTMLParser):

    def __init__(self, tagArray: tuple, tagValue: str):
        super().__init__()
        self.data = []
        self.capture = False
        self.tagArray = tagArray
        self.tagValue = tagValue

    def handle_starttag(self, tag, attrs):
        if tag in self.tagArray:
            for name, value in attrs:
                if name == 'id' and value == self.tagValue:
                    print('Encountered a start tag:', tag)
                    self.capture = True

    def handle_endtag(self, tag):
        if tag in self.tagArray:
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data.append(data)

mapping = [
    (r"^/$", "get_index"),
    (r"^/books/(?P<book_id>\d+)$", "get_book"),
    (r"^/books/search$", "get_search_books"),
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
    
    def get_search_books(self):
        
        query_data = dict(parse_qsl(self.url.query))
        print(query_data)
        params = [query_data.get('author'), query_data.get('title'), query_data.get('description')]
        if not any(params):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open('html/books/search.html', 'r') as f:
                response = f.read()
            return self.wfile.write(response.encode("utf-8"))

        r = redis.StrictRedis(host='localhost', port=6379, db=0, charset="utf-8", decode_responses=True)
        books = r.keys('book*')
        books_found = set()
        for book in books:
            book_data = r.get(book)
            author = query_data.get('author')
            title = query_data.get('title')
            description = query_data.get('description')
            not_none_params = [i for i in params if i is not None]

            if title:
                title_parser = MyHTMLParser(('h2'), 'title')
                title_parser.feed(book_data)
                if title.lower() not in title_parser.data[0].lower():
                    continue
            if author:
                author_parser = MyHTMLParser(('p'), 'author')
                author_parser.feed(book_data)
                print(author_parser.data[0].lower(), author.lower())
                if author.lower() not in author_parser.data[0].lower():
                    continue
            if description:
                description_parser = MyHTMLParser(('p'), 'description')
                description_parser.feed(book_data)
                if description.lower() not in description_parser.data[0].lower():
                    continue
            print('Book found: ', book)
            books_found.add(book)

        r.connection_pool.disconnect()

        print('Books found: ', books_found)
        with open('html/books/search.html') as f:
                response = f.read()
        if books_found:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                for book in books_found:
                    book_data = r.get(book)
                    title_parser = MyHTMLParser(('h2'), 'title')
                    title_parser.feed(book_data)
                    response += f'<br><li><a href="/books/{book.split("book")[1]}">{title_parser.data[0]}</a></li>'
                return self.wfile.write(response.encode("utf-8"))
        response += '<p>No books found</p>'
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        return self.wfile.write(response.encode("utf-8"))

def set_redis_keys():
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    for book in os.listdir('html/books'):
        with open(f'html/books/{book}') as book_file:
            if book.startswith('book'):
                r.set(f'{book.split(".")[0]}', book_file.read())
                print(f'Key {book} set')
    r.connection_pool.disconnect()

if __name__ == "__main__":
    print("Server starting...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    set_redis_keys()
    server.serve_forever()
