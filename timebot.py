# -*- coding: utf-8 -*-

"""Timebot main class definition module"""

__author__ = "Danilenko A."
__email__ = "hdg700@gmail.com"

import defines
import report
import xmpp
import sys
from models import *
from datetime import datetime, time

class Connection(object):
    """Connection class used to communicate with server"""
    def __init__(self, login, password):
        self.password = password
        self.jid = xmpp.protocol.JID(login)
        self.client = xmpp.Client(self.jid.getDomain(), debug=[])

    def connect(self):
        """Connects to server"""
        if not self.client.connect(server=(u'talk.google.com', 5223)):
            sys.stderr.write('Соединение не удалось\n')
            return False

        print u'Соединение прошло успешно'

        if not self.client.auth(self.jid.getNode(), self.password):
            sys.stderr.write('Не удалось авторизоваться\n')
            return False

        print u'Авторизация прошла успешно'

        self.client.sendInitPresence()
        return True

    def getSock(self):
        """Returns Connection socket"""
        return self.client.Connection._sock

    def send(self, jid, msg):
        """Sends message to server"""
        xmpp_msg = xmpp.protocol.Message(to=jid, body=msg, typ='chat')
        self.client.send(xmpp_msg)

    def initHandlers(self, onMessage, onPresence):
        """Init jabber handlers"""
        self.client.RegisterHandler('message', onMessage)
        self.client.RegisterHandler('presence', onPresence)

class Timebot(object):
    """Timebot - jabber-bot main class"""
    def __init__(self, connection):
        """Timebot initialization
        Receives connection-object"""
        self.connection = connection
        self.users = {}
        self.handlers = {}
        self.initHandlers()

    def onPresence(self, con, event):
        """Handles jabber presence event"""
        type = event.getType()
        show = event.getShow()
        jid = event.getFrom()
        mng = TUserManager()

        # subscribe request received
        if type == 'subscribe':
            self.connection.client.send(xmpp.Presence(to=jid, typ='subscribed'))
            self.connection.client.send(xmpp.Presence(to=jid, typ='subscribe'))
            return True

        # subscribed notification received
        if type == 'subscribed':
            jid = jid.getStripped()
            if not mng.hasUser(jid):
                self.connection.send(jid, defines.MSG_SUBSCRIBE[1])
            return True

        # status changes handling

        jid = jid.getStripped()
        # user gone offline
        if type == 'unavailable':
            user = self.getUser(jid)
            if not user:
                return

            # autostop work session
            if datetime.time(datetime.now()) > user.company.end:
                stop_time = self.stopUser(user, False, True)
                if stop_time:
                    self.log(user, defines.DB_LOG_AUTOSTOP, stop_time)
                    self.connection.send(jid, defines.MSG_PRESENCE[u'autostop'])

            self.log(user, defines.DB_LOG_OFFLINE)
            try:
                del self.users[user.jid]
            except KeyError:
                pass
        elif type == None:
            new = False
            try:
                user = self.users[jid]
            except KeyError:
                user = mng.getUserByJid(jid)
                if not user:
                    self.connection.send(jid, defines.MSG_PRESENCE[u'nouser'])
                    return False
                self.users[jid] = user
                new = True

            # new user authorized in jabber
            if new:
                self.log(user, defines.DB_LOG_ONLINE)
            # user changed status
            else:
                if show == 'away':
                    user = self.getUser(jid)
                    self.log(user, defines.DB_LOG_AWAY)
                    if datetime.time(datetime.now()) > user.company.end:
                        stop_time = self.stopUser(user, False, True)
                        if stop_time:
                            self.log(user, defines.DB_LOG_AUTOSTOP, stop_time)
                            self.connection.send(jid, defines.MSG_PRESENCE[u'autostop'])
                    else:
                        self.log(user, defines.DB_LOG_ONLINE)
                else:
                    pass

    def onMessage(self, con, event):
        """Handles jabber message event"""
        type = event.getType()
        jid = event.getFrom().getStripped()
        if not type == 'chat':
            return False

        message = event.getBody()
        if message == None:
            return False

        self.processMessage(jid, message)

    def initHandlers(self):
        """Init jabber handlers and process message functions dict"""
        self.handlers[defines.CMD_REG] = self.onReg
        self.handlers[defines.CMD_START] = self.onStart
        self.handlers[defines.CMD_STOP] = self.onStop
        self.handlers[defines.CMD_TODAY] = self.onToday
        self.handlers[defines.CMD_SUMMARY] = self.onSummary
        self.handlers[defines.CMD_REPORT] = self.onReport
        self.handlers[defines.CMD_CONTINUE] = self.onContinue
        self.handlers[defines.CMD_HELP] = self.onHelp

        self.connection.initHandlers(self.onMessage, self.onPresence)

    def processMessage(self, jid, message):
        """Gets the command and it's parameters from the message and calls corresponding methods"""
        print jid, ':', message
        cmd, sep, message = message.partition(' ')
        cmd = [i[0] for i in defines.commands.items() if cmd in i[1]]
        if cmd:
            try:
                self.handlers[cmd[0]](jid, message)
            except KeyError:
                print u'User', jid, 'asked for an unavailable command with id', cmd[0]

    def getUser(self, jid):
        """Gets user from self.users or from db"""
        try:
            user = self.users[jid]
        except KeyError:
            mng = TUserManager()
            user = mng.getUserByJid(jid)
        return user

    def stopUser(self, user, sendmsg=True, autostop=False):
        """Stops user's active session"""
        time_mng = TWorktimeManager()
        active_session = time_mng.getActiveSessionForUser(user)
        if not active_session:
            if sendmsg: self.connection.send(user.jid, defines.MSG_STOP[u'notstarted'])
            return False

        active_session.stop = datetime.now()
        if autostop:
            active_session.autostoped = True
        time_mng.commit()

        if sendmsg: self.connection.send(user.jid, defines.MSG_STOP[1])

        return active_session.stop

    def onHelp(self, jid, message):
        """Help command handler
        Shows help timp about argument command"""
        pass

    def onReg(self, jid, message):
        """Registration command handler
        Registers new user for timebot"""
        print '--> Reg:', jid, message
        mng = TUserManager()
        if not mng.hasUser(jid):
            user = TUser(jid, message)
            mng.add(user)
            mng.commit()

            self.connection.send(jid, defines.MSG_REG[1])
        else:
            self.connection.send(jid, defines.MSG_REG[0])

    def onStart(self, jid, message):
        """Start command handler
        Starts new working session for registered user"""
        print '--> Start:', jid, message
        user_mng = TUserManager()
        user = self.getUser(jid)
        if not user:
            self.connection.send(jid, defines.MSG_START[u'nouser'])
            return

        time_mng = TWorktimeManager()
        active_session = time_mng.getActiveSessionForUser(user)
        if active_session:
            self.connection.send(jid, defines.MSG_START[u'alreadystarted'])
            return

        work_session = TWorktime(user)
        time_mng.add(work_session)
        time_mng.commit()
        self.connection.send(jid, defines.MSG_START[1])

    def onStop(self, jid, message):
        """Stop command handler
        Stops current user's working session"""
        print '--> Stop:', jid, message
        user_mng = TUserManager()
        user = self.getUser(jid)
        if not user:
            self.connection.send(jid, defines.MSG_STOP[u'nouser'])
            return

        stop_time = self.stopUser(user)

    def onToday(self, jid, message):
        """Today command handler
        Shows for what time user has been working today and his today's salary"""
        print '--> Today:', jid, message
        user_mng = TUserManager()
        time_mng = TWorktimeManager()
        user = self.getUser(jid)
        if not user:
            self.connection.send(jid, defines.MSG_TODAY[u'nouser'])
            return
        if not user.rate:
            self.connection.send(jid, defines.MSG_TODAY[u'norate'])
            return

        reswt = time_mng.getTodayWorktimeForUser(user)
        if not reswt:
            self.connection.send(jid, defines.MSG_TODAY[u'nosessions'])
            return

        hours, minutes, salary = self.getUserSalaryFromWorktime(user, reswt)
        if not salary:
            self.connection.send(jid, defines.MSG_TODAY[u'nosalary'])
            return

        self.connection.send(jid, defines.MSG_TODAY[1].format(hours, minutes, salary))

    def onSummary(self, jid, message):
        """Summary command handler
        Shows user's salary for specified period or current month"""
        print '--> Summary:', jid, message
        user_mng = TUserManager()
        time_mng = TWorktimeManager()
        user = self.getUser(jid)
        if not user:
            self.connection.send(jid, defines.MSG_SUMMARY[u'nouser'])
            return
        if not user.rate:
            self.connection.send(jid, defines.MSG_SUMMARY[u'norate'])
            return

        args = message.split()
        if not args:
            reswt = time_mng.getMonthWorktimeForUser(user)

            hours, minutes, salary = self.getUserSalaryFromWorktime(user, reswt)
            if not salary:
                self.connection.send(jid, defines.MSG_SUMMARY[u'nosalary'])
                return

            self.connection.send(jid, defines.MSG_SUMMARY[u'month'].format(hours, minutes, salary))
        else:
            if len(args) != 2:
                self.connection.send(jid, defines.MSG_SUMMARY[u'invalid_args'])
                return

            try:
                datetime.strptime(args[0], '%y-%m-%d')
                datetime.strptime(args[1], '%y-%m-%d')
            except ValueError:
                self.connection.send(user.jid, defines.MSG_SUMMARY[u'dateformat_error'])
                return

            reswt = time_mng.getPeriodWorktimeForUser(user, *args)

            hours, minutes, salary = self.getUserSalaryFromWorktime(user, reswt)
            if not salary:
                self.connection.send(jid, defines.MSG_SUMMARY[u'nosalary'])
                return

            self.connection.send(jid, defines.MSG_SUMMARY[u'period'].format(hours, minutes, salary))

    def getUserSalaryFromWorktime(self, user, wtlist):
        """Calculates sum of worktime in seconds"""
        sec_sum = sum([(wt.stop - wt.start).seconds if wt.stop != None
                else (datetime.now() - wt.start).seconds for wt in wtlist])

        minutes = sec_sum/60.0
        salary = int(user.rate/60.0 * minutes)

        hours = int(minutes/60)
        minutes = int(minutes%60)

        return hours, minutes, salary

    def getUserDaysSalaryFromWorktime(self, user, wtlist):
        """Calculates sum of worktime for every day in seconds"""
        wtlist = [(wt.start, (wt.stop - wt.start).seconds) if wt.stop != None
                else (wt.start, (datetime.now() - wt.start).seconds) for wt in wtlist]

        if not wtlist:
            raise IndexError()

        def calc(seconds):
            """Calculates hours, minutes and salary from seconds"""
            minutes = seconds/60.0
            salary = int(user.rate/60.0 * minutes)

            hours = int(minutes/60)
            minutes = int(minutes%60)

            return hours, minutes, salary

        data = []
        last_start, last_sum = wtlist[0]
        sec_sum = last_sum
        for i in wtlist[1:]:
            sec_sum += i[1]
            if i[0].day == last_start.day:
                last_sum += i[1]
            else:
                data.append((last_start, calc(last_sum)))
                last_start, last_sum = i

        if data[-1][0].day != last_start.day:
            data.append((last_start, calc(last_sum)))

        return calc(sec_sum), data


    def onContinue(self, jid, message):
        """Cancels autostop session"""
        print '--> Continue:', jid, message
        user = self.getUser(jid)
        if not user:
            self.connection.send(jid, defines.MSG_CONTINUE[u'nouser'])
            return

        time_mng = TWorktimeManager()
        last_session = time_mng.getLastSessionForUser(user)
        if not last_session:
            self.connection.send(jid, defines.MSG_CONTINUE[u'notodaysession'])
            return

        if last_session.stop == None:
            self.connection.send(jid, defines.MSG_CONTINUE[u'activesession'])
            return

        if last_session.autostoped == False:
            self.connection.send(jid, defines.MSG_CONTINUE[u'nocanceledsession'])
            return

        last_session.stop = None
        last_session.autostoped = False
        time_mng.add(last_session)
        time_mng.commit()

        self.connection.send(jid, defines.MSG_CONTINUE[1])

        self.log(user, defines.DB_LOG_CONTINUE)

    def onReport(self, jid, message):
        """Report command handler
        Calculates all users salary for period"""
        print '--> Report:', jid, message
        user_mng = TUserManager()
        time_mng = TWorktimeManager()
        user = self.getUser(jid)
        if not user:
            self.connection.send(jid, defines.MSG_REPORT[u'nouser'])
            return

        if not user.isAdmin():
            return

        args = message.split()
        report.ReportThread(self.connection, user, *args[:2]).start()

    def doReport(self, user, begin=False, end=False):
        """Get summary data for report"""
        prevMonth = False
        if begin in ['prev', '-1']:
            prevMonth = True

        if not prevMonth and begin and end:
            try:
                datetime.strptime(begin, '%y-%m-%d')
                datetime.strptime(end, '%y-%m-%d')
            except ValueError:
                self.connection.send(user.jid, defines.MSG_REPORT[u'dateformat_error'])
                return

        self.connection.send(user.jid, defines.MSG_REPORT[u'accepted'])
        time_mng = TWorktimeManager()
        company = user.company
        data_sum = []
        data_sum.append((u'Имя', u'Ставка', u'Время', u'Зарплата'))

        users_data_daily = {}
        for u in company.users:
            if begin and end:
                reswt = time_mng.getPeriodWorktimeForUser(u, begin, end)
            else:
                reswt = time_mng.getMonthWorktimeForUser(u, prevMonth)
            #hours, minutes, salary = self.getUserDaysSalaryFromWorktime(u, reswt)
            try:
                sum_salary, daily_salary = self.getUserDaysSalaryFromWorktime(u, reswt)
            except IndexError:
                continue

            row = [u.name, u.rate,
                    u'{0} ч {1} мин'.format(sum_salary[0],
                            sum_salary[1] if sum_salary[1] >= 10 else '0' + str(sum_salary[1])).encode('utf-8'),
                    u'{0} руб'.format(sum_salary[2])]
            data_sum.append(row)

            data_daily = []
            data_daily.append((u'Дата', u'Время', u'Зарплата'));

            for day in daily_salary:
                row = [day[0].strftime('%d / %m / %Y'), u'{0} ч {1} мин'.format(day[1][0],
                        day[1][1]),
                        u'{0} руб'.format(day[1][2])]
                data_daily.append(row)
            users_data_daily[u.name] = data_daily

        now = datetime.now()
        filename_report = u'pdf/report_{0}.pdf'.format(now.date())
        self.generatePDF(filename_report, data_sum, begin, end)
        link = self.uploadReport(filename_report, u'Report ({0} {1})'.format(now.date(), now.time()), user)
        if link:
            self.connection.send(user.jid, defines.MSG_REPORT[u'report'] + u'\n' + link)
        else:
            self.connection.send(user.jid, defines.MSG_REPORT[u'request_error'])

        filename_full_report = u'pdf/full_report_{0}.pdf'.format(now.date())
        self.generatePDF(filename_full_report, users_data_daily, begin, end, full_report=True)
        link = self.uploadReport(filename_full_report, u'Full report ({0} {1})'.format(now.date(), now.time()), user)
        if link:
            self.connection.send(user.jid, defines.MSG_REPORT[u'full_report'] + u'\n' + link)
        else:
            self.connection.send(user.jid, defines.MSG_REPORT[u'request_error'])


    def  generatePDF(self, filename, data, begin=False, end=False, full_report=False):
        """Generates a pdf-report"""
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.platypus.tables import Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
        from reportlab.lib.colors import Color

        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        pdfmetrics.registerFont(TTFont(u'Verdana', u'./verdana.ttf'))
        pdfmetrics.registerFont(TTFont(u'VerdanaB', u'./verdana-bold.ttf'))

        doc = SimpleDocTemplate(filename, topMargin=30)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name=u'Rus', fontName=u'Verdana', fontSize=12,
                leading=35, leftIndent=0, alignment=TA_CENTER, firstLineIndent=0))

        content = []
        if begin and end:
            header_str = u'Отчет по зарплатам за период с {0} по {1}'.format(begin, end)
        else:
            header_str = u'Отчет по зарплатам за месяц'

        if not full_report:
            header = Paragraph(header_str, styles[u'Rus'])
            content.append(header)

        if full_report:
            for username, tdata in data.items():
                tb = Table(tdata, [250, 130, 130], repeatRows=True)
                tb.setStyle(TableStyle([(u'FONT', (0, 0), (-1, -1), u'Verdana'),
                        (u'INNERGRID', (0, 0), (-1, -1), 0.20, Color(0.5, 0.5, 0.5)),
                        (u'BACKGROUND', (0, 0), (-1, 0), Color(0.7647, 0.8235, 0.8784)),
                        (u'ROWBACKGROUNDS', (0, 1), (-1, -1), (Color(0.9411, 0.9686, 1.0), Color(1, 1, 1))),
                        (u'BOX', (0, 0), (-1, -1), 0.20, Color(0.1, 0.1, 0.1))]))

                content.append(Paragraph(username, styles[u'Rus']))
                content.append(tb)
                content.append(PageBreak())

        else:
            tb = Table(data, [250, 60, 130, 130], repeatRows=True)
            tb.setStyle(TableStyle([(u'FONT', (0, 0), (-1, -1), u'Verdana'),
                    (u'INNERGRID', (0, 0), (-1, -1), 0.20, Color(0.5, 0.5, 0.5)),
                    (u'BACKGROUND', (0, 0), (-1, 0), Color(0.7647, 0.8235, 0.8784)),
                    (u'ROWBACKGROUNDS', (0, 1), (-1, -1), (Color(0.9411, 0.9686, 1.0), Color(1, 1, 1))),
                    (u'BOX', (0, 0), (-1, -1), 0.20, Color(0.1, 0.1, 0.1))]))

            content.append(tb)

        def onPage(canvas, doc):
            canvas.setFont(u'Verdana', 8)
            canvas.drawString(5, 5, u'(C) Generated by gTimebot - ' + header_str)

        doc.build(content, onFirstPage=onPage, onLaterPages=onPage)

    def uploadReport(self, filename, filetitle, user):
        """Uploads a pdf-report to google-docs service"""
        import gdata.docs.data
        import gdata.docs.client

        try:
            client = gdata.docs.client.DocsClient(source=config.CONF_APP_CODE)
            client.ssl = True
            client.ClientLogin(config.CONF_GMAIL_LOGIN,
                    config.CONF_GMAIL_PASS, source=config.CONF_APP_CODE)

            entry = client.Upload(filename, filetitle, content_type=u'application/pdf')

            scope = gdata.acl.data.AclScope(value=user.jid, type=u'user')
            role = gdata.acl.data.AclRole(value=u'reader')
            acl = gdata.docs.data.Acl(scope=scope, role=role)

            client.Post(acl, entry.GetAclFeedLink().href)
        except gdata.client.RequestError:
            return False

        return entry.GetAlternateLink().href

    def log(self, user, event, time=False):
        """Logs timebot events into database"""
        if not time:
            time = datetime.now()
        log_mng = TLogManager()
        log_event = TLog(user, event, time)
        log_mng.add(log_event)
        log_mng.commit()
