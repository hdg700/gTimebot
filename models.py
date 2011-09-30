#!/usr/bin/python2.6
# -*- coding: utf-8 -*-

"""
Timebot models definition module
"""

__author__ = "Danilenko A."
__email__ = "hdg700@gmail.com"

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import *
from datetime import datetime, time, date, timedelta
import calendar
import config
import defines

engine = create_engine(config.CONF_DB_DSN)
engine.execute('SET NAMES utf8')
Session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base(bind=engine)

class TUser(Base):
    """Timebot user model"""
    __tablename__ = 'tb_user'
    __table_args__ = {'mysql_engine':'InnoDB'}

    id = Column(Integer, primary_key=True)
    jid = Column(Unicode(50), unique=True, nullable=False)
    name = Column(Unicode(50))
    rate = Column(Integer)
    company_id = Column(Integer, ForeignKey('tb_company.id'))
    is_admin = Column(Boolean)

    worktime = relation('TWorktime', backref='user')
    company = relation('TCompany', backref='users')

    def __init__(self, jid, name, rate=None):
        """Timebot user class initialization"""
        self.jid = jid
        self.name = name
        self.is_admin = False

        if rate:
            self.rate = rate

    def __repr__(self):
        return u'<TUser: {0} ({1})>'.format(self.name, self.jid)

    def isAdmin(self):
        """returns True, if current user is admin"""
        return self.is_admin

    def stop(self, nomsg=False):
        """Ends user's active session"""
        time_mng = TWorktimeManager()
        active_session = time_mng.getActiveSessionForUser(self)
        if not active_session:
            if not nomsg: self.connection.send(self.jid, defines.MSG_STOP[u'notstarted'])
            return

        active_session.stop = datetime.now()
        time_mng.commit()
        if not nomsg: self.connection.send(self.jid, defines.MSG_STOP[1])

class TLog(Base):
    """Timebot log model"""
    __tablename__ = 'tb_log'
    __table_args__ = {'mysql_engine':'InnoDB'}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('tb_user.id'))
    event = Column(Unicode(20), nullable=False)
    time = Column(DateTime, default=datetime.now)

    user = relation('TUser', backref='events')

    def __init__(self, user, event, time):
        """Timebot log model class initialization"""
        self.user = user
        self.event = event
        self.time = time

    def __repr__(self):
        return u'<TLog({3}): {0} ({1}): {2}>'.format(self.user.jid, self.event, self.time, self.id)

class TWorktime(Base):
    """Timebot worktime model"""
    __tablename__ = 'tb_time'
    __table_args__ = {'mysql_engine':'InnoDB'}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('tb_user.id'))
    start = Column(DateTime, default=datetime.now)
    stop = Column(DateTime, nullable=True)
    autostoped = Column(Boolean, default=False)

    def __init__(self, user):
        """Timebot worktime class initialization"""
        self.user = user

    def __repr__(self):
        return u'<TWorktime: {0} ({1})>'.format(self.id, self.start)

def defaultBeginTime():
    return datetime.time(10, 0)

def defaultEndTime():
    return datetime.time(18, 0)

class TCompany(Base):
    """Timebot company model"""
    __tablename__ = 'tb_company'
    __table_args__ = {'mysql_engine':'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(50), nullable=True)
    begin = Column(Time, default=defaultBeginTime)
    end = Column(Time, default=defaultEndTime)

    def __init__(self, name):
        """Timebot company class initialization"""
        self.name = name

    def __repr__(self):
        return '<TCompany: {0} ({1})>'.format(self.id, self.name)


class TUserManager(object):
    """TUser database table manager
    Provides query methods"""
    def __init__(self):
        """TUserManager constructor
        Inits session"""
        self.session = Session()

    def add(self, obj):
        """Proxy method for session.add"""
        self.session.add(obj)

    def commit(self):
        """Proxy method for session.commit"""
        self.session.commit()

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


class TLogManager(object):
    """TLog database table manager"""
    def __init__(self):
        """TLogManager constructor
        Inits session"""
        self.session = Session()

    def add(self, obj):
        """Proxy method for session.add"""
        self.session.add(obj)

    def commit(self):
        """Proxy method for session.commit"""
        self.session.commit()

    def getAutoCanceledSession(self, user):
        """Returns canceled session"""
        try:
            return self.session.query(TWorktime)\
                    .filter(TWorktime.user == user)\
                    .filter(TWorktime.stop == TLog.time)\
                    .filter(TLog.user == user)\
                    .filter(TLog.event == defines.DB_LOG_AUTOSTOP)\
                    .filter(TLog.time >= date.today())\
                    .order_by(desc(TLog.time))\
                    .limit(1).one()
        except NoResultFound:
            return False


class TWorktimeManager(object):
    """TWorktime database table manager
    Provides query methods"""
    def __init__(self):
        """TWorktimeManager constructor
        Inits session"""
        self.session = Session()

    def add(self, obj):
        """Proxy method for session.add"""
        self.session.add(obj)

    def commit(self):
        """Proxy method for session.commit"""
        self.session.commit()

    def getLastSessionForUser(self, user):
        """Returns last session for specified user"""
        try:
            return self.session.query(TWorktime)\
                    .filter(TWorktime.user == user)\
                    .filter(TWorktime.start >= date.today())\
                    .order_by(desc(TWorktime.id))\
                    .limit(1).one()
        except NoResultFound:
            return False

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
                    .filter(TWorktime.user == user)\
                    .filter(TWorktime.start >= date.today())\
                    .filter(TWorktime.start < date.today() + timedelta(days=1)).all()
        except NoResultFound:
            return False

    def getMonthWorktimeForUser(self, user, prevMonth=False):
        """Returns month worktime for speciefed user"""
        try:
            today = datetime.now()

            if prevMonth:
                today = today - timedelta(days=today.day+1)

            first_day = today.replace(day=1, hour=0, minute=0, second=0)
            last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1], hour=23, minute=59, second=59)

            return self.session.query(TWorktime)\
                    .filter(TWorktime.user == user)\
                    .filter(TWorktime.start >= first_day)\
                    .filter(TWorktime.start <= last_day)\
                    .order_by(asc(TWorktime.start))\
                    .all()
        except NoResultFound:
            return False

    def getPeriodWorktimeForUser(self, user, begin, end):
        """Returns period worktime for speciefed user"""
        try:
            return self.session.query(TWorktime)\
                    .filter(TWorktime.user == user)\
                    .filter(TWorktime.start >= begin)\
                    .filter(TWorktime.start < end).all()
        except NoResultFound:
            return False


def initModels():
    """Initialize timebot DB tables and mappers"""
    Base.metadata.create_all()
