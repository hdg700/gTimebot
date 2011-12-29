#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Danilenko A."
__email__ = "hdg700@gmail.com"

import timebot
import select
import config
import models
import sys

def main():
    models.initModels()
    xmpp_conn = timebot.Connection(config.CONF_GMAIL_LOGIN, config.CONF_GMAIL_PASS)
    if not xmpp_conn.connect():
        exit(2)

    bot = timebot.Timebot(xmpp_conn)

    socklist = [xmpp_conn.getSock()]
    while True:
        (i, o, e) = select.select(socklist, [], [], 2)
        if not i:
            continue

        for sock in i:
            if sock == xmpp_conn.getSock():
                xmpp_conn.client.Process(1)

if __name__ == "__main__":
    main()
