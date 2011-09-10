# -*- coding: utf-8 -*-

"""Report thread module"""

__author__ = "Danilenko A."
__email__ = "hdg700@gmail.com"

from models import *
import threading

class ReportThread(threading.Thread):
    def __init__(self, func, *args):
        self.func = func
        self.args = args
        threading.Thread.__init__(self)

    def run(self):
        self.func(*self.args)
