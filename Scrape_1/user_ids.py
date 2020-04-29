import requests, re, bs4

import os, sys, traceback
from datetime import datetime

import time

import pickle
import json

_URL_TEMPLATE = "https://archiveofourown.org/people/search?commit=Search+People&page={0}&people_search%5Bfandom%5D={1}&people_search%5Bname%5D=&people_search%5Bquery%5D="

class ScraperPage(object):
    def __init__(self, url=None, search_type='work'):

        response = requests.get(url)
        self.html = response.content

        if search_type == 'work':
            at_cls = 'work blurb group'
        if search_type == 'user':
            at_cls = 'user pseud picture blurb group'

        self.users = {}

        self.soup = bs4.BeautifulSoup(self.html, features='lxml')
        for story in self.soup.find_all('li', attrs={'class': at_cls}):
            user_url = story.find('h4').find('a')['href'].split('pseuds')[0]
            user_txt = story.find('h5').text
            try:
                user_works = int(re.search('\d+', re.search(r'\d+ works', user_txt).group(0)).group(0))
            except AttributeError:
                user_works = 0

            try:
                user_bkmrks = int(re.search('\d+', re.search(r'\d+ bookmarks', user_txt).group(0)).group(0))
            except AttributeError:
                user_bkmrks = 0

            self.users[user_url] = {'num_works': user_works, 'num_bookmarks': user_bkmrks}




if __name__ == "__main__":
    error_file = open("outputs/error_file.txt", 'w')

    try:
        with open("outputs/users.json") as fp:
            users_sofar = json.load(fp)
    except FileNotFoundError:
        users_sofar = {}

    totaltime = 0
    total_sleep = 0
    page_count = 1

    try:
        with open("outputs/fandom_lists/checkpoint.json") as fp:
            checkpoint = json.load(fp)
    except FileNotFoundError:
        checkpoint = {'strt_idx': 0, 'fndm_idx': 1, 'fndms': {}}
    try:
        for fandom_file in range(checkpoint['fndm_idx'],11):

            checkpoint['fndm_idx'] = fandom_file

            with open("fandom_lists/" + str(fandom_file) + '.pkl', 'rb') as fp:
                fandoms = pickle.load(fp)

            fandoms = list(fandoms.keys())

            if checkpoint['strt_idx'] != fandom_file:
                checkpoint['fndms'].update({k:False for k in fandoms})

            for fandom_idx in range(len(fandoms)):
                sleep_time = 60
                fandom = fandoms[fandom_idx]
                #Skip this fandom if we've already scraped it
                if checkpoint['fndms'][fandom]:
                    continue

                print(fandom)
                for i in range(5):
                    try:
                        front_page = ScraperPage(url=_URL_TEMPLATE.format(1, fandom), search_type='user')
                        break
                    except requests.exceptions.Timeout as errt:
                            print(errt)
                            print('Page timeout. Sleeping %d...' % sleep_time)
                            time.sleep(sleep_time)
                            total_sleep += sleep_time
                            sleep_time += 10
                    except requests.exceptions.ConnectionError as errc:
                        print(errc)
                        print("ConnectionError. Sleeping %d..." % sleep_time)
                        time.sleep(sleep_time)
                        total_sleep += sleep_time
                        sleep_time += 10
                else:
                    sleep_time = 10
                    print("fandom {} skipped".format(fandom))
                    continue

                try:
                    navs = front_page.soup.find(title='pagination').find_all('li')
                except AttributeError:
                    navs = []

                if(len(navs) > 0):
                    page_num = int(navs[-2].get_text())
                #if there is only one page, skip the loop.
                else:
                    start = time.time()
                    url = _URL_TEMPLATE.format(1, fandom)
                    try:
                        page = ScraperPage(url, search_type = 'user')
                    except KeyboardInterrupt:
                        error_file.write("fandom file was %d" % fandom_file)
                        error_file.write("fandom idx was %d" % fandom_idx)
                        error_file.close()
                        with open("outputs/user_urls.txt", 'w') as fp:
                            for url in users_sofar:
                                fp.write(url + '\n')
                        with open("fandom_lists/checkpoint.json", "w") as fp:
                            checkpoint['strt_idx'] = checkpoint['fndm_idx']
                            json.dump(checkpoint, fp)

                        print("Looks like you are leaving, let me prep some final data...")
                        print("Total time was %d" % totaltime)
                        print("fandom file was %d" % fandom_file)
                        print("fandom idx was %d" % fandom_idx)
                        print("Page Number was %d" % pg)
                        print("Averate tpp was %d" % (totaltime/page_count))
                        print("Time sleeping: %d" % total_sleep)
                        print("Goodbye!")
                        sys.exit(1)
                    except requests.exceptions.Timeout as errt:
                        print(errt)
                        print('Page timeout. Sleeping %d...' % sleep_time)
                        time.sleep(sleep_time)
                        total_sleep += sleep_time
                        sleep_time += 10
                    except requests.exceptions.ConnectionError as errc:
                        print(errc)
                        print("ConnectionError. Sleeping %d..." % sleep_time)
                        time.sleep(sleep_time)
                        total_sleep += sleep_time
                        sleep_time += 10
                    end = time.time()
                    totaltime += end-start
                    page_count += 1
                    users_sofar.update(page.users)
                    checkpoint['fndms'][fandom] = True
                    continue


                print(page_num)
                for pg in range(1,page_num):
                    start = time.time()
                    url = _URL_TEMPLATE.format(pg, fandom)
                    for i in range(5):
                        try:
                            page = ScraperPage(url, search_type = 'user')
                            break
                        except KeyboardInterrupt:
                            error_file.write("fandom file was %d" % fandom_file)
                            error_file.write("fandom idx was %d" % fandom_idx)
                            error_file.close()
                            with open("outputs/user_urls.txt", 'w') as fp:
                                for url in users_sofar:
                                    fp.write(url + '\n')
                            with open("fandom_lists/checkpoint.json", "w") as fp:
                                checkpoint['strt_idx'] = checkpoint['fndm_idx']
                                json.dump(checkpoint, fp)

                            print("Looks like you are leaving, let me prep some final data...")
                            print("Total time was %d" % totaltime)
                            print("fandom file was %d" % fandom_file)
                            print("fandom idx was %d" % fandom_idx)
                            print("Page Number was %d" % pg)
                            print("Averate tpp was %d" % (totaltime/page_count))
                            print("Time sleeping: %d" % total_sleep)
                            print("Goodbye!")
                            sys.exit(1)
                        except requests.exceptions.Timeout as errt:
                            print(errt)
                            print('Page timeout. Sleeping %d...' % sleep_time)
                            time.sleep(sleep_time)
                            total_sleep += sleep_time
                            sleep_time += 10
                        except requests.exceptions.ConnectionError as errc:
                            print(errc)
                            print("ConnectionError. Sleeping %d..." % sleep_time)
                            time.sleep(sleep_time)
                            total_sleep += sleep_time
                            sleep_time += 10

                    else:
                        #Bring sleep_time down to a round minute.
                        sleep_time = 60
                        #Skip this page.
                        end = time.time()
                        print("Time of page: %d" % (end-start))
                        print("Page skipped.")
                        continue

                    end = time.time()
                    totaltime += end-start
                    page_count += 1
                    users_sofar.update(page.users)
                    checkpoint['fndms'][fandom] = True
                    sleep_time = 60
    except:
        traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], 
                                  limit=2, file=sys.stdout)
        with open("fandom_lists/checkpoint.json", "w") as fp:
            checkpoint['strt_idx'] = checkpoint['fndm_idx']
            json.dump(checkpoint, fp)

    with open("outputs/users.json", 'w') as fp:
        json.dump(users_sofar, fp)

    error_file.close()

    print("Average Time per page: %d" % (totaltime/page_count))
    print("Total time: %d" % totaltime)
    print("Time sleeping: %d" % total_sleep)
    print("pages: %d" % page_count)