#!/usr/bin/python2.6
# -*- coding: utf-8 -*-

import config
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker

engine = None
meta = None
session = None

def initConnection():
    global engine
    global meta

    if not engine:
        engine = create_engine(config.CONF_DB_DSN)
        meta = MetaData(engine)

def getEngine():
    global engine

    if not engine:
        initConnection()
    return engine

def getMeta():
    global meta

    if not meta:
        initConnection()
    return meta

def getSession():
    global engine
    global session

    if not engine:
        initConnection()

    if not session:
        Session = sessionmaker(bind=engine)
        session = Session()
        
    return session



