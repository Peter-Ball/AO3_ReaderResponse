#These are generally useful functions to be called across the scraper and dev files.
#Author: Peter Ball

import datetime

#check if the datestring in a range
def datestring_in_range(datestring, formatstr, start, end):
	d = datetime.datetime.strptime(datestring, formatstr).date()
	return datetime.date.fromisoformat(start) <= d <= datetime.date.fromisoformat(end)
