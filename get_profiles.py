import argparse
import csv
import os
import time
from bs4 import BeautifulSoup
from datetime import datetime
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

PROFILE_TMP = 'profile_tmp.html'  # temp profile file for debugging

LOGIN_URL = 'https://www.goodreads.com/ap/signin?openid.assoc_handle=amzn_goodreads_web_na&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0'
LOGIN_FILE = 'gr_login.txt'


def login(driver):
    # read the login detail from the text file
    f = open(LOGIN_FILE, 'r')
    email, password = f.read().split()

    driver.get(LOGIN_URL)
    driver.find_element(By.XPATH, '//input[@name="email"]').send_keys(email)
    driver.find_element(
        By.XPATH, '//input[@name="password"]').send_keys(password)
    time.sleep(2)

    driver.find_element(By.XPATH, '//input[@id="signInSubmit"]').click()
    # you have 10 seconds to resolve the recaptcha if it comes up
    time.sleep(10)


def get_name(soup):
    try:
        return soup.find('h1', {'class': 'userProfileName'}).text.strip()
    except AttributeError:
        # this is an author
        h1 = soup.find('h1', {'class': 'authorName'})
        return h1.select('span')[0].text


def _truncate_more(item):
    if item.endswith('...more'):
        return item[:-7].strip()  # truncate the ...more
    return item


def get_info(soup):
    titles = soup.find_all('div', {'class': 'infoBoxRowTitle'})
    titles = [title.text.lower() for title in titles]
    items = soup.find_all('div', {'class': 'infoBoxRowItem'})
    items = [item.text.strip() for item in items]
    items = [_truncate_more(item) for item in items]
    return dict(zip(titles, items))


def get_info_author(soup):
    titles = soup.find_all('div', {'class': 'dataTitle'})
    titles = [title.text.lower() for title in titles]
    # can't get the value of 'born' as structure is borked, so remove
    if titles[0] == 'born':
        del titles[0]
    items = soup.find_all('div', {'class': 'dataItem'})
    items = [item.text.strip() for item in items]
    valid_items = []
    for item in items:
        if item.endswith('...more'):
            valid_items.append(item[:-7].strip())  # truncate the ...more
        else:
            valid_items.append(item)

    info = dict(zip(titles, valid_items))

    # get about author section
    about = soup.find('div', {'class': 'aboutAuthorInfo'})
    try:
        try:
            info['about me'] = about.select('span')[1].text
        except IndexError:
            # the section is too short so no "more" section
            info['about me'] = about.select('span')[0].text
    except Exception as e:
        pass  # likely that 'about me' does not exist

    return info


def get_profile(source, profile):
    soup = BeautifulSoup(source, 'lxml')

    if not profile.get('name'):
        name = get_name(soup)
        profile['name'] = name

    if soup.find('div', {'class': 'infoBoxRowTitle'}):
        info = get_info(soup)
    else:
        info = get_info_author(soup)

    profile.update(info)

    return profile


def load_page(driver, url, wait_time=1):
    driver.get(url)
    time.sleep(wait_time)

    # for debugging, in case there's an error, we can look at the last profile
    f = open(PROFILE_TMP, "w")
    f.write(driver.page_source)
    f.close()


def scrape_profiles(driver, reviews_file, max):
    ''' 
    reviews_file: the csv file output from get_reviews.py 
    max: max profiles to scrape
    '''
    reviews = []
    title = None
    with open(reviews_file, 'r') as csvfile:
        reader = csv.reader(csvfile)
        i = 0
        for row in reader:
            if i == 0:  # first row is the header
                assert row[0] == 'title'
                headers = row
            else:
                # convert list to dictionary with headers as keys
                review = {}
                j = 0
                for header in headers:
                    review[header] = row[j]
                    j += 1
                reviews.append(review)
            i += 1

    print(
        f'\nScraping profiles for book: {reviews[0]["title"]} by {reviews[0]["authors"]}')

    profiles = []
    for i, review in enumerate(reviews):
        url = review['url']
        print(f' Scraping profile #{i+1}: ' + url)

        # copy the review data info to the profile
        profile = review

        load_page(driver, url)

        try:
            profile = get_profile(driver.page_source, profile)
        except Exception as e:  # didn't get the page properly
            print(e)
            print(f'Failed to load profile #{i}, try again..')

            load_page(driver, url, 1.5)  # load page again and wait longer
            try:
                profile = get_profile(driver.page_source, profile)
            except Exception as e:
                # if failed again, skip
                print(e)
                print(f'Failed to load profile #{i} the second time. Skip..')
                continue

        profiles.append(profile)
        if max > 0 and len(profiles) >= max:
            break

    return profiles


def main():
    start_time = datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default='stage1_reviews',
                        help='Input directory containing reviews from get_reviews.py')
    parser.add_argument('--output', type=str, default='stage2_profiles',
                        help='Output directory')
    parser.add_argument('-d', '--dryrun', action='store_true', help='Dry run')

    args = parser.parse_args()

    # create output folder if does not exist
    if not os.path.exists(args.output):
        os.mkdir(args.output)

    csvfiles = []
    for item in os.listdir(args.input):
        if item.endswith('_reviews.csv'):
            csvfiles.append(item)

    options = Options()
    ua = UserAgent()
    userAgent = ua.random
    print(userAgent)
    options.add_argument(f'user-agent={userAgent}')

    driver = webdriver.Chrome(options=options, service=Service(
        ChromeDriverManager().install()))
    login(driver)  # login to GR (needed to get the profiles)

    total_profiles = 0
    for filename in csvfiles:
        if args.dryrun:
            print(f'Scraping profiles from {filename}..')
            continue

        reviews_file = os.path.join(args.input, filename)
        profiles = scrape_profiles(driver, reviews_file, args.max)
        total_profiles += len(profiles)

        outfile = os.path.join(
            args.output, filename.replace('_reviews', '_profiles'))

        FIELDS = ['title', 'authors', 'name', 'user_type', 'url', 'rating', 'date', 'review', 'website',
                  'twitter', 'details', 'activity', 'about me', 'interests', 'favorite books',
                  'genre', 'influences', 'birthday', 'member since']
        with open(outfile, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(profiles)
        print(
            f'\n🎉 Profiles scraped for f{filename}. Total: {len(profiles)} profiles 🎉')

    print(
        f'\n🎉 Success! All profiles scraped. Total: {len(csvfiles)} books and {total_profiles} profiles 🎉')
    print(f'\nGoodreads profiles have been saved to /{args.output}\n')
    print(f'Goodreads scraping run time = ⏰ ' +
          str(datetime.now() - start_time) + ' ⏰')

    # all good, do not need the temp profile anymore
    if os.path.exists(PROFILE_TMP):
        os.remove(PROFILE_TMP)


if __name__ == '__main__':
    main()
