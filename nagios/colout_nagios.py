# Solarized colout theme for nagios logs
#  * Install colout from pypi or https://github.com/nojhan/colout
#  * mkdir ~/.colout
#  * Install this file into ~/.colout/colout_nagios.py
#  * tail -0f /var/log/nagios3/nagios.log | perl -pi -e 's/(\d+)/localtime($1)/e' | colout -T ~/.colout -t nagios
#
# By Stefan Midjich

def theme():
    return [
        [ "(SERVICE ALERT\:) (.+)(;OK;HARD;)(.+)$", "#859900" ],
        [ "(SERVICE ALERT\:) (.+)(;OK;SOFT;)(.+)$", "#2aa198" ],
        [ "(SERVICE ALERT\:) (.+;)(UNKNOWN|CRITICAL)(;HARD;)(.+)$", "#dc322f" ],
        [ "(SERVICE ALERT\:) (.+;)(UNKNOWN|CRITICAL)(;SOFT;)(.+)$", "#b58900" ],
        [ "(SERVICE ALERT\:) (.+)(;WARNING;HARD;)(.+)$", "#dc322f" ],
        [ "(SERVICE ALERT\:) (.+)(;WARNING;SOFT;)(.+)$", "#b58900" ],
        [ "(HOST ALERT\:) (.+)(;UP;HARD;)(.+)$", "#859900" ],
        [ "(HOST ALERT\:) (.+)(;UP;SOFT;)(.+)$", "#2aa198" ],
        [ "(HOST ALERT\:) (.+)(;DOWN;HARD;)(.+)$", "#dc322f" ],
        [ "(HOST ALERT\:) (.+)(;DOWN;SOFT;)(.+)$", "#b58900" ],
        [ "(EXTERNAL COMMAND\:) (.+)$", "#e4e4e4", "bold" ],
    ]
