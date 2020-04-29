
import requests, re, bs4

#import expandedscraperAsync

import os
import traceback
import sys

import json, pickle

import time

from datetime import datetime

from urllib.parse import quote

_WORKS_TEMPLATE = "https://archiveofourown.org{0}works?commit=Sort+and+Filter&page={{0}}&utf8=%E2%9C%93&work_search%5Bdate_from%5D={1}&work_search%5Bdate_to%5D={2}&work_search%5Blanguage_id%5D=1"

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
            topbox = [a.text for a in story.find('h4').find_all('a')]
            info['title'], info['author'] = topbox[:2]
            #If giftee is there, then collect it
            try:
                info['giftee'] = topbox[3]
            except IndexError:
                info['giftee'] = ''
            try:
                info['fandoms'] = [a.text for a in story.find('h5').find_all('a')]
            except AttributeError:
                info['fandoms'] = []
            info['date'] = story.find('p', attrs= {'class': 'datetime'}).text
            try:
                info['summary'] = story.find('blockquote', attrs = {'class': 'userstuff summary'}).text
            except AttributeError:
                info['summary'] = ''
            
            #info['stats'] = {'words': '0', 'bookmarks': '0', 'kudos': '0', 'chapters': '0', 'hits': '0'}
            info['words'] = int(self.lookup_stat(story, 'words', default='0').replace(',', ''))
            info['bookmarks'] = int(self.lookup_stat(story, 'bookmarks', default='0').replace(',', ''))
            info['kudos'] = int(self.lookup_stat(story, 'kudos', default='0').replace(',', ''))
            info['hits'] = int(self.lookup_stat(story, 'hits', default='0').replace(',', ''))

            info['chapters'] = re.search(r'\d+', story.find('dd', attrs={'class': 'chapters'}).text).group(0)

            #stat_namenum_zip = [(dd_tag.get('class')[0], dd_tag.text) for dd_tag in story.find_all('dd')]
            #info['stats'].update({k:v for k, v in stat_namenum_zip})


            self.works.append(info)

    #Straight from works.py
    def lookup_stat(self, storyframe, class_name, default=None):
        dd_tag = storyframe.find('dd', attrs={'class': class_name})
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


if __name__ == "__main__":
    totaltime = 0
    pagecnt = 1
    total_sleep = 0
    try:
        output = open("outputs/user_meta.jsonl", "a")
        time_rec = open("outputs/time_rec.jsonl", "a")


        try:
            with open("outputs/checkpoint_meta.json") as fp:
                checkpoint = json.load(fp)
        except FileNotFoundError:
            checkpoint = {"strt_idx": 0, "curr_idx": 0}
        

        warning_sign = 0
        #Amount of time the program sleeps after a disconnect error.
        #For each disconnect error that happens on one page, add 10 seconds.
        sleep_time = 70

        with open("outputs/user_sample2-1.pkl", 'rb') as fp:
            users = pickle.load(fp)
        #USER LOOP: Iterates over the users in the user dict
        for user_idx in range(len(users)):
            if user_idx < checkpoint['strt_idx']-1:
                continue

            user = users[user_idx]
            try:
                if user['works'] > 0:
                    continue
            except:
                pass

            if user_idx % 10 == 0:
                with open("outputs/checkpoint_meta.json", "w") as fp:
                    checkpoint['strt_idx'] = checkpoint['curr_idx']
                    json.dump(checkpoint, fp)
            
            checkpoint['curr_idx'] += 1
            #Encode the url for this user between these dates
            work_url = encode_url(user['upath'], '2015-02-01', '2020-02-01')
            user['works'] = []
            print(user['upath'])

            #get the number of pages:
            for i in range(5):
                try:
                    start = time.perf_counter()
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
                except loadError as lerr:
                    print(lerr)
                    print('the bad error happened!')
                    print("Total time was %d" % totaltime)
                    print("Page Number was %d" % i)
                    print("Averate tpp was %d" % (totaltime/pagecnt))
                    print("Exiting...")
                    sys.exit(1)
            else:
                sleep_time = 70
                continue
            try:
                navs = front_page.soup.find(title='pagination').find_all('li')
            except AttributeError:
                navs = []

            if(len(navs) > 0):
                page_num = int(navs[-2].get_text())
                print("This user has %d pages of works" % page_num)
                user['works'] += front_page.works
                end = time.perf_counter()
                print("Time of page 1: %.2f" % (end-start))
            else:
                print("This user has %d works." % len(front_page.works))
                user['works'] += front_page.works
                user['total_kudos'] = 0 
                user['total_bookmarks'] = 0
                user['total_words'] = 0
                for work in user['works']:
                    user['total_kudos'] += int(work['kudos'])
                    user['total_bookmarks'] += int(work['bookmarks'])
                    user['total_words'] += int(work['words'])

                output.write(json.dumps(user) + '\n')
                end = time.perf_counter()
                print("Time of page: %.2f" % (end-start))
                totaltime += (end-start)
                time_rec.write(json.dumps({"status": "successful", "time": time.time(), "total_time": totaltime}) + '\n')
                continue
                #process_story(front_page)

            start_idx = 2
            #CENTRAL LOOP: Iterate over every page pf works
            for i in range(start_idx,page_num+1):
                pagecnt += 1
                start = time.perf_counter()
                url = work_url.format(i)
                for attempt in range(10):
                    try:
                        page = get_front(url)
                        user['works'].extend(page.works)
                        break
                    except KeyboardInterrupt:
                        output.close()
                        time_rec.close()
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
                    except loadError as lerr:
                        print(lerr)
                        print('the bad error happened!')
                        print("Total time was %d" % totaltime)
                        print("Page Number was %d" % i)
                        print("Averate tpp was %d" % (totaltime/pagecnt))
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
                    end = time.perf_counter()
                    print("Time of page %d: %.2f" % (i, (end-start)))
                    print("Page skipped.")
                    total_time += (end-start)
                    continue
                    #path = ("./Data/HungerGamesTrillogy/page%s" % i)

                end = time.perf_counter()

                print("Time of page %d: %.2f" % (i, (end-start)))
                totaltime += (end-start)
                time_rec.write(json.dumps({"status": "successful", "time": time.time(), "total_time": totaltime}) + '\n')
                sleep_time = 70
                #END CENTRAL LOOP

            user['total_kudos'] = 0 
            user['total_bookmarks'] = 0
            user['total_words'] = 0
            user['total_hits'] = 0
            for work in user['works']:
                user['total_kudos'] += work['kudos']
                user['total_bookmarks'] += work['bookmarks']
                user['total_words'] += work['words']
                user['total_hits'] += work['hits']

            output.write(json.dumps(user) + '\n')

            sleep_time = 70
            #END USER LOOP
    except:
        traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], 
                                  file=sys.stdout)
        with open("outputs/checkpoint_meta.json", "w") as fp:
            checkpoint['strt_idx'] = checkpoint['curr_idx']
            json.dump(checkpoint, fp)

    output.close()
    time_rec.close()
    with open("outputs/checkpoint_meta.json", "w") as fp:
            checkpoint['strt_idx'] = checkpoint['curr_idx']
            json.dump(checkpoint, fp)

    print("Average Time per page: %.2f" % (totaltime/pagecnt))
    print("Total time: %d" % totaltime)
    print("Time sleeping: %d" % total_sleep)
    print("pages: %d" % pagecnt)