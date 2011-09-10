#!/usr/bin/python2.6
# -*- coding: utf-8 -*-

"""
Timebot models definition module
"""

from sqlalchemy import *
from sqlalchemy.orm import mapper, relation
from sqlalchemy.orm.exc import *
from datetime import datetime, date, timedelta
import db

class TUser(object):
    """Timebot user model"""
    def __init__(self, jid, name, rate=None):
        """Timebot user class initialization"""
        self.jid = jid
        self.name = name

        if rate:
            self.rate = rate

    def __repr__(self):
        return '<TUser: {0} ({1})>'.format(self.name, self.jid)


class TCompany(object):
    """Timebot company model"""
    def __init__(self, name):
        """Timebot company class initialization"""
        self.name = name

    def __repr__(self):
        return '<TCompany: {0} ({1})>'.format(self.id, self.name)


class TWorktime(object):
    """Timebot worktime model"""
    def __init__(self, user):
        """Timebot worktime class initialization"""
        self.user = user

    def __repr__(self):
        return '<TWorktime: {0} ({1})>'.format(self.id, self.user.jid)


class TUserManager(object):
    """TUser database table manager
    Provides query methods"""
    def __init__(self):
        """TUserManager constructor
        Inits session"""
        self.session = db.getSession()

    def add(self, obj):
        """Proxy method for session.add"""
        self.session.add(obj)

    def flush(self):
        """Proxy method for session.flush"""
        self.session.flush()
        
    def hasUser(self, jid):
        """This method checks if there is already such user in db"""
        try:
            self.session.query(TUser).filter(TUser.jid == jid).one()
            return True
        except NoResultFound:
            return False

    def getUserByJid(self, jid):
        """This method returns TUser object with specified jid"""
        try:
            return self.session.query(TUser).filter(TUser.jid == jid).one()
        except NoResultFound:
            return False


class TWorktimeManager(object):
    """TWorktime database table manager
    Provides query methods"""
    def __init__(self):
        """TWorktimeManager constructor
        Inits session"""
        self.session = db.getSession()

    def add(self, obj):
        """Proxy method for session.add"""
        self.session.add(obj)

    def flush(self):
        """Proxy method for session.flush"""
        self.session.flush()

    def getActiveSessionForUser(self, user):
        """Returns an active session for specified user"""
        try:
            return self.session.query(TWorktime)\
                    .filter(TWorktime.user == user)\
                    .filter(TWorktime.stop == None).one()
        except NoResultFound:
            return False

    def getTodayWorktimeForUser(self, user):
        """Returns today worktime for speciefed user"""
        try:
            return self.session.query(TWorktime)\
                    .filter(TWorktime.start >= date.today())\
                    .filter(TWorktime.start < date.today() + timedelta(days=1)).all()
        except NoResultFound:
            return False


def initModels():
    """Initialize timebot DB tables and mappers"""
    engine = db.getEngine()
    meta = db.getMeta()
    session = db.getSession()

    tb_user = Table(
            'tb_user', meta,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('company_id', None, ForeignKey('tb_company.id'), nullable=True),
            Column('jid', Unicode(50), unique=True, nullable=False),
            Column('name', Unicode(50)),
            Column('rate', Integer))

    tb_worktime = Table(
            'tb_time', meta,
            Column('id', Integer, primary_key=True),
            Column('user_id', None, ForeignKey('tb_user.id'), nullable=False),
            Column('start', DateTime, default=datetime.now),
            Column('stop', DateTime, nullable=True))

    tb_company = Table(
            'tb_company', meta,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(50), nullable=True))

    meta.create_all()

    mapper(TUser, tb_user, properties=dict(
            worktime=relation(TWorktime),
            company=relation(TCompany)))
    mapper(TWorktime, tb_worktime, properties=dict(
            user=relation(TUser)))
    mapper(TCompany, tb_company, properties=dict(
            users=relation(TUser)))
