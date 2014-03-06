# Example: sudo tail -F /var/log/maillog|grep -E '(stat=|CLEAN|Blocked SPAM)'|colout -T ~/.colout -t maillog
# By Stefan Midjich

def theme():
  bright_black = '#002b36'
  black = '#073642'
  bright_green = '#586e75'
  bright_yellow = '#657b83'
  bright_blue = '#839496'
  bright_cyan = '#93a1a1'
  white = '#eee8d5'
  bright_white = '#fdf6e3'
  yellow = '#b58900'
  orange = '#cb4b16'
  red = '#dc322f'
  magenta = '#d33682'
  violet = '#6c71c4'
  blue = '#268bd2'
  cyan = '#2aa198'
  green = '#859900'

  return [
      [ "(.+) (stat=Sent) (.+)", green ],
      [ "stat=Reject", yellow ],
      [ "stat=queued", red ],
      [ "Blocked SPAM", red ],
      [ "CLEAN", green ]
  ]
