'''
Author: Peter Ball, summer 2019 (peter.ball@mail.mcgill.ca)

This is where Chapter, Story, and ScraperPage objects are defined.

A Chapter object stores the text from one chapter of a story, as
well as a list of comments, which are represented as dicts.

A Story object has an ID which corresponds to a work ID on AO3, and
stores various metadata about that work. It also has a list of 'Chapter'
objects which store the text and comments of each chapter of the work.

A ScraperPage object takes a URL in it's init and scrapes the page at
that URL (The URL must be a page from AO3's fandom search function). Then
it finds each story on that page and generates a Story object for those
stories, acting as a container for each Story object.


This document is designed ONLY to be called by the 'crawlerAsync.py' code.
It depends on the 'works.py' code in this directory, which is an adapted 
version of the codeby the same name from alexwlchan's AO3 Python interface 
found at https://github.com/alexwlchan/ao3. Other dependencies can be
seen in the import statements.
'''

import json

import requests, re, bs4

import os
import sys
import traceback
from datetime import datetime

import works

from util_funcs import request_wrapper


_STORY_URL_TEMPLATE = "https://archiveofourown.org/works/%s?show_comments=true&view_full_work=true"


_COMMENT_CHAP_EXPR = 'on Chapter %d'

class Chapter(object):
    def __init__(self, text=None):
        self.text = text

        self.comments = []

    def add_comment(self, comment=None):
        self.comments.append(comment)


class Story(object):
    def __init__(self, id_=None, req_delay=5):
        #In init clause, just get the id and generate work object
        #This is so code plays nicely with async
        #TODO: Is this necessary? Try integrating with get_meta
        self.id_ = id_
        self.work = works.Work(id_)
        self.req_delay = req_delay

    def get_meta(self, sess=None):
        #Try statements for each datum.
        #TODO: find a prettier way to write this

        try:
            self.title = self.work.title
        except:
            self.title = ""
        try:
            self.author = self.work.author
        except:
            self.author = ""

        try:
            self.summary =  self.work.summary
        except:
            self.summary = ""

        try:
            self.rating = self.work.rating
        except:
            self.rating = ""

        try:
            self.warnings = self.work.warnings
        except:
            self.warnings = []

        try:
            self.category = self.work.category
        except:
            self.category = []

        try:
            self.fandoms = self.work.fandoms
        except:
            self.fandoms = []

        try:
            self.relationship = self.work.relationship
        except: 
            self.relationship = []

        try:
            self.characters = self.work.characters
        except:
            self.characters = []

        try:
            self.additional_tags = self.work.additional_tags
        except:
            self.additional_tags = ""

        try:
            self.language = self.work.language
        except:
            self.language = ""

        try:
            self.published = str(self.work.published)
        except:
            self.published = ""

        try:
            self.words = self.work.words
        except:
            self.words = 0

        try:
            self.kudos = self.work.kudos
        except:
            self.kudos = 0

        try:
            self.bookmarks = self.work.bookmarks
        except:
            self.bookmarks = 0

        try:
            self.hits = self.work.hits
        except:
            self.hits = 0

        self.chapters = []

        self.url = _STORY_URL_TEMPLATE % (self.id_)
        self.html = ""

        self.num_comments = 0
        self.num_chapters = 0

        if self.error == 200:
            self.download_chapters()

            self.num_comments = sum([len(ch.comments) for ch in self.chapters])
            self.num_chapters = len(self.chapters)

    def get_work(self):
        self.error = 200
        try:
            self.work.make_request(self.req_delay)
            
        except works.WorkNotFound as errw:
            print(errw)
            self.error = 404

        except RuntimeError as errr:
            print(errr)
            self.error = 2

        except AttributeError:
            file = open('error_file.txt', 'a')
            message = ("story %s: %s occurred at %s\n\n"
                        % (self.id_, traceback.format_exc(), datetime.now()))
            file.write(message)
            file.close()
            self.error = 1

        print("working on story %s, error is %s" % (self.id_, str(self.error)))
        self.get_meta()


    def download_chapters(self):
        #SCRAPE CHAPTER TEXT, SAVE INTO CHAPTERS DICT

        print("downloading chapters %s..." % self.id_)
        self.html = self.work._html

        self.soup = bs4.BeautifulSoup(self.html, features='lxml')

        chapters = []
        
        #Two cases: Only one chapter, or multiple chapters. HTML is different for the two
        #RenderContents() removes erronious html tags. It is slow, but not too bad
        if (self.soup.find(class_='chapter') == None):
            chapter_text = ''
            
            for p in self.soup.find(id = 'chapters').find_all('p'):
                chapter_text = chapter_text + ('%s\n' % p.renderContents().decode('utf-8'))

            temp = Chapter(chapter_text)
            chapters.append(temp)
            

        else:
            chapter_objs = self.soup.find_all('div', id=re.compile("^chapter-\d+"))
            for chap in chapter_objs:
                chapter_text = ""

                for p in chap.find_all("p"):
                    chapter_text = chapter_text + ("%s\n" % p.renderContents().decode('utf-8'))

                temp = Chapter(chapter_text)
                chapters.append(temp)
        #END SCRAPE CHAP TXT
        print("Chapters scraped: %s" % self.id_)
        self.chapters = chapters

        self.download_comments()

    def download_comments(self):
        #BEGIN COMMENTS SECTION
        
        #need to get the comment page, pull the text with bs4, then set up another bs4 that will tree the text
        print("Downloading comments %s..." % self.id_)
        comments = []
        new_soup = self.soup
        a_tag = new_soup.find(title='next')
        comments = self.soup.find_all('li', id=re.compile('^comment_\d+'))
        if a_tag != None:
            while a_tag.a != None:
                link = "https://archiveofourown.org%s" % a_tag.a.get('href')
                print("Paginating %s..." % self.id_)
                req = request_wrapper(link, self.req_delay)
                new_html = req.content
                new_soup = bs4.BeautifulSoup(new_html, features='lxml')
                comments.extend(new_soup.find_all('li', id=re.compile('^comment_\d+')))
                a_tag = new_soup.find(title='next')


        #find every comment from chapter j, store its info in the json, then increment j.
        j = 0
        comment_list = []
        for i in range(0, len(comments)):
            if '(Previous comment deleted.)' in comments[i].text:
                continue
            while( (_COMMENT_CHAP_EXPR % j) not in comments[i].find('span').get_text() and j < len(self.chapters)):
                j = j+1
            
            comment = {}

            #get date. will have format: 01 Jan 2018.
            date = comments[i].find(class_='date').get_text() + ' ' + comments[i].find(class_='month').get_text() + ' ' + comments[i].find(class_= 'year').get_text()
            
            #time in separate dict that has clock time and time zone. Format: {08:47AM, EDT}
            time = comments[i].find(class_='time').get_text()
            timezone = comments[i].find(class_='timezone').get_text()
            comment['ident'] = int(re.search('\d+', comments[i].get('id')).group(0))
            comment['date'] = date
            comment['time'] = {'clock_time': time, 'time_zone': timezone}

            comment['user'] = comments[i].find('a').get_text()

            comment['text'] = comments[i].find('blockquote', attrs={'class': 'userstuff'}).get_text()
            comment['chapter'] = j

            try:
                comment['parent'] = int(re.search('\d+', comments[i].find('ul', attrs={'class': 'actions'}).find('a', text = "Parent Thread").get('href')).group(0))
            except AttributeError:
                comment['parent'] = ''

            self.chapters[j-1].add_comment(comment)
        print("Comments done %s" % self.id_)

    #Only grab the first page of comments --- MUCH faster, but obvious limitations
    def fstpg_comments(self):
        print("Downloading comments %s..." % self.id_)
        comments = self.soup.find_all('li', id=re.compile('^comment_\d+'))

        j = 0
        comment_list = []
        for i in range(0, len(comments)):
            while( (_COMMENT_CHAP_EXPR % j) not in comments[i].find('span').get_text() and j < len(self.chapters)):
                j = j+1
            
            comment = {}

            #get date. will have format: 01 Jan 2018.
            date = comments[i].find(class_='date').get_text() + ' ' + comments[i].find(class_='month').get_text() + ' ' + comments[i].find(class_= 'year').get_text()
            
            #time in separate dict that has clock time and time zone. Format: {08:47AM, EDT}
            time = comments[i].find(class_='time').get_text()
            timezone = comments[i].find(class_='timezone').get_text()

            comment['date'] = date
            comment['time'] = {'clock_time': time, 'time_zone': timezone}
            comment['user'] = comments[i].find('a').get_text()
            comment['text'] = comments[i].find(class_='userstuff').find('p').get_text()

            self.chapters[j-1].add_comment(comment)
        

        print("Comments done %s" % self.id_)
    #END COMMENTS SECTION


    def return_dict(self):
        data = {
        'ident': self.id_,
        'title': self.title,
        'author': self.author,
        'summary': self.summary,
        'rating': self.rating,
        'warnings': self.warnings,
        'category': self.category,
        'fandoms': self.fandoms,
        'relationships': self.relationship,
        'characters': self.characters,
        'additional_tags': self.additional_tags,
        'language': self.language,
        'published': self.published,
        'words': self.words,
        'kudos': self.kudos,
        'bookmarks': self.bookmarks,
        'hits': self.hits,
        'num_comments': self.num_comments,
        'num_chapters': self.num_chapters,
        'error': self.error
        }

        chapter_holder = []

        for chapter in self.chapters:
            curr_dict = {
            'text': chapter.text,
            'comments': chapter.comments
            }
            chapter_holder.append(curr_dict)
                                

        data['chapters'] = chapter_holder

        return data




class ScraperPage(object):

    def __init__(self, url=None, search_type='work', req_delay=5):

        response = request_wrapper(url, req_delay)
        html = response.content

        if search_type == 'work':
            at_cls = 'work blurb group'
        if search_type == 'user':
            at_cls = 'user pseud picture blurb group'
        if search_type == 'bookmark':
            at_cls = 'bookmark blurb group'

        self.works = []

        self.soup = bs4.BeautifulSoup(html, features='lxml')

        if re.search(r'Retry later', self.soup.text) and len(self.soup.text) < 1000:
            raise requests.exceptions.ConnectionError
            
        for story in self.soup.find_all('li', attrs={'class': at_cls}):
            work_info = {}

            #If its a mystery work we skip it
            if story.find('div', attrs={'class': 'mystery'}):
                continue

            #Check if the bookmark has been deleted
            if search_type == 'bookmark':
                work_info['series?'] = False
                try:
                    msg = story.find('p', attrs={'class': 'message'}).text
                    if msg == 'This has been deleted, sorry!':
                        continue
                except AttributeError:
                    pass

            #Get story ident
            if search_type == 'work':
                work_info['ident'] = re.search('\d+', story.get('id')).group(0)
            elif search_type == 'bookmark':
                try:
                    work_info['ident'] = re.search('\d+', story.find('div', attrs={'class': 'header module'}).find('a', attrs={'href': re.compile(r'/works/\d+')})['href']).group(0)
                except TypeError:
                    try:
                        work_info['ident'] = re.search('\d+', story.find('div', attrs={'class': 'header module'}).find('a', attrs={'href': re.compile(r'/series/\d+')})['href']).group(0)
                        work_info['series?'] = True
                    except TypeError:
                        #If it's an external work we throw it away because we can't get any info on it really
                        if re.search('\d+', story.find('div', attrs={'class': 'header module'}).find('a', attrs={'href': re.compile(r'/external_works/\d+')})['href']).group(0):
                            continue

                except AttributeError:
                    if story.find('div', attrs={'class': 'mystery'}):
                        continue
                    else:
                        raise AttributeError

            topbox = [a for a in story.find('h4').find_all('a')]
            work_info['title'] = topbox[0].text
            try:
                work_info['author'] = '/users/{}/'.format(topbox[1].text)
            except IndexError:
                work_info['author'] = 'Anonymous'
            work_info['published'] = story.find('p', attrs= {'class': 'datetime'}).text
            try:
                if not topbox[-1].has_attr('rel'):
                    work_info['giftee'] = topbox[-1]['href'].split('gifts')[0]
                else:
                    work_info['giftee'] = ''
            except IndexError:
                work_info['giftee'] = ''
            try:
                work_info['fandoms'] = [a.text for a in story.find('h5').find_all('a')]
            except AttributeError:
                work_info['fandoms'] = []

            try:
                work_info['warnings'] = [li.find('a', attrs={'class': 'tag'}).text for li in story.find_all('li', attrs={'class': 'warnings'})]
            except AttributeError:
                work_info['warnings'] = []

            try:
                work_info['relationships'] = [li.find('a', attrs={'class': 'tag'}).text for li in story.find_all('li', attrs={'class': 'relationships'})]
            except AttributeError:
                work_info['relationships'] = []

            try:
                work_info['characters'] = [li.find('a', attrs={'class': 'tag'}).text for li in story.find_all('li', attrs={'class': 'characters'})]
            except AttributeError:
                work_info['characters'] = []
            try:
                work_info['additional_tags'] = [li.find('a', attrs={'class': 'tag'}).text for li in story.find_all('li', attrs={'class': 'freeforms'})]
            except AttributeError:
                work_info['additional_tags'] = []

            try:
                work_info['summary'] = story.find('blockquote', attrs = {'class': 'userstuff summary'}).text
            except AttributeError:
                work_info['summary'] = ''
            
            #info['stats'] = {'words': '0', 'bookmarks': '0', 'kudos': '0', 'chapters': '0', 'hits': '0'}
            work_info['words'] = int(self.lookup_stat(story, 'words', default='0').replace(',', ''))
            work_info['bookmarks'] = int(self.lookup_stat(story, 'bookmarks', default='0').replace(',', ''))
            work_info['kudos'] = int(self.lookup_stat(story, 'kudos', default='0').replace(',', ''))
            work_info['hits'] = int(self.lookup_stat(story, 'hits', default='0').replace(',', ''))
            work_info['num_comments'] = int(self.lookup_stat(story, 'comments', default='0').replace(',', ''))

            try:
                work_info['num_chapters'] = re.search(r'\d+', self.soup.find('dd', attrs={'class': 'chapters'}).text).group(0)
            except AttributeError:
                #If it gets here it is likely a series so we put a null value
                work_info['num_chapters'] = None

            if search_type == 'bookmark':
                bkmrk_info = {}
                bkmrk_info['ident'] = work_info['ident']
                bkmrk_info['type'] = ''
                status = story.find('p', attrs={'class': 'status'}).text
                if 'Rec' in status:
                    bkmrk_info['type'] = 'Rec'
                if 'Public Bookmark' in status:
                    bkmrk_info['type'] = 'Public Bookmark'

                bottombox = story.find('div', attrs={'class': 'user module group'})
                bkmrk_info['bkmrk_date'] = bottombox.find('p', attrs={'class':'datetime'}).text
                try:
                    bkmrk_info['bkmrk_note'] = bottombox.find('blockquote', attrs={'class': 'userstuff notes'}).find('p').text
                except AttributeError:
                    bkmrk_info['bkmrk_note'] = ''


            #stat_namenum_zip = [(dd_tag.get('class')[0], dd_tag.text) for dd_tag in story.find_all('dd')]
            #info['stats'].update({k:v for k, v in stat_namenum_zip})

            if search_type == "work":
                self.works.append(work_info)
            if search_type == "bookmark":
                self.works.append([work_info, bkmrk_info])

        print("length is  %d" % len(self.works))

    #Straight from works.py
    def lookup_stat(self, story, class_name, default=None):
        dd_tag = story.find('dd', attrs={'class': class_name})
        if dd_tag is None:
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