# -*- coding: utf-8 -*-

"""Report thread module"""

__author__ = "Danilenko A."
__email__ = "hdg700@gmail.com"

from models import *
from datetime import datetime, time
import threading

class ReportThread(threading.Thread):
    def __init__(self, connection, user, *args):
        self.user = user
        self.connection = connection
        self.args = args
        threading.Thread.__init__(self)

        print args

    def run(self):
        self.doReport(self.user, *self.args)

    def getDaysSalaryFromWorktime(self, rate, wtlist):
        """Calculates sum of worktime for every day in seconds"""
        wtlist = [(wt.start, (wt.stop - wt.start).seconds) if wt.stop != None
                else (wt.start, (datetime.now() - wt.start).seconds) for wt in wtlist]

        if not wtlist:
            raise IndexError()

        def calc(seconds):
            """Calculates hours, minutes and salary from seconds"""
            minutes = seconds/60.0
            salary = int(rate/60.0 * minutes)

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

    def doReport(self, user, begin=False, end=False):
        """Get summary data for report"""
        prevMonth = False
        if begin in ['last', 'prev', '-1']:
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
                sum_salary, daily_salary = self.getDaysSalaryFromWorktime(u.rate, reswt)
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

#    def uploadReport(self, filename, filetitle, user):
#        """Uploads a pdf-report to google-docs service"""
#        import gdata.docs.data
#        import gdata.docs.client
#        import syslog
#
#        try:
#            client = gdata.docs.client.DocsClient(source=config.CONF_APP_CODE)
#            client.ssl = True
#            client.ClientLogin(config.CONF_GMAIL_LOGIN,
#                    config.CONF_GMAIL_PASS, source=config.CONF_APP_CODE)
#
#            entry = client.Upload(filename, filetitle, content_type=u'application/pdf')
#
#            scope = gdata.acl.data.AclScope(value=user.jid, type=u'user')
#            role = gdata.acl.data.AclRole(value=u'reader')
#            acl = gdata.docs.data.Acl(scope=scope, role=role)
#
#            client.Post(acl, entry.GetAclFeedLink().href)
#        except gdata.client.RequestError as e:
#            syslog.syslog(str(e))
#            return False
#        except Exception as e:
#            syslog.syslog(str(e))
#            return False
#
#        return entry.GetAlternateLink().href

    def uploadReport(self, filename, filetitle, user):
        """Uploads a pdf-report to google-docs service"""
        import os
        import atom.data
        import gdata.docs.data
        import gdata.docs.client
        import gdata.acl.data

        try:
            client = gdata.docs.client.DocsClient(source=config.CONF_APP_CODE)
            client.ssl = True
            client.ClientLogin(config.CONF_GMAIL_LOGIN,
                    config.CONF_GMAIL_PASS, source=config.CONF_APP_CODE)

            f = open(filename)
            fsize = os.path.getsize(f.name)

            uploader = gdata.client.ResumableUploader(
                    client, f, 'application/pdf', fsize, chunk_size=10485760, desired_class=gdata.data.GDEntry)

            entry = gdata.data.GDEntry(title=atom.data.Title(text=filetitle))
            entry = uploader.UploadFile('/feeds/upload/create-session/default/private/full', entry=entry)

            #scope = gdata.acl.data.AclScope(value=user.jid, type=u'user')
            #role = gdata.acl.data.AclRole(value=u'reader')
            #acl = gdata.docs.DocumentListAclEntry(scope=scope, role=role)

            #print entry.get_acl_link()
            #print entry.get_feed_link()
            #print entry.get_post_link()

            ##client.Post(acl, entry.GetAclFeedLink().href)
            #client.Post(acl, entry.get_acl_link().href)
        except gdata.client.RequestError as e:
            print e
            return False

        return entry.GetAlternateLink().href

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
