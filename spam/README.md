Spam Training for SpamAssassin
================

This project is not yet finished because other emergencies took my time but it was uploaded to spread a minor tool in the tools dir. 

It's supposed to receive e-mail from an alias in /etc/aliases like this. 

    spamtraining: 	|/etc/smrsh/spamtraining

In sendmail this requires a symlink with the actual program from /etc/smrsh/spamtraining. 

The received e-mails are taken apart for attachments, the first attachment is saved if it's a multipart mail message. An email is sent out to admins who decide if it is spam or ham by replying with a command. 
