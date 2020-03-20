#!/usr/bin/env python3
import json
from zeroconf import ServiceBrowser, Zeroconf
import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid
import asyncio
from tornado.options import define, options
define("port", default=1234, help="Port to listen on", type=int)

class MyListener:
    def remove_service(self, zeroconf, type, name):
        print("Service {} removed".format(name))

    def add_service(self, zeroconf, type, name):
        asyncio.set_event_loop(asyncio.new_event_loop())
        info = zeroconf.get_service_info(type, name)
        print(info.properties)
        try:
            serviceData = {
                'name': info.name,
                'server': info.server,
                'port': info.port,
                'httpEndpoint': info.properties['httpEndpoint'.encode()].decode(),
                'wsEndpoint': info.properties['wsEndpoint'.encode()].decode(),
                'schemaEndpoint': info.properties['schemaEndpoint'.encode()].decode(),
                'websocketsOnly': info.properties['websocketsOnly'.encode()],
                'uuid': info.properties['uuid'.encode()].decode(),
                'service_type': info.properties['service_type'.encode()].decode(),
            }
            ZeroConfHandler.send_data(serviceData)
            print("Service {} added, service info: {}".format(name, json.dumps(serviceData)))
        except Exception as e:
            print("Error sending service info: {}".format(repr(e)))


class Application(tornado.web.Application):
    def __init__(self):
        # Setup zeroconf listener
        zeroconf = Zeroconf()
        listener = MyListener()
        browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

        handlers = [(r"/", ZeroConfHandler)]
        settings = dict(
            cookie_secret="asdlkfjhfiguhefgrkjbfdlgkjadfh",
            xsrf_cookies=True,
        )
        super(Application, self).__init__(handlers, **settings)


class ZeroConfHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 200

    #def initialize(self):
    #    print("eek")

    def check_origin(self, origin):
        return True

    def get_compression_options(self):
        return {}

    def open(self):
        ZeroConfHandler.waiters.add(self)
        #self.write_message("Hi, client: connection is made ...")
        print('client connection')

    def on_close(self):
        ZeroConfHandler.waiters.remove(self)
        self.write_message("Bye client!")
        print("Closing client")

    @classmethod
    def send_data(cls, data):
        print("sending message: {}".format(data))
        for waiter in cls.waiters:
            try:
                waiter.write_message(data)
            except Exception as e:
                print("Error sending message: {}".format(repr(e)))

def main():
    # Setup tornado
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()