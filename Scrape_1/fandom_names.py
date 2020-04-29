import requests, re, bs4

import os
import sys
import traceback

from collections import Counter

import pickle

import urllib.parse

urls =  ["https://archiveofourown.org/media/Anime%20*a*%20Manga/fandoms",
		"https://archiveofourown.org/media/Books%20*a*%20Literature/fandoms",
		"https://archiveofourown.org/media/Cartoons%20*a*%20Comics%20*a*%20Graphic%20Novels/fandoms",
		"https://archiveofourown.org/media/Celebrities%20*a*%20Real%20People/fandoms",
		"https://archiveofourown.org/media/Movies/fandoms",
		"https://archiveofourown.org/media/Music%20*a*%20Bands/fandoms",
		"https://archiveofourown.org/media/Other%20Media/fandoms",
		"https://archiveofourown.org/media/Theater/fandoms",
		"https://archiveofourown.org/media/TV%20Shows/fandoms",
		"https://archiveofourown.org/media/Video%20Games/fandoms"]

count = 1
for url in urls:
	print('getting {}'.format('url'))
	response = requests.get(url)
	html = response.content
	print('Response gotten.')

	soup = bs4.BeautifulSoup(html, features = 'lxml')

	fandoms = {}

	print('getting fandoms')
	for character_box in soup.find_all('ul', attrs={'class': 'tags index group'}):
		for fandom in character_box.find_all('li'):
			fanstr = fandom.find('a').text
			fandom.a.decompose()
			fanstr = urllib.parse.quote(fanstr)
			fandoms[fanstr] = int(re.search(r"\d+", fandom.text).group(0))

	final_fandoms = {k:v for k, v in fandoms.items() if v >= 20}
	need_sum = {k:v for k, v in fandoms.items() if v < 20}

	print('Found {} fandoms above 20'.format(len(final_fandoms)))
	print('Merging {} fandoms'.format(len(need_sum)))
	#combine small fandoms to reduce searches
	all_ns_keys = list(need_sum.keys())

	integrated = {k:v for k, v in zip(all_ns_keys, [False for key in all_ns_keys])}
	to_go = len(all_ns_keys)
	for key in all_ns_keys:
		print('Merging to {}'.format(key))
		if integrated[key]:
			continue
		else:
			curr_vl = need_sum[key]
			curr_ky = key
			integrated[key] = True
			to_go -= 1

		for addit_key in all_ns_keys:
			if curr_vl > 20 or to_go < 0:
				break
			if integrated[addit_key]:
				continue

			if need_sum[addit_key] + curr_vl <= 20:
				curr_ky = curr_ky + "%2C" + addit_key
				curr_vl += need_sum[addit_key]
				integrated[addit_key] = True
				to_go -= 1

		final_fandoms[curr_ky] = curr_vl


	final_fandoms = Counter(final_fandoms)

	with open('./outputs/fandom_lists/{}.pkl'.format(count), 'wb') as fp:
		pickle.dump(final_fandoms, fp) 

	count += 1