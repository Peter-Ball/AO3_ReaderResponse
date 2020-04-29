
import requests, re, bs4

#import expandedscraperAsync

import os
import traceback
import sys

import json, pickle

import time

from datetime import datetime

import asyncio
import aiohttp
from aiohttp import ClientSession

from urllib.parse import quote
#template url for a fandom search between two dates
#fandomstring MUST be converted to urlencoded text first
#format with tuple of form ('fandomstring', 'page#' 'yyyy-mm-dd', 'yyyy-mm-dd')
_WORKS_TEMPLATE = "https://archiveofourown.org{0}works?commit=Sort+and+Filter&page={{0}}&utf8=%E2%9C%93&work_search%5Bdate_from%5D={1}&work_search%5Bdate_to%5D={2}&work_search%5Blanguage_id%5D=1"

#SOME GLOBAL VARIABLES:

#warning_sign is incremented every time there is a disconnect error
#If an interation runs all the way through, warning_sign is reset to 0
#If warning sign reaches 100, that means there have been 100 consecutive
#disconnect errors, so the program exits.
class ScraperPage(object):

    def __init__(self, url=None, search_type='work'):

        response = requests.get(url)
        html = response.content

        if search_type == 'work':
            at_cls = 'work blurb group'
        if search_type == 'user':
            at_cls = 'user pseud picture blurb group'

        self.works = []

        self.soup = bs4.BeautifulSoup(html, features='lxml')

        if re.search(r'Retry later', self.soup.text) and len(self.soup.text) < 1000:
            raise requests.exceptions.ConnectionError
        for story in self.soup.find_all('li', attrs={'class': at_cls}):
            info = {}
            info['ident'] = re.search('\d+', story.get('id')).group(0)
            info['title'], info['author'] = [a.text for a in story.find('h4').find_all('a')][:2]
            info['fandoms'] = [a.text for a in story.find('h5').find_all('a')]
            info['date'] = story.find('p', attrs= {'class': 'datetime'}).text
            
            #info['stats'] = {'words': '0', 'bookmarks': '0', 'kudos': '0', 'chapters': '0', 'hits': '0'}
            info['stats'] = {}
            info['stats']['words'] = int(self.lookup_stat('words', default='0').replace(',', ''))
            info['stats']['bookmarks'] = int(self.lookup_stat('bookmarks', default='0').replace(',', ''))
            info['stats']['kudos'] = int(self.lookup_stat('kudos', default='0').replace(',', ''))
            info['stats']['hits'] = int(self.lookup_stat('hits', default='0').replace(',', ''))

            info['stats']['chapters'] = re.search(r'\d+', self.soup.find('dd', attrs={'class': 'chapters'}).text).group(0)

            #stat_namenum_zip = [(dd_tag.get('class')[0], dd_tag.text) for dd_tag in story.find_all('dd')]
            #info['stats'].update({k:v for k, v in stat_namenum_zip})


            self.works.append(info)

        print("lenght is  %d" % len(self.works))

    #Straight from works.py
    def lookup_stat(self, class_name, default=None):
        dd_tag = self.soup.find('dd', attrs={'class': class_name})
        if dd_tag is None:
            return default
        if dd_tag.text == '':
            return default
        if 'tags' in dd_tag.attrs['class']:
            return self._lookup_list_stat(dd_tag=dd_tag)
        return dd_tag.text

    def _lookup_list_stat(self, dd_tag):
        """Returns the value of a list statistic.

        Some statistics can have multiple values (e.g. the list of characters).
        This helper method should be used to retrieve those.

        """
        # A list tag is stored in the form
        #
        #     <dd class="[field_name] tags">
        #       <ul class="commas">
        #         <li><a href="/further-works">[value 1]</a></li>
        #         <li><a href="/more-info">[value 2]</a></li>
        #         <li class="last"><a href="/more-works">[value 3]</a></li>
        #       </ul>
        #     </dd>
        #
        # We want to get the data from the individual <li> elements.
        li_tags = dd_tag.findAll('li')
        a_tags = [t.contents[0] for t in li_tags]
        return [t.contents[0] for t in a_tags]


from functools import wraps

class loadError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

#Wrapper for async downloads. Important part is  the gather statement
async def get_page(stories=None):

    async with ClientSession() as session:
        tasks = []
        for i in range(0, len(stories)):
            tasks.append(stories[i].get_work(session))
        await asyncio.gather(*tasks)

def encode_url(user, date_from, date_to):
    return _WORKS_TEMPLATE.format(user, date_from, date_to)

def get_front(url):
    return ScraperPage(url)

'''def process_story(page):

    #This list holds the IDs of stories from this page
    stories = []
    for elem in page.IDs:
        stories.append(expandedscraperAsync.Story(elem))

    #Access all pages asynchronously. Check for warning_sign
    if(warning_sign > 100):
        raise loadError('strange things are afoot')
    asyncio.run(get_page(stories))
    warning_sign = 0
    print("Commence Writing Sequence")
    for story in stories:
        #Returns a json string
        print("stringing %s" % story.id_)
        story_obj = story.return_json()
        print("stringed")
        #Writing in jsonl format!
        #If the story is in multiple fandoms, we put it in crossover
        #else, we put it in the current fandom jsonl
        output.write('%s\n' % story_obj)
        print("object written: %s" % story.id_)'''


if __name__ == "__main__":
    try:
        output = open("outputs/user_meta.jsonl", "a")


        try:
            with open("outputs/checkpoint_meta.json") as fp:
                checkpoint = json.load(fp)
        except FileNotFoundError:
            checkpoint = {'strt_idx': 0, 'curr_idx': 0}
        

        warning_sign = 0
        #Amount of time the program sleeps after a disconnect error.
        #For each disconnect error that happens on one page, add 10 seconds.
        sleep_time = 60

        totaltime = 0
        pagecnt = 1
        total_sleep = 0

        '''with open("outputs/users.json") as fp:
            users = json.load(fp)'''

        with open("outputs/user_sample1.pkl", 'rb') as fp:
            users = pickle.load(fp)
        #USER LOOP: Iterates over the users in the user dict
        for user_idx in range(0, len(users)):
            if user_idx < checkpoint['strt_idx']:
                continue

            user = users[user_idx]
            try:
                if user['num_works'] < 20:
                    checkpoint['curr_idx'] += 1
                    continue
                if len(user['works']) > 0:
                    checkpoint['curr_idx'] += 1
                    continue
            except:
                pass

            #encode the template urls for the fandom
            #split it in to two because searches are cut off after
            #100000 results.

            work_url = encode_url(user['upath'], '2015-02-01', '2020-02-01')
            user['works'] = []
            print(user['upath'])

            #get the number of pages:
            for i in range(5):
                try:
                    front_page = get_front(work_url.format(1))
                    pagecnt += 1
                    break
                except KeyboardInterrupt:
                    output.close()
                    print("Looks like you are leaving, let me prep some final data...")
                    print("Total time was %d" % totaltime)
                    print("Averate tpp was %d" % (totaltime/pagecnt))
                    print("Time sleeping: %d" % total_sleep)
                    print("Goodbye!")
                    with open("outputs/checkpoint_meta.json", "w") as fp:
                                checkpoint['strt_idx'] = checkpoint['curr_idx']
                                json.dump(checkpoint, fp)
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
                except aiohttp.client_exceptions.ServerDisconnectedError as errs:
                    warning_sign += 1
                    print(errs)
                    print('ServerDisconnectedError. Sleeping %d...' % sleep_time)
                    time.sleep(sleep_time)
                    total_sleep += sleep_time
                    sleep_time += 10
                except loadError as lerr:
                    print(lerr)
                    print('the bad error happened!')
                    print("Total time was %d" % totaltime)
                    print("Page Number was %d" % i)
                    print("Averate tpp was %d" % (totaltime/i))
                    print("Exiting...")
                    sys.exit(1)
            else:
                checkpoint['curr_idx'] += 1
                sleep_time = 60
                continue
            try:
                navs = front_page.soup.find(title='pagination').find_all('li')
            except AttributeError:
                #print(front_page.soup.find('h2', attrs={'class': 'heading'}).text)
                #navs = []
                checkpoint['curr_idx'] += 1
                sleep_time = 60
                continue

            if(len(navs) > 0):
                page_num = int(navs[-2].get_text())
                user['works'] += front_page.works
            else:
                user['works'] += front_page.works
                user['total_kudos'] = 0 
                user['total_bookmarks'] = 0
                user['total_words'] = 0
                for work in user['works']:
                    user['total_kudos'] += int(work['stats']['kudos'])
                    user['total_bookmarks'] += int(work['stats']['bookmarks'])
                    user['total_words'] += int(work['stats']['words'])

                output.write(json.dumps(user) + '\n')
                checkpoint['curr_idx'] += 1
                sleep_time = 60
                continue
                #process_story(front_page)


            #CENTRAL LOOP: Iterate over every page in the fandom home
            for i in range(2,page_num+1):
                
                start = time.time()
                url = work_url.format(i)

                for attempt in range(10):
                    try:
                        print("getting user {} meta".format(user['upath']))
                        page = get_front(url)
                        user['works'].extend(page.works)
                        print(len(page.works))
                        print()
                        pagecnt += 1
                        break
                    except KeyboardInterrupt:
                        output.close()
                        print("Looks like you are leaving, let me prep some final data...")
                        print("Total time was %d" % totaltime)
                        print("Averate tpp was %d" % (totaltime/page_cnt))
                        print("Time sleeping: %d" % total_sleep)
                        print("Goodbye!")
                        with open("outputs/checkpoint_meta.json", "w") as fp:
                            checkpoint['strt_idx'] = checkpoint['curr_idx']
                            json.dump(checkpoint, fp)

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
                    except aiohttp.client_exceptions.ServerDisconnectedError as errs:
                        warning_sign += 1
                        print(errs)
                        print('ServerDisconnectedError. Sleeping %d...' % sleep_time)
                        time.sleep(sleep_time)
                        total_sleep += sleep_time
                        sleep_time += 10
                    except loadError as lerr:
                        print(lerr)
                        print('the bad error happened!')
                        print("Total time was %d" % totaltime)
                        print("Page Number was %d" % i)
                        print("Averate tpp was %d" % (totaltime/i))
                        print("Exiting...")
                        with open("outputs/checkpoint_meta.json", "w") as fp:
                            checkpoint['strt_idx'] = checkpoint['curr_idx']
                            json.dump(checkpoint, fp)
                        
                        sys.exit(1)
                    #process_story(page)
                else:
                    #Bring sleep_time down to a round minute.
                    sleep_time = 60
                    #Skip this page.
                    end = time.time()
                    print("Time of page: %d" % (end-start))
                    print("Page skipped.")
                    continue
                #path = ("./Data/HungerGamesTrillogy/page%s" % i)

                end = time.time()

                print("Time of page: %d" % (end-start))
                totaltime += (end-start)
                sleep_time = 60
                #END CENTRAL LOOP

            user['total_kudos'] = 0 
            user['total_bookmarks'] = 0
            user['total_words'] = 0
            user['total_hits'] = 0
            for work in user['works']:
                user['total_kudos'] += work['stats']['kudos']
                user['total_bookmarks'] += work['stats']['bookmarks']
                user['total_words'] += work['stats']['words']
                user['total_hits'] += work['stats']['hits']


            output.write(json.dumps(user) + '\n')
            checkpoint['curr_idx'] += 1
            sleep_time = 60
            #END USER LOOP
    except:
        traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], 
                                  file=sys.stdout)
        with open("outputs/checkpoint_meta.json", "w") as fp:
            checkpoint['strt_idx'] = checkpoint['curr_idx']
            json.dump(checkpoint, fp)

    output.close()


    print("Average Time per page: %.2f" % (totaltime/pagecnt))
    print("Total time: %d" % totaltime)
    print("Time sleeping: %d" % total_sleep)
    print("pages: %d" % pagecnt)
