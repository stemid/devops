Spam Training for SpamAssassin
================

It's supposed to receive e-mail from an alias in /etc/aliases like this. 

    spamtraining: 	|/etc/smrsh/spamtraining

In sendmail this requires a symlink with the actual program from /etc/smrsh/spamtraining. The program should be owned by the mail user that executes it. 

Has also been tested in postfix where the smrsh linking procedure is not required. 

TODO
====

  * Add logging handler for sending critical errors to admins
