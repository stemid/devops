Spam Training for SpamAssassin
================

System setup to receive spam candidates from users into a special mailbox. And then notify admins who can confirm or delete the candidates. Confirmed candidates are placed in a special directory for later sa-learning. 

Please go through settings.py before attempting science. 

HOWTO Sendmail
===========

It's supposed to receive e-mail from an alias in /etc/aliases like this. 

    spamtraining: 	|/etc/smrsh/spamtraining

In sendmail this requires a symlink with the actual program from /etc/smrsh/spamtraining. The program should be owned by the mail user that executes it. 

Has also been tested in postfix where the smrsh linking procedure is not required. 

TODO
====

  * Add logging handler for sending critical errors to admins
  * http://docs.python.org/2/library/logging.handlers.html#logging.handlers.SMTPHandler
  * Investigate the possibility of raising an exception from adminMail()
