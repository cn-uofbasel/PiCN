"""Interface Layer (REST API)"""

from PiCN.Processes import LayerProcess
from PiCN.Packets.Content import Content

import multiprocessing
import shelve
from http.server import BaseHTTPRequestHandler
import socketserver
import http.server
import ssl


class DataHandler(BaseHTTPRequestHandler):
    queue_to_lower = None
    heads_name = None  # name of latest block for every sensor
    heads_timestamp = None  # timestamp of latest sample for every sensor

    def handle_post_data(self, body):
        try:
            # split body
            samples = body.decode('utf-8').split("|")
            sensor_id = samples[0]
            data_body = samples[1]
            # sensor prefix
            sensor_prefix = "/ch/unibas/beesens/" + sensor_id
            # update or create heads
            if sensor_id in self.heads_name:
                # check if received values are not already inserted
                if float(data_body.split(":")[0]) < self.heads_timestamp[sensor_id]:
                    return True
                # increment heads_name
                last_comp = self.heads_name[sensor_id].rfind('/') + 1
                incr_block_num = str(int(self.heads_name[sensor_id][last_comp:]) + 1)
                self.heads_name[sensor_id] = sensor_prefix + "/" + incr_block_num
            else:
                self.heads_name[sensor_id] = sensor_prefix + "/1"
                self.send_to_storage(Content(sensor_prefix, "ptr:" + self.heads_name[sensor_id]))
            self.heads_timestamp[sensor_id] = float(data_body.split(",")[-1].split(":")[0])
            # create content objects
            last_comp = self.heads_name[sensor_id].rfind('/') + 1
            incr_block_num = str(int(self.heads_name[sensor_id][last_comp:]) + 1)
            ptr_to_next = sensor_prefix + "/" + incr_block_num
            payload = data_body + "\nptr:" + ptr_to_next
            content = Content(self.heads_name[sensor_id], payload)
            # TODO - split into multiple content objects if exceeds a certain length (e.g. chunk size of 4096 bytes)
            self.send_to_storage(content)
            return True
        except:
            return False

    def do_POST(self):
        body_len = int(self.headers['Content-Length'])
        body = self.rfile.read(body_len)
        if self.handle_post_data(body):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(418)  # I'm a teapot
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"failed")

    def do_GET(self):
        self.send_response(404)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Use POST to write data.")

    def send_to_storage(self, content: Content):
        self.queue_to_lower.put(content)


class InterfaceLayer(LayerProcess):
    def __init__(self, http_port=8080, log_level=255, database_path="/tmp", flush_database=False, pem_path=None):
        super().__init__(logger_name="REST API", log_level=log_level)
        self.pem_path = pem_path
        self.database_path = database_path
        self.http_port = http_port
        self.heads_name = shelve.open(self.database_path + "/beesens-heads-name.db")
        self.heads_timestamp = shelve.open(self.database_path + "/beesens-heads-timestamp.db")
        if flush_database:
            self.heads_name.clear()
            self.heads_timestamp.clear()

    def _run(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
             to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        handler = DataHandler
        handler.queue_to_lower = to_lower
        handler.heads_name = self.heads_name
        handler.heads_timestamp = self.heads_timestamp

        if self.pem_path is None:
            # without ssl (http)
            with socketserver.TCPServer(("", self.http_port), handler) as httpd:
                httpd.serve_forever()
        else:
            # with ssl (https)
            with http.server.HTTPServer(("", self.http_port), handler) as httpd:
                httpd.socket = ssl.wrap_socket(httpd.socket, server_side=True, certfile=self.pem_path,
                                               ssl_version=ssl.PROTOCOL_TLS)
                httpd.serve_forever()
