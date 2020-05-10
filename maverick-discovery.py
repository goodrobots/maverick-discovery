#!/usr/bin/env python3
import json
import tornado.ioloop
import tornado.web
import tornado.websocket
import asyncio
from tornado.options import define, options
define("ws_port", default=6001, help="Non-encrypted port to listen on", type=int)
define("wss_port", default=6002, help="Encrypted port to listen on", type=int)
define("ssl_key", help="SSL key path", type=str)
define("ssl_cert", help="SSL certificate path", type=str)
from zeroconf import ServiceBrowser, Zeroconf

class MyListener:
    def remove_service(self, zeroconf, type, name):
        ZeroConfHandler.remove_cache(name)

    def add_service(self, zeroconf, type, name):
        asyncio.set_event_loop(asyncio.new_event_loop())
        info = zeroconf.get_service_info(type, name)
        serviceData = {}
        # First try to format a maverick-api service
        if 'maverick-api' in info.name:
            try:
                serviceData = {
                    'port': info.port,
                    'name': info.properties['name'.encode()].decode(),
                    'httpEndpoint': info.properties['httpEndpoint'.encode()].decode(),
                    'httpsEndpoint': info.properties['httpsEndpoint'.encode()].decode() if 'httpsEndpoint'.encode() in info.properties else None,
                    'wsEndpoint': info.properties['wsEndpoint'.encode()].decode(),
                    'wssEndpoint': info.properties['wssEndpoint'.encode()].decode() if 'wssEndpoint'.encode() in info.properties else None,
                    'schemaEndpoint': info.properties['schemaEndpoint'.encode()].decode(),
                    'schemasEndpoint': info.properties['schemasEndpoint'.encode()].decode() if 'schemasEndpoint'.encode() in info.properties else None,
                    'websocketsOnly': info.properties['websocketsOnly'.encode()].decode(),
                    'uuid': info.properties['uuid'.encode()].decode(),
                    'service_name': info.name,
                    'service_type': info.properties['service_type'.encode()].decode(),
                    'hostname': info.properties['hostname'.encode()].decode(),
                }
            except Exception as e:
                print("Error formatting API service info: {} : {}".format(repr(e), info), flush=True)
        if 'visiond-webrtc' in info.name:
            try:
                serviceData = {
                    'port': info.port,
                    'name': info.properties['name'.encode()].decode(),
                    'wsEndpoint': info.properties['wsEndpoint'.encode()].decode(),
                    'uuid': info.properties['uuid'.encode()].decode(),
                    'service_name': info.name,
                    'service_type': info.properties['service_type'.encode()].decode(),
                    'hostname': info.properties['hostname'.encode()].decode(),
                }
            except Exception as e:
                print("Error formatting Visiond service info: {}".format(repr(e)), flush=True)

        if serviceData:
            ZeroConfHandler.send_data(serviceData)
            ZeroConfHandler.update_cache(serviceData)


class Application(tornado.web.Application):
    def __init__(self):
        # Setup zeroconf listener
        zeroconf = Zeroconf()
        listener = MyListener()
        browser = ServiceBrowser(zc=zeroconf, type_="_api._tcp.local.", listener=listener)
        browser = ServiceBrowser(zc=zeroconf, type_="_webrtc._udp.local.", listener=listener)

        # Setup websocket handler
        handlers = [(r"/", ZeroConfHandler)]
        settings = dict(
            cookie_secret="asdlkfjhfiguhefgrkjbfdlgkjadfh",
            xsrf_cookies=True,
        )
        super(Application, self).__init__(handlers, **settings)


class ZeroConfHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = {}
    #cache_size = 200

    def check_origin(self, origin):
        return True

    def get_compression_options(self):
        return {}

    def open(self):
        ZeroConfHandler.waiters.add(self)
        #self.write_message("Hi, client: connection is made ...")
        print('client connection', flush=True)
        for entry in ZeroConfHandler.cache:
            ZeroConfHandler.send_data(ZeroConfHandler.cache[entry])
            print("Sending entry to new client: {}".format(entry), flush=True)

    def on_close(self):
        ZeroConfHandler.waiters.remove(self)
        print("Closing client", flush=True)

    @classmethod
    def send_data(cls, data):
        for waiter in cls.waiters:
            try:
                print("Sending message to {}: {}".format(waiter, data), flush=True)
                waiter.write_message(data)
            except Exception as e:
                print("Error sending message: {}".format(repr(e)), flush=True)

    @classmethod
    def update_cache(cls, data):
        try:
            cls.cache[data['name']] = data
            #if len(cls.cache) > cls.cache_size:
            #    cls.cache = cls.cache[-cls.cache_size :]
            print(" - Data added to cache: {}".format(data), flush=True)
        except Exception as e:
            print(" - Error adding to cache: {}".format(repr(e)), flush=True)

    @classmethod
    def remove_cache(cls, data):
        del cls.cache[data]
        print("Deleted {} from cache".format(data), flush=True)

def main():
    # Setup tornado
    print("Starting maverick-discovery", flush=True)
    tornado.options.parse_command_line()
    discovery_app = Application()

    print(f"Listening on non-encrypted port {options.ws_port}", flush=True)
    ws_server = tornado.httpserver.HTTPServer(discovery_app)
    ws_server.listen(int(options.ws_port), address='0.0.0.0')

    options.ssl_cert = "/srv/maverick/data/security/ssl/web/mavweb.crt"
    options.ssl_key = "/srv/maverick/data/security/ssl/web/mavweb.key"
    if options.ssl_cert and options.ssl_key:
        print(f"Listening on encrypted port {options.wss_port}", flush=True)
        ssl_options = dict(certfile=options.ssl_cert, keyfile=options.ssl_key)
        wss_server = tornado.httpserver.HTTPServer(discovery_app, ssl_options=ssl_options)
        wss_server.listen(int(options.wss_port), address='0.0.0.0')

    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()