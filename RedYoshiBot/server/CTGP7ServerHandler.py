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
import random
import sys
import ctypes
import signal

from .CTGP7Requests import CTGP7Requests
from .CTGP7ServerDatabase import CTGP7ServerDatabase
from .CTGP7CtwwHandler import CTGP7CtwwHandler
from .CTGP7ServerCritical import do_critical_operations_in, do_critical_operations_out

class CTGP7ServerHandler:
    
    logging_lock = threading.Lock()
    debug_mode = False
    myself = None
    loggerCallback = lambda x : x 
    white_listed_consoleIDs = []

    @staticmethod
    def logMessageToFile(message):
        if (CTGP7ServerHandler.debug_mode):
            if (len(CTGP7ServerHandler.white_listed_consoleIDs) == 0 or any([(str(m) in message) for m in CTGP7ServerHandler.white_listed_consoleIDs])):
                print(message)
        else:
            if (CTGP7ServerHandler.loggerCallback is not None):
                CTGP7ServerHandler.loggerCallback(message)

    class PostGetHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            what = ""
            if (len(self.path) >= 3 and self.path[0] == "/" and self.path[2] == "/"):
                what = self.path[1]
            
            if (what == "t"):
                token = self.path[3:]
                password = CTGP7ServerHandler.myself.ctwwHandler.get_password_from_token(token)

                if password is None: # Generate random password
                    password = ''.join(random.choices("0123456789ABCDEF", k=16))

                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.send_header("Content-length", len(password))
                self.end_headers()
                self.wfile.write(bytes(password, "ascii"))
            else:
                textret = "Not Found"
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                self.send_header("Content-length", len(textret))
                self.end_headers()
                self.wfile.write(bytes(textret, "ascii"))

        def do_POST(self):
            if (not do_critical_operations_in(CTGP7ServerHandler.myself, self)):
                return
            
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

                if "_CSH1" in inputData and "_CSH2" in inputData:
                    isLegal = CTGP7ServerHandler.myself.database.verify_console_legality(reqConsoleID, inputData["_CSH1"], inputData["_CSH2"])
                    if not isLegal:
                        skipExceptionPrint = True
                        raise Exception("Illegal console detected")

                solver = CTGP7Requests(CTGP7ServerHandler.myself.database, CTGP7ServerHandler.myself.ctwwHandler, inputData, CTGP7ServerHandler.debug_mode, reqConsoleID)
                outputData.update(solver.solve())
                logStr += solver.info

                outputData["_CID"] = reqConsoleID
                outputData["_seed"] = inputData["_seed"]
                outputData["res"] = 0
          
                if (not do_critical_operations_out(CTGP7ServerHandler.myself, self, outputData)):
                    return

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
            # if (CTGP7ServerHandler.debug_mode):
            #    BaseHTTPRequestHandler.log_message(self, format, *args)
            pass

    class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
        pass

    def __init__(self, isDebugOn: bool):

        CTGP7ServerHandler.debug_mode = isDebugOn
        CTGP7ServerHandler.myself = self

        try:
            with open("debugConsoleID.txt", "r") as f:
                CTGP7ServerHandler.white_listed_consoleIDs = f.read().strip().split(" ")
        except:
            pass

        self.database = CTGP7ServerDatabase()
        self.database.connect()

        self.ctwwHandler = CTGP7CtwwHandler(self.database)

        server_thread = threading.Thread(target=self.server_start)
        server_thread.daemon = True
        server_thread.start()

        self.nex = None

    def terminate(self):
        self.nex.terminate()
        self.nex = None
        self.database.disconnect()
        self.database = None
        self.ctwwHandler = None
        CTGP7ServerHandler.myself = None
        print("CTGP-7 server terminated.")
    
    def server_start(self):
        self.server = self.ThreadingSimpleServer(("", 64334), self.PostGetHandler)
        context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_1)
        context.options |= ssl.OP_NO_TLSv1_2
        context.load_cert_chain('RedYoshiBot/server/data/server.pem')
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)

        libc = ctypes.CDLL("libc.so.6")
        def set_pdeathsig(sig = signal.SIGTERM):
            def callable():
                return libc.prctl(1, sig)
            return callable
        self.nex = subprocess.Popen(["./mario-kart-7-secure"], stdout=subprocess.DEVNULL, preexec_fn=set_pdeathsig(signal.SIGTERM))

        print("CTGP-7 server started.")
        self.server.serve_forever()
