import argparse
import csv
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

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
    driver.find_element(By.XPATH, '//input[@id="signInSubmit"]').click()


def get_name(soup):
    try:
        return soup.find('h1', {'class': 'userProfileName'}).text.strip()
    except AttributeError:
        # this is an author
        h1 = soup.find('h1', {'class': 'authorName'})
        return h1.select('span')[0].text


def get_info(soup):
    titles = soup.find_all('div', {'class': 'infoBoxRowTitle'})
    titles = [title.text.lower() for title in titles]
    items = soup.find_all('div', {'class': 'infoBoxRowItem'})
    items = [item.text.strip().rstrip('...more\n') for item in items]
    return dict(zip(titles, items))


def get_info_author(soup):
    titles = soup.find_all('div', {'class': 'dataTitle'})
    titles = [title.text.lower() for title in titles]
    # can't get the value of 'born' as structure is borked, so remove
    if titles[0] == 'born':
        del titles[0]
    items = soup.find_all('div', {'class': 'dataItem'})
    items = [item.text.strip().rstrip('...more\n') for item in items]

    info = dict(zip(titles, items))

    # get about author section
    about = soup.find('div', {'class': 'aboutAuthorInfo'})
    try:
        info['about me'] = about.select('span')[1].text
    except IndexError:
        # the section is too short so no "more" section
        info['about me'] = about.select('span')[0].text

    return info


def get_profile(source):
    soup = BeautifulSoup(source, 'lxml')
    profile = {}

    name = get_name(soup)
    profile['name'] = name

    if soup.find('div', {'class': 'infoBoxRowTitle'}):
        info = get_info(soup)
    else:
        info = get_info_author(soup)

    profile.update(info)

    return profile


def main():
    start_time = datetime.now()
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--profile_urls', type=str, default='gr_profiles.txt')
    parser.add_argument('--output_dir', type=str, default='profiles')

    args = parser.parse_args()

    urls = [line.strip()
            for line in open(args.profile_urls, 'r') if line.strip()]

    driver = webdriver.Chrome(ChromeDriverManager().install())
    login(driver)

    profiles = []
    for i, url in enumerate(urls):
        print(str(datetime.now()) + f': Scraping profile #{i}: ' + url)

        driver.get(url)
        time.sleep(0.5)

        # for debugging, in case there's an error, we can look at the last profile
        f = open("profile_tmp.html", "w")
        f.write(driver.page_source)
        f.close()

        profile = get_profile(driver.page_source)
        profile['source url'] = url  # add the source URL for reference

        profiles.append(profile)

    pro_file = os.path.join(args.output_dir, f"profiles.csv")
    FIELDS = ['name', 'source url', 'website', 'twitter', 'details', 'activity', 'about me', 'interests',
              'favorite books', 'url', 'genre', 'influences', 'birthday', 'member since']
    with open(pro_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(profiles)

    print(str(datetime.now()) + ' ' + script_name + f':\n\n')
    print(f'🎉 Success! All profiles scraped. 🎉\n\n')
    print(f'Goodreads profiles file has been output to /{args.output_dir}\n')
    print(f'Goodreads scraping run time = ⏰ ' +
          str(datetime.now() - start_time) + ' ⏰')


if __name__ == '__main__':
    main()
