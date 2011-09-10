#!/usr/bin/python2.6
# -*- coding: utf-8 -*-

import socket
import select
import sys

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 8000))
    server.listen(5)

    socklist = [server, sys.stdin]
    clients = []
    stop = False
    while not stop:
        i = select.select(socklist + clients, [], [], 2)[0]

        for s in i:
            if s == server:
                client = server.accept()
                print 'New client: ', client[1]
                clients.append(client[0])
            elif s == sys.stdin:
                text = sys.stdin.readline().strip()
                if text and text == 'exit':
                    stop = True
                    break
                else:
                    [i.send(text) for i in clients]

            else:
                try:
                    data = s.recv(1024)
                    if data:
                        print unicode(data, 'utf-8') + '\n'
                    else:
                        s.close()
                        clients.remove(s)
                        print 'Client removed'
                except socket.error as e:
                    s.close()
                    clients.remove(s)
                    print 'Client removed'

if __name__ == "__main__":
    main()
