from socket import *
from threading import Thread
import re
from urllib.parse import urlparse
import os.path
from tm import render_template

class server:
    def __init__(self):
        self.host = ""
        self.port = 6666
        self.listen = 521
        self.recvNum = 1024
        self.routeInfo = []
        self.ico = "1.ico"
        self.staticDir = "static"
        self.template = "template"
        self.staticType = ".jpg,.png,.gif,.css,.js,.html" #后缀名是静态文件
        self.mimeType = {".jpg":"image/jpeg",".png":"image/png",".gif":"image/gif",".css":"text/css",".js":"application/x-javascript",".html":"text/html"}

    #6.采集路由的信息
    def route(self,url,methods=["GET"]):
        def run(callback):
            obj = {}
            obj["params"] = re.findall(r":([^/]+)",url)   #保存参数
            obj["url"] = re.sub(r":[^/]+","(\w+)",url)
            obj["callback"] = callback
            obj["methods"] = methods
            self.routeInfo.append(obj)
        return run

    # 8.设置头参数信息
    def parse_headers(self, response):
        info = ""
        info += response["headers"]["pool"] + " " + response["headers"]["status_code"] + "\r\n"
        info += "content-type:" + response["headers"]["content-type"] + "\r\n\r\n"
        return info.encode(encoding="utf8")

    # 7.请求的路由动态的处理
    def route_handle(self,tcpData,tcpSocket):
        flag = True
        for item in self.routeInfo:
            reg = item["url"]
            result = re.match(r"%s" % (reg), tcpData["path"])
            if result and item["methods"].count(tcpData["type"]) > 0:
                for item1 in range(len(item["params"])):

                    tcpData["params"][item["params"][item1]] = result.group(item1 + 1)
                flag = False
                response = {}
                response["headers"] = {}
                response["headers"]["pool"] = "HTTP/1.1"
                response["headers"]["status_code"] = "200 OK"
                response["headers"]["content-type"] = "text/html;charset=utf-8"
                body = item["callback"](tcpData, response)
                headers = self.parse_headers(response)
                tcpSocket.send(headers + body.encode(encoding="utf8"))
                tcpSocket.close()
                break
        if flag:
            tcpSocket.send(b"this page not find")
            tcpSocket.close()

    #5.处理请求的逻辑
    def request_handle(self,tcpData,tcpSocket):
        url = tcpData["path"]
        if url == "/favicon.ico":
            try:
                f = open(self.ico,"rb")
                icoInfo = f.read()
                f.close()
                tcpSocket.send(b"HTTP/1.1 200 OK\r\ncontent-type:image/x-icon\r\n\r\n"+icoInfo)
                tcpSocket.close()
            except:
                tcpSocket.send(b"HTTP/1.1 404 NOT FIND")
                tcpSocket.close()
        #？？？？？？？？？？？？？？？？？？？？？？
        elif self.staticType.find(os.path.splitext(url)[1])>-1 and os.path.splitext(url)[1]:
            if os.path.isdir(self.staticDir):   #目录的话执行条件体
                fullpath = os.path.join(self.staticDir,url[1:])
                if os.path.isfile(fullpath):
                    fobj = open(fullpath,"rb")
                    con = fobj.read()
                    fobj.close()
                    tcpSocket.send(("HTTP/1.1 200 OK\r\ncontent-type:"+self.mimeType[os.path.splitext(url)[1]]+";charset=utf-8\r\n\r\n").encode(encoding="utf8")+con)
                    tcpSocket.close()
                else:
                    tcpSocket.send(b"HTTP/1.1 404 NOT FIND")
                    tcpSocket.close()
        else:
            print("动态路径")
            self.route_handle(tcpData, tcpSocket)

    #4.对客户端请求的数据进行格式化
    def requestData_handle(self,tcpData):
        obj = {}
        requestInfo = tcpData.splitlines()
        if len(requestInfo)>0:
            urlInfo = requestInfo[0]
            type = re.match(r"[^\s]*",urlInfo).group(0)   #GET方式
            obj["type"] = type
            requestUrl = urlparse(re.match(r"\w+\s+([^\s]*)", urlInfo).group(1))   #路径
            obj["path"] = requestUrl[2]
            obj["query"] = {}
            obj["params"] = {}
            if requestUrl[4]:
                for item in requestUrl[4].split("&"):
                    arr = item.split("=")
                    obj["query"][arr[0]] = arr[1]
        return obj

    #3.开启线程，接受到新的客户端连接的内容
    def startHandle(self,tcpSocket,tcpAddr):
        tcpData = tcpSocket.recv(self.recvNum).decode(encoding="utf8")

        #每一条数据处理之前先进行格式化
        # self.requestData_handle(tcpData)

        #对请求的每一条数据进行处理
        self.request_handle(self.requestData_handle(tcpData),tcpSocket)

    #2.创建服务器
    def create_socket(self):
        tcp = socket(AF_INET,SOCK_STREAM)
        tcp.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
        tcp.bind((self.host,self.port))
        tcp.listen(self.listen)
        print(self.host + str(self.port) + "启动成功")
        while True:
            tcpSocket,tcpAddr = tcp.accept()
            Thread(target=self.startHandle,args=(tcpSocket,tcpAddr)).start()

    #1.开启
    def start(self,host="",port=9999,listen=521):
        self.host = host
        self.port = port
        self.listen = listen
        self.create_socket()
