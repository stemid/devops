# coding: utf-8
import web
import json

# Initialize settings class
from settings import Settings
s = Settings()
settings = s.config

urls = (
    '/notify/by/(.+)', 'Notify',
)

app = web.application(urls, globals())

class Notify:
    def _notify_by_email(self, rcpt, subject, message):
        from smtplib import SMTP

        msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (
            settings['email_from'],
            rcpt,
            subject,
            message
        ))

        server = SMTP(settings['email_smarthost'])
        server.sendmail(
            settings['email_from'],
            rcpt,
            msg
        )

    def _notify_by_sms(self, pager, notification, hostname, message):
        import sh

        notify_by_sms = sh.Command(settings['sms_command'])
        print type(notify_by_sms)
        notify_by_sms(pager, notification, hostname, _in=message)

    def _notify_by_oplog(self, **kw):
        import psycopg2

        fieldnames = [
            'customer',
            'eventtype',
            'regtime',
            'subject',
            'message',
        ]

        conn = psycopg2.connect(
            host = s.opglog_dbhost,
            database = s.oplog_dbname,
            user = s.opglog_dbuser,
            password = s.oplog_dbpass
        )
        cur = conn.cursor()

        cur.execute(
            '''INSERT INTO Event (
                customer, eventtype, regtime, subject, message
            ) VALUES (
                %s, %s, %s, %s, %s
            )'''
        , (
            kw.get('customer'),
            kw.get('eventtype'),
            kw.get('regtime'),
            kw.get('subject'),
            kw.get('message')
        ))
        conn.commit()
        cur.close()
        conn.close()

    def GET(self, command):
        from datetime import datetime

        if command not in settings['notification_commands']:
            raise web.notfound()

        if command == 'email':
            query = web.input(
                recipient = None,
                subject = None,
                msg = ''
            )

            if not query.recipient or not query.subject:
                print json.dumps({
                    'recipient': query.recipient,
                    'subject': query.subject,
                })
                raise web.internalerror()

            try:
                self._notify_by_email(
                    query.recipient, 
                    query.subject, query.
                    msg
                )
            except Exception, e:
                print json.dumps({
                    'error': str(e),
                })
                raise web.internalerror()
            finally:
                return web.ok()

        if command == 'sms':
            query = web.input(
                contactpager = None,
                notification = None,
                hostname = '',
                msg = ''
            )

            if not query.contactpager or not query.notification:
                print json.dumps({
                    'contactpager': query.contactpager, 
                    'notification': query.notification,
                })
                raise web.internalerror()

            try:
                self._notify_by_sms(
                    query.contactpager, 
                    query.notification,
                    query.hostname,
                    query.msg
                )
            except Exception, e:
                print json.dumps({
                    'error': str(e),
                })
                raise web.internalerror()
            finally:
                return web.ok()

        if command == 'oplog':
            query = web.input(
                customer = '(okänd)',
                event = 'Host Unknown',
                regtime = datetime.now(),
                subject = None,
                msg = None 
            )

            if not query.subject or not query.msg:
                raise web.badrequest()

            try:
                self._notify_by_oplog(
                    query.customer,
                    query.event,
                    query.regtime,
                    query.subject,
                    query.msg
                )
            except Exception, e:
                raise web.internalerror()
            finally:
                return web.ok()

if __name__ == '__main__':
    app.run()

if __name__.startswith('_mod_wsgi_'):
    application = app.wsgifunc()
