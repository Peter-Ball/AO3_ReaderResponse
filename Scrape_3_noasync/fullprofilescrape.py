import requests, re, bs4
import os
import traceback
import sys

import json, csv

import asyncio
from aiohttp import ClientSession
import aiohttp

from expandedscraper import Chapter, Story, ScraperPage

from functools import wraps

import time

from util_funcs import datestring_in_range

#Global variables
_template = "https://archiveofourown.org{}"
_datapath = "../../data/scrape3_testing/pwrusrs/{}"
sleep_time = 60
total_sleep = 0
totaltime = 0
checkpoint = {}

#Source: https://stackoverflow.com/questions/28965795/how-can-i-reuse-exception-handling-code-for-multiple-functions-in-python
def handle_io(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        global sleep_time
        global total_sleep
        global totaltime
        global checkpoint
        try:
            return f(*args, **kwargs)
        except KeyboardInterrupt:
            workmeta_pointer.close()
            with open("outputs/checkpoint_full.json", "w") as fp:
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
        except aiohttp.client_exceptions.ClientResponseError as errcr:
            print(errcr)
            print("Response error. Sleeping %d..." % sleep_time)
            time.sleep(sleep_time)
            sleep_time += 10
        except loadError as lerr:
            print(lerr)
            print('the bad error happened!')
            print("Total time was %d" % totaltime)
            print("Page Number was %d" % i)
            print("Averate tpp was %d" % (totaltime/i))
            print("Exiting...")
            with open("outputs/checkpoint_full.json", "w") as fp:
                json.dump(checkpoint, fp)

    return decorated

class loadError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def flatten_work(work):
    refit_work = {'ident': work['ident'], 'title': work['title'], 'fandoms': work['fandoms'],
                           'words': work['stats']['words'], 'bookmarks': work['stats']['bookmarks'],
                           'hits': work['stats']['hits'], 'chapters': work['stats']['chapters']}
    return refit_work

#taken from the old crawlerAsync code.
@handle_io
async def get_group(stories=None):

    async with ClientSession() as session:
        tasks = []
        for i in range(0, len(stories)):
            tasks.append(stories[i].get_work(session))
        await asyncio.gather(*tasks)

@handle_io
def get_joindate(upath):
    response = requests.get((_template + 'profile').format(upath))
    html = response.content

    soup = bs4.BeautifulSoup(html,features='lxml')

    metabox = soup.find('dl', attrs={'class': 'meta'})
    dds = metabox.find_all('dd')
    return(dds[1].text)

#Wrapper for error handling
@handle_io
def get_bkmrkpg(upath, idx, req_delay):
    global REQ_DELAY
    url = "https://archiveofourown.org{0}bookmarks?page={1}"
    return ScraperPage(url.format(upath, idx), search_type='bookmark', req_delay=req_delay)

def get_bookmarks(upath, req_delay):
    bookmarks = []
    #get first page:
    for attempt in range(5):
        start = time.perf_counter()
        page1 = get_bkmrkpg(upath, 1, req_delay)
        break
    else:
        sleep_time = 60
        return bookmarks

    #if there are multiple pages, get the navigation buttons
    try:
        navs = page1.soup.find(title='pagination').find_all('li')
    except AttributeError:
        navs = []

    #If its a one page, prep the data and return
    filtered_bookmarks = [bookmark for bookmark in page1.works if datestring_in_range(bookmark[1]['bkmrk_date'], '%d %b %Y', '2015-02-01', '2020-02-01')]
    if len(navs)==0:
        print("This user had {} bookmarks.".format(len(filtered_bookmarks)))
        bookmarks.extend(filtered_bookmarks)
        end = time.perf_counter()
        print('scraping bookmarks took {:.2f} seconds.'.format(end-start))
        return bookmarks

    #if there is more than one page of bookmarks
    page_num = int(navs[-2].get_text())
    print('This user has {} pages of bookmarks'.format(page_num))
    bookmarks.extend(filtered_bookmarks)
    end = time.perf_counter()
    print('Page 1 took {:.2f} seconds'.format(end-start))

    start_idx = 2
    for i in range(start_idx, page_num+1):
        
        for attempt in range(5):
            start = time.perf_counter()
            page = get_bkmrkpg(upath, i, req_delay)
            break
        else:
            sleep_time = 60
            continue

        
        filtered_bookmarks = [bookmark for bookmark in page.works if datestring_in_range(bookmark[1]['bkmrk_date'], '%d %b %Y', '2015-02-01', '2020-02-01')]
        bookmarks.extend(filtered_bookmarks)
        end = time.perf_counter()
        print('page {} took {:.2f} seconds'.format(i, end-start))
        sleep_time = 60

    return bookmarks

def get_giftpg(upath, idx, req_delay):
    global REQ_DELAY
    url = "https://archiveofourown.org{0}gifts?page={1}"
    return ScraperPage(url.format(upath, idx), search_type='work', req_delay=req_delay)

def get_gifts(upath, req_delay):
    gifts = []
    #get first page
    start = time.perf_counter()
    for attempt in range(5):
        page1 = get_giftpg(upath, 1, req_delay)
        break
    else:
        sleep_time = 60
        return gifts

    #if there are multiple pages, get the navigation buttons
    try:
        navs = page1.soup.find(title='pagination').find_all('li')
    except AttributeError:
        navs = []

    #If its a one page, prep the data and return
    filtered_gifts = [gift for gift in page1.works if datestring_in_range(gift['published'], '%d %b %Y', '2015-02-01', '2020-02-01')]
    if len(navs)==0:
        print("This user had {} gifts.".format(len(filtered_gifts)))
        gifts.extend(filtered_gifts)
        end = time.perf_counter()
        print('scraping gifts took {:.2f} seconds.'.format(end-start))
        return gifts

    #if there is more than one page of gifts
    page_num = int(navs[-2].get_text())
    print('This user has {} pages of gifts'.format(page_num))
    gifts.extend(filtered_gifts)
    end = time.perf_counter()
    print('Page 1 took {:.2f} seconds'.format(end-start))

    start_idx = 2
    for i in range(start_idx, page_num+1):
        
        for attempt in range(5):
            start = time.perf_counter()
            page1 = get_giftpg(upath, i, req_delay)
            break
        else:
            sleep_time = 60
            continue

        
        filtered_gifts = [gift for gift in page1.works if datestring_in_range(gift['published'], '%d %b %Y', '2015-02-01', '2020-02-01')]
        gifts.extend(filtered_gifts)
        end = time.perf_counter()
        print('page {} took {:.2f} seconds'.format(i, end-start))
        sleep_time = 60

    return gifts


#Source: https://chrisalbon.com/python/data_wrangling/break_list_into_chunks_of_equal_size/
def chunks(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i+n]
    


if __name__ == "__main__":

    workmeta_pointer = open(_datapath.format('worksmeta.csv'), 'a', encoding='utf-8-sig', newline = '')

    try:
        try:
            with open("outputs/checkpoint_full.json") as fp:
                checkpoint = json.load(fp)
        except FileNotFoundError:
            checkpoint = {'last_user_idx': 0, 'in_idx': 0, 'last_work': None, 'totaltime': 0}


        with open('./user_meta_final_apr02_nosummary.json') as fp:
            usermeta = json.load(fp)

        with open(_datapath.format('powerusers.json')) as fp:
            userlist = json.load(fp)

        workmeta_writer = csv.DictWriter(workmeta_pointer, 
                                        fieldnames = ['ident', 'title', 'author', 'rating', 'warnings', 'category', 'fandoms', 'relationships', 'characters', 'additional_tags',
                                                      'published', 'num_comments', 'words', 'bookmarks', 'kudos', 'hits', 'num_chapters', 'series?', 'error'],
                                        extrasaction = 'ignore',
                                        restval = 'nil')
        if os.path.getsize(_datapath.format('worksmeta.csv')) == 0:
            workmeta_writer.writeheader()
        
        idx = 0

        works_sofar = {}
        try:
            with open(_datapath.format('worksmeta.csv'), encoding='utf-8-sig', newline = '') as fp:
                reader = csv.reader(fp)
                for row in reader:
                    ident = row[0]
                    works_sofar[ident] = True
            print(len(works_sofar))
        except IndexError:
            pass

        REQ_DELAY = 2
        
        for upath in userlist:
            first_thru = False
            idx += 1
            user = usermeta[upath]
            print('User: {}'.format(user['upath']))
            #if upath != '/users/Silverfern500/':
            if checkpoint['last_user_idx'] > idx:  
                continue

            full_time_start = time.perf_counter()
            
            #First user thru is in_idx
            if checkpoint['last_user_idx'] == idx:
                checkpoint['in_idx'] = idx
                first_thru = True

            checkpoint['last_user_idx'] = idx
            if idx % 5 == 0:
                checkpoint['totaltime'] = totaltime
                with open("outputs/checkpoint_full.json", "w") as fp:
                    json.dump(checkpoint, fp)
                with open('outputs/worksofar.json', 'w') as fp:
                    json.dump(works_sofar, fp)

            work_idents = [work['ident'] for work in user['works']]

            workobjs = [Story(ident, REQ_DELAY) for ident in work_idents]
            user['works'] = work_idents
            
            #If this is the first user through after a reboot, then only get works from the last one grabbed.
            if first_thru:
                #Only shorten workobj list if last_work is in the list
                try:
                    last_work_idx = work_idents.index(checkpoint['last_work'])
                    workobjs = workobjs[last_work_idx+1:]
                except ValueError:
                    pass

                first_thru = False
            

            #First grab the join date from profile page:
            try:
                user['joindate'] = get_joindate(user['upath'])
            except AttributeError:
                with open('outputs/missingusers.txt', 'a') as fp:
                    fp.write(user['upath'] + '\n')
                continue
            print('Joined: {}'.format(user['joindate']))

            #Then get the user's 
            #try:
            print("Getting works...")
            for work in workobjs:
                for attempt in range(5):   
                    try:
                        work.get_work()

                        #moved writing sequence to central for loop
                        workdict = work.return_dict()
                        workdict['author'] = user['upath']
                        workdict['series?'] = False
                        checkpoint['last_work'] = workdict['ident']
                        
                        #Always write to metatable for workobjs because they have the most info
                        #Will need to remove duplicates afterwards
                        #Write work metadata into the metadata csv
                        workmeta_writer.writerow(workdict)
                        works_sofar[workdict['ident']] = True

                        allcomments = [item for sublist in [ch['comments'] for ch in workdict['chapters']] for item in sublist]
                        try:
                            os.mkdir(_datapath.format('works/{0}/'.format(workdict['ident'])))
                        except FileExistsError:
                            pass

                        #Write the full text into a .txt
                        with open(_datapath.format('works/{0}/{0}.txt'.format(workdict['ident'])), 'w', encoding='utf-8-sig') as fp:
                            i = 1
                            for chapter in workdict['chapters']:
                                fp.write("Chapter {}\n".format(i))
                                fp.write(chapter['text'])
                                fp.write("\n")
                                i += 1

                        #Write all the comments into a json included with the text
                        with open(_datapath.format('works/{0}/{0}_comments.json'.format(workdict['ident'])), 'w', encoding='utf-8-sig') as fp:
                            json.dump(allcomments, fp)

                        break

                    except KeyboardInterrupt:
                        workmeta_pointer.close()
                        with open("outputs/checkpoint_full.json", "w") as fp:
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
                    except requests.exceptions.HTTPError as errh:
                        print(errh)
                        print("HttpError. Sleepng %d..." % sleep_time)
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
                    except aiohttp.client_exceptions.ClientResponseError as errcr:
                        print(errcr)
                        print("Response error. Sleeping %d..." % sleep_time)
                        time.sleep(sleep_time)
                        sleep_time += 10
                    except loadError as lerr:
                        print(lerr)
                        print('the bad error happened!')
                        print("Total time was %d" % totaltime)
                        print("Page Number was %d" % i)
                        print("Averate tpp was %d" % (totaltime/i))
                        print("Exiting...")
                        with open("outputs/checkpoint_full.json", "w") as fp:
                            json.dump(checkpoint, fp)

                else:
                    sleep_time = 60
                    print('Skipping chunk')
                



            print("Getting Bookmarks...")
            bookmarks = get_bookmarks(user['upath'], req_delay=REQ_DELAY)

            print("Getting Gifts...")
            gifts = get_gifts(user['upath'], req_delay=REQ_DELAY)

            sleep_time = 60

            usr_bkmrklist = [bkmrk[1] for bkmrk in bookmarks]

            user['bookmarks'] = usr_bkmrklist

            user['gifts'] = [gift['ident'] for gift in gifts]

            #write the new user metadata back to a new jsonl file
            with open(_datapath.format('new_users.jsonl'), 'a') as fp:
                fp.write(json.dumps(user) + '\n')

            for bookmark in bookmarks:
                workinfo = bookmark[0]
                if workinfo['ident'] not in works_sofar:
                    workinfo['error'] =200
                    workmeta_writer.writerow(workinfo)
                    works_sofar[workinfo['ident']] = True

            for gift in gifts:
                if gift['ident'] not in works_sofar:
                    gift['error'] = 200
                    workmeta_writer.writerow(gift)
                    works_sofar[gift['ident']] = True

            full_time_end = time.perf_counter()
            full_time = full_time_end - full_time_start
            totaltime += full_time/60
            print('user {0}, idx {1} done. Time was {2}'.format(user['upath'], str(idx), str(full_time)))

        print("Done!")
        workmeta_pointer.close()
    except:
        traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], 
                                      file=sys.stdout)
        workmeta_pointer.close()
        with open("outputs/checkpoint_full.json", "w") as fp:
            json.dump(checkpoint, fp)



        
