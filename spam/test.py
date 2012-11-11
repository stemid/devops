#!/usr/bin/env python

import sys
import pdb
from email.parser import Parser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

email = Parser().parse(sys.stdin)

payloads = email.get_payload()

newMail = MIMEMultipart()
newMail['From'] = 'me@domain.tld'
newMail['Subject'] = 'Some subject'
newMail['To'] = 'someguy@ibm.com'
newMail.preamble = 'You need a MIME reader'

for p in payloads:
    p.add_header('Content-Disposition', 'attachment', filename='att.eml')
    newMail.attach(p)

body = MIMEText('This is some body')
newMail.attach(body)

o = open('testoutput', 'w')
pdb.set_trace()
pdb.run('newBody = newMail.as_string()')
pdb.run('o.write(newMail.as_string())')
o.close()

sys.exit(0)
