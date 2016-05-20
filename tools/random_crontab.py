#!/usr/bin/env python
# Generate random crontab lines of a specified job.
#
# by Stefan Midjich <swehack@gmail.com> - 2016

from __future__ import print_function

from sys import stdout, stderr
from random import randint
from argparse import ArgumentParser, FileType, ArgumentDefaultsHelpFormatter

parser = ArgumentParser(
    description='Generate random crontab lines for a specified job. ',
    epilog=('Example: random_crontab.py --hour R --minute R "bash test"'
            ' --count 5'),
    formatter_class=ArgumentDefaultsHelpFormatter
)

parser.add_argument(
    '-v', '--verbose',
    action='count',
    help='Verbose output, use more v\'s to increase level'
)

parser.add_argument(
    'job',
    help='Cron job, follows same rules as specified in crontab(5)'
)

parser.add_argument(
    '--outputfile', '-o',
    default=stdout,
    type=FileType('w'),
    help='Output file for cron data'
)

parser.add_argument(
    '--count',
    type=int,
    help='Number of jobs to generate, random if not specified'
)

parser.add_argument(
    '--max-count',
    default=50,
    type=int,
    help='Maximum number of cronjobs to generate randomly'
)

parser.add_argument(
    '--user',
    help='Include a user field with this user'
)

parser.add_argument(
    '--minute',
    default='*',
    help='Minute field, specify R for random value'
)

parser.add_argument(
    '--hour',
    default='*',
    help='Hour field, specify R for random value'
)

parser.add_argument(
    '--day',
    default='*',
    help='Day of month field, specify R for random value'
)

parser.add_argument(
    '--month',
    default='*',
    help='Month field, specify R for random value'
)

parser.add_argument(
    '--weekday',
    default='*',
    help='Day of week field, specify R for random value'
)


def make_cronjob(minute, hour, day, month, weekday, user, job):
    if not minute:
        minute = randint(0, 59)
    if not hour:
        hour = randint(0, 23)
    if not day:
        day = randint(1, 31)
    if not month:
        month = randint(1, 12)
    if not weekday:
        weekday = randint(0, 7)

    if not user:
        user = ''

    cronjob = '{minute}\t{hour}\t{day}\t{month}\t{weekday}\t{user}\t{job}'.format(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        weekday=weekday,
        user=user,
        job=job
    )

    return cronjob


def write_crontab(output, data):
    print(data, file=output)


def main():
    args = parser.parse_args()

    minute = args.minute
    hour = args.hour
    day = args.day
    month = args.month
    weekday = args.weekday

    # Check for any r/R's in cron field arguments and ensure random values
    # are used for them.
    if minute.upper().startswith('R'):
        minute = None
    if hour.upper().startswith('R'):
        hour = None
    if day.upper().startswith('R'):
        day = None
    if month.upper().startswith('R'):
        month = None
    if weekday.upper().startswith('R'):
        weekday = None

    if args.count:
        num_cronjobs = args.count
    else:
        num_cronjobs = randint(1, args.max_count)

    for job in range(1, num_cronjobs):
        job_data = make_cronjob(
            minute,
            hour,
            day,
            month,
            weekday,
            args.user,
            args.job
        )

        write_crontab(args.outputfile, job_data)


if __name__ == '__main__':
    main()
