#These are generally useful functions to be called across the scraper and dev files.
#Author: Peter Ball

import datetime
import requests
import time
import numpy as np

#check if the datestring in a range
def datestring_in_range(datestring, formatstr, start, end):
	d = datetime.datetime.strptime(datestring, formatstr).date()
	return datetime.datetime.strptime(start, '%Y-%m-%d').date() <= d <= datetime.datetime.strptime(end, '%Y-%m-%d').date()



def request_wrapper(url, req_delay):
	response = requests.get(url)
	#humanizing with gaussian noise
	sleep_time = req_delay + np.random.normal(0, 0.1)
	print("Sleeping {:.2f}".format(sleep_time))
	time.sleep(sleep_time)

	return response