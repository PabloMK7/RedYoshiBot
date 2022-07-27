from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import ssl
from urllib import parse
import bson
import sqlite3
import datetime
import os
import traceback
import subprocess

from .CTGP7Requests import CTGP7Requests
from .CTGP7ServerDatabase import CTGP7ServerDatabase
from .CTGP7CtwwHandler import CTGP7CtwwHandler

class CTGP7ServerHandler:
    
    logging_lock = threading.Lock()
    debug_mode = False
    myself = None
    loggerCallback = lambda x : x 

    @staticmethod
    def logMessageToFile(message):
        if (CTGP7ServerHandler.debug_mode):
            print(message)
        else:
            if (CTGP7ServerHandler.loggerCallback is not None):
                CTGP7ServerHandler.loggerCallback(message)

    class PostHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            timeNow = datetime.datetime.now()
            
            connDataLen = int(self.headers['Content-Length'])
            connData = self.rfile.read(connDataLen)

            outputData = {}
            logStr = "--------------------\n"
            logStr += "Timestamp: {}\n".format(timeNow.isoformat())

            skipExceptionPrint = False

            try:
                process = subprocess.Popen(["./encbsondocument", "d"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                process.stdin.write(connData)
                process.stdin.flush()
                
                connData = process.stdout.read()
                process.wait()
                
                if (process.returncode != 0):
                    raise Exception("Couldn't decrypt message: {}".format(process.returncode))

                inputData = bson.loads(connData)
                if not "_CID" in inputData or not "_seed" in inputData:
                    skipExceptionPrint = True
                    raise Exception("Input is missing: cID: {}, seed: {}".format(not "_CID" in inputData, not "_seed" in inputData))
                
                reqConsoleID = inputData["_CID"]

                logStr += "Console ID: 0x{:016X}\n".format(reqConsoleID)

                solver = CTGP7Requests(CTGP7ServerHandler.myself.database, CTGP7ServerHandler.myself.ctwwHandler, inputData, CTGP7ServerHandler.debug_mode, reqConsoleID)
                outputData.update(solver.solve())
                logStr += solver.info

                outputData["_CID"] = reqConsoleID
                outputData["_seed"] = inputData["_seed"]
                outputData["res"] = 0

            except Exception:
                outputData["res"] = -1
                if not skipExceptionPrint: traceback.print_exc()
            
            process = subprocess.Popen(["./encbsondocument", "e"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            process.stdin.write(bson.dumps(outputData))
            process.stdin.flush()

            connOutData = process.stdout.read()
            process.wait()
            if (process.returncode != 0):
                connOutData = b'\x00\x00\x00\x00' # wtf?

            connOutLen = len(connOutData)
            
            self.send_response(200)
            self.send_header('Content-Type',
                            '"application/octet-stream"')
            self.send_header("Content-Length", connOutLen)
            self.end_headers()
            
            self.wfile.write(connOutData)
            
            elap = datetime.datetime.now() - timeNow
            logStr += "Elapsed: {:.3f}ms\n".format(elap.seconds * 1000 + elap.microseconds / 1000)
            logStr += "--------------------\n"

            with CTGP7ServerHandler.logging_lock:
                CTGP7ServerHandler.logMessageToFile(logStr)
        
        def log_message(self, format, *args):
            if (CTGP7ServerHandler.debug_mode):
                BaseHTTPRequestHandler.log_message(self, format, *args)

    class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
        pass

    def __init__(self, isDebugOn: bool):

        CTGP7ServerHandler.debug_mode = isDebugOn
        CTGP7ServerHandler.myself = self

        self.database = CTGP7ServerDatabase()
        self.database.connect()

        self.ctwwHandler = CTGP7CtwwHandler(self.database)

        server_thread = threading.Thread(target=self.server_start)
        server_thread.daemon = True
        server_thread.start()

    def terminate(self):
        self.database.disconnect()
        self.database = None
        self.ctwwHandler = None
        CTGP7ServerHandler.myself = None
        print("CTGP-7 server terminated.")
    
    def server_start(self):
        self.server = self.ThreadingSimpleServer(("", 64333), self.PostHandler)
        context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_1)
        context.options |= ssl.OP_NO_TLSv1_2
        context.load_cert_chain('RedYoshiBot/server/data/server.pem')
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        print("CTGP-7 server started.")
        self.server.serve_forever()
