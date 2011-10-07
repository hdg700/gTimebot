# -*- coding: utf-8 -*-

"""Report thread module"""

__author__ = "Danilenko A."
__email__ = "hdg700@gmail.com"

from models import *
from datetime import datetime, time
import threading

class ReportThread(threading.Thread):
    def __init__(self, func, *args):
        self.func = func
        self.args = args
        threading.Thread.__init__(self)

    def run(self):
        self.func(*self.args)

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

