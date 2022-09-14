# AO3_ReaderResponse
This repo contains code I wrote as a research assistant on an upcoming project from Richard So (McGill University) and Aarthi Vadde (Duke University) applying reader response theory and social network analysis to fan fiction.

My job was to scrape all of the data used in the project and compile it into a dataset. The dataset is complex in structure, linking user data to content, and large in scale, comprising million of users, user actions, text metadatas, and full texts.

Data was sourced from [Archive Of Our Own](https://archiveofourown.org/), a large platform for sharing fan fictions. The vast majority of the code is my own, except the [work.py](https://github.com/Peter-Ball/AO3_ReaderResponse/blob/master/Scrape_3/works.py) file, which was sourced from Alex Chan's [AO3 python api](https://github.com/alexwlchan/ao3).

This code is meant for demonstration purposes only, and should not be expected to run out of the box, due to its old age and device-specific file structures. However, with some massaging, you can definitely get an AO3 scraper up and running with this code.

I complied the dataset in 3 separate scrapes.

## Scrape 1

The first goal was to get a list of all users of AO3. AO3 has a [search people](https://archiveofourown.org/people/search) function, which gives a list of users. The problem is, AO3's search functions only allow a maximum of 100,000 items returned. AO3 has more than 5 million users! So to get a list of *every* user of the site, we need to perform a number of searches on smaller criteria. The main search criteria available is fandom, so my strategy was to get a list of every fandom, then programatically perform a search for every user associated with every fandom. This would have the added effect of filtering out users who have never engaged in any content.\*

The first task was to compile a list of all fandoms, using [fandom_names.py](https://github.com/Peter-Ball/AO3_ReaderResponse/blob/master/Scrape_1/fandom_names.py). 

The scraper goes through all sub-categories of fandoms, including movies, novels, and TV shows, and scrapes the list of fandoms kept by AO3. A regular expression seeks out the number of works associated with each fandom and stores it in a dictionary keyed to the fandom name. 

Because of the vast number of fandoms, it is necessary to compress small fandoms under a single name in order to keep the number of searches tractable. we can thus loop over all fandoms with less works than fill one page of search results (20) and add their names together with an operator recognized by AO3 urls until the total number of works equals 20. These are added to the final dictionary of fandom names and work counts, which is stored in a pickle.

With this list of fandoms in hand, we can search for users in a tractable way. In the [user_ids.py](https://github.com/Peter-Ball/AO3_ReaderResponse/blob/master/Scrape_1/user_ids.py) file, the list of fandoms is cycled through, with each used as a parameter in a user search. For each search, I scrape the first page of results, and parse for the number of result pages. Then I iterate over every page and scrape, parsing and storing each entry in a dictionary (`users_sofar`). Because I am using a dictionary with usernames as keys, users who appear in multiple searches are only recorded once. For each user I store the number of works and the number of bookmarks. The final dictionary as stored as a pickle.

\* *NOTE: I have since realized that a more efficient system would have been to search through names alphabetically. Using the first character in every name would still result in over 100,000 results per letter, which probably discouraged me inintially. But using the expressions aa\*, ab\*, ac\* etc. would be specific enough to get under 100,000 results, while reducing the number of searches from many thousands to 1292 (36 alphanumeric characters squared). I could have then further subsampled for engagement. I certainly wish I had thought of this a year ago!*

## Scrape 2

My next task was to get the full metadata of each user. Whenever I scrape from AO3, I am very conscious of the load I put on their servers. This is a fan-funded, volunteer run website, and the absolute last thing I want to do is burden them with extra costs or bandwidth issues. Plus, scraping the full metadata and works of 5 million users takes a long time! So I suggested to my supervisors that we subsample 200,000 users for collecting basic metadata (user profile and list of works) and a subset of 30,000 users for collecting the full metadata (all bookmarks, gifts, comments -- basically every piece of information available on their public profile).

Scrape 2 focused on getting the user profile and list of works for the subset of 200,000 users.

With a random sample of 200,000 users in hand (named at the time, in classic research style, `user_sample2-1.pkl`), I scraped every user page, recording whatever public metadata was available on their front page (number of works, number of kudos, etc.) and then iterated through every page of works written by the user, collecting all metadata for each work. Each user was stored as an entry in a dictionary, with relevant metadata, plus each work was stored in a subdictionary with all metadata accessible from the search page.

For this scrape (and scrape 3) I was given access to Duke University's compute cluster. I got experience scheduling jobs with SLURM and collecting data asychronously, which was super interesting!

## Scrape 3

At this point we have the name of every user on the site, basic metadata on 200,000 of those users, and a list of their works with basic metadata. But my supervisors were particularly interested in how users engaged with *each other,* and how that related to the specific textual content of the fan fiction they wrote. To acomplish this, we needed not just the user profile and a list of their works, but also a record of every engagement they made with other users' fan fictions (bookmarks, gifted fics) and the full text of the works they wrote. I again recommended sub-sampling to reduce the impact of this scrape on AO3 servers -- 30,000 users were randomly sampled.

Most of the action happens in `fullprofilescrape.py`, where functions and classes stored in the other files in ./scrape_3 are coordinated to collect and store the samepled users' data. 

For each sampled user, I load their profile page, and begin collecting the full text of each work. I open each work, giving me access to its full metadata including all tags. Then I parse the full text, with each chapter stored separately. The work is stored as a dictionary with metadata and chapters. The works are compiled into a list for each user. Some users have hundreds of works, some have zero, and both cases need to be handled.

The users' bookmarks and the corresponding fic title and metadata are collected by paginating over all bookmarks and running the `get_bookmarks` function. The usernames of the authors of bookmarked fics are of particular interest.

The users' gifted works are also recorded. These are works that users write and then \"gift\" to others, sometimes friends, sometimes others they are paired with through secret santa activities and the like. These interactions are also recorded in the same style as bookmarks.

The end result is a list of dictionaries pertaining to users, each with the user metadata, works, bookmarks, and gifts. From this can be derived the network and engagement statistics my supervisors were looking for.

Whew!

## Takeaways

The project was huge in scope and had me brushing up again and again with scalability: what is easy at the level of a single user is unfathomably complex at the scale of an entire social platform. I had to write code that could run for hours without fail, and compile a useable dataset of millions of inter-related objects.

I am proud of the work I did to make my code robust. You will notice a lot of error handling in this code -- this is classic scraping stuff, most of the work is figuring out what can go wrong (with I/O stuff, pretty much everything) and then writing exception handling for it so you don't lose data. I learned a lot about error handling during this project -- you may notice in early scrapes the error handling is re-written for each request function, but by the time I wrote [`fullprofilescrape.py`](https://github.com/Peter-Ball/AO3_ReaderResponse/blob/master/Scrape_3/fullprofilescrape.py) I had consolidated all input-output handling into a wrapper function that can be easily re-used. I also made the code robust against complete shutdown by implementing a checkpoint system. Every so often, the program would take note of how many iterations it had done. If for any reason the entire program shut off, it could pick back up where it left off. My method was somewhat primitive, simply writing to a json every so often with relevant info, so I am curious how experienced programmers would handle this more elegantly.

I also learned a ton about asychronous processes using the Duke compute cluster. I scheduled hundreds of parallel jobs with SLURM, then coallated the results into a single dataset. I also experimented with the asynchronous IO libraries `asyncio` and `asynchttp`. I was able to apply concepts I learned in Operating Systems classes like pooling and scheduling to my own project -- so cool!

The main learning lesson of this project was that with a complex dataset like this, it is *incredibly* important to do a lot of design specification work with the client before scraping begins. The end result of all my work -- a list of dictionaries -- did the job in storing the info I had been asked to retrieve. But it was not conducive to network analysis, because works, users, and bookmarks were not separated but rather jumbled together into one rather simplistic data type. In retrospect, I should have taken an object-oriented approach, with works, users, bookmarks, etc. each having their own class and list of properties, which could then be easily and flexibly assembled into the nodes and edges of the social networks my supervisors were after. As it was, I had to do a lot of post-processing on the dictionaries to mold them into useable forms for my supervisors. This was done on a request-by-request basis and often involved hacky scripting, so the results are not on display here.

A big thanks to Richard and Aarthi for the chance to take ownership of such a big dataset, and to you for reading!
