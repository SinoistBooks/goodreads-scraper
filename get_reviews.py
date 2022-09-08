import argparse
import csv
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from urllib.error import HTTPError
from selenium.webdriver.common.by import By
import geckodriver_autoinstaller
from webdriver_manager.chrome import ChromeDriverManager


def switch_reviews_mode(driver, url):
    """
    From the book page, go to the reviews page.
    On selenium, you cannot go direct to the reviews page. (Will get message: Are you lost?)
    """
    try:
        # the first load always has the pop up to register
        driver.get(url)
        time.sleep(1)
        driver.find_element(By.LINK_TEXT, 'See all reviews and ratings')

    except NoSuchElementException:
        print(f'🚨 NoSuchElementException (Likely a pop-up)🚨\n🔄 Refreshing Goodreads site..')

        driver.get(url)
        SCROLL_PAUSE_TIME = 1

        # scroll to at the end of the reviews to get the 'see all reviews' button
        i = 0
        while (i <= 8):
            # Scroll down to bottom
            if i == 8:  # roughly 8x scroll you get to the bottom.
                # scroll up a bit so the button is visible.
                y = (i * 1750) - 1000
            else:
                y = i * 1750
            print(f'Scroll down {i}: {y}')
            driver.execute_script(f"window.scrollTo(0, {y});")

            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)
            i += 1

        # driver.find_element(By.LINK_TEXT, 'See all reviews and ratings').click()
        more_reviews_button = driver.find_element(
            By.XPATH, '//div[@class="lazyload-wrapper "]/div[@class="ReviewsList"]/div[4]/a')
        more_reviews_button.click()

        driver.execute_script(f"window.scrollTo(0, 400);")
        time.sleep(1)
        driver.find_element(
            By.XPATH, '//span[@data-testid="loadPrev"]').click()

    return True


def get_reviewer(node):
    for c in node.find('div', {'class': 'ReviewerProfile__name'}).children:
        return c.text, c['href']
    return '', ''


def get_review(node):
    content = node.find('section', {'class': 'ReviewText__content'})
    return content.div.div.span.text


def get_date_rating(node):
    row = node.find('section', {'class': 'ReviewCard__row'})
    rating_row = row.select('div > span')
    rating = None
    if rating_row:
        rating = rating_row[0]['aria-label']
    date = row.select('section > span')[0].a.text
    return rating, date


def get_user_type(node):
    meta = node.find('span', {'class': 'Text__author'})
    if meta:
        return meta.text.strip()
    return None


def scrape_reviews(filename):
    '''
    Scrape reviews from the HTML file
    '''
    f = open(filename, 'r')
    source = f.read()

    soup = BeautifulSoup(source, 'lxml')
    nodes = soup.find_all('article', {'class': 'ReviewCard'})

    # Iterate through and parse the reviews.
    reviews = []
    for node in nodes:
        name, url = get_reviewer(node)
        utype = get_user_type(node)
        # print(f'Name: {name} ({utype}) - {url}')

        review = get_review(node)
        rating, date = get_date_rating(node)

        reviews.append({'name': name,
                        'user_type': utype,
                        'url': url,
                        'rating': rating,
                        'date': date,
                        'review': review,
                        })

    print(f'Total reviews: {len(reviews)}')

    return reviews


def load_reviews(driver, pages):
    SCROLL_PAUSE_TIME = 1.5

    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    i = 0
    while True:
        # Scroll down to bottom
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            driver.execute_script(f"window.scrollTo(0, {new_height - 1000});")
            # wait a bit for the button to load
            time.sleep(1)

            btn = None
            while btn is None:
                btn = driver.find_element(
                    By.XPATH, '//span[@data-testid="loadMore"]')
                if not btn:
                    print("Load more button is not found, waiting for it to load..")
                time.sleep(1)

            try:
                btn.click()
            except ElementClickInterceptedException:
                print('ERROR: ElementClickInterceptedException. Sleep then continue..')
                time.sleep(1)
                continue
            except Exception as e:
                print(e)
                print('ERROR. Continue anyway..')
                continue

            print(f'Load more reviews... {i}')
            if i >= pages - 1:
                print("Ok i'm done")
                break
            i += 1

        last_height = new_height


def main():

    start_time = datetime.now()
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', default=None, type=int)
    parser.add_argument('--book_ids_path', type=str)
    parser.add_argument('--output_dir', type=str)
    parser.add_argument('--browser', type=str,
                        help="choose a browser", default="chrome")

    args = parser.parse_args()

    if not args.book_ids_path:
        parser.error(
            "\n\nPlease add the --book_ids_path flag and choose a filepath that contains Goodreads book IDs\n")
    if not args.output_dir:
        parser.error(
            "\n\nPlease add the --output_dir and choose a directory filepath to output your reviews\n")
    if not args.browser:
        parser.error(
            "\n\nPlease add the --browser flag and choose a browser: either Firefox or Chrome\n")

    book_ids = [line.strip() for line in open(
        args.book_ids_path, 'r') if line.strip()]

    # Set up driver
    if args.browser is not None:
        if args.browser.lower() == 'chrome':
            driver = webdriver.Chrome(ChromeDriverManager().install())
        elif args.browser.lower() == 'firefox':
            geckodriver_autoinstaller.install()
            driver = webdriver.Firefox()
       # Get an option to work with Google Colab
        elif args.browser.lower() == "colab":
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument('--no-sandbox')
            driver = webdriver.Chrome(
                '/usr/lib/chromium-browser/chromedriver', options=chrome_options)
        else:
            print('Please select a web browser: Chrome or Firefox')
    else:
        print('Please select a web browser: Chrome or Firefox')

    for i, book_id in enumerate(book_ids):
        try:
            url = 'https://www.goodreads.com/book/show/' + book_id
            switch_reviews_mode(driver, url)
            try:
                load_reviews(driver, args.pages)
            except Exception as e:
                print(e)
                print('ERROR loading more reviews. Take whatever we have.')

            print(str(datetime.now()) + ': Scraping ' + book_id + '...')

            # Save the HTML page
            filename = os.path.join(args.output_dir, f"reviews_{book_id}.html")
            f = open(filename, "w")
            f.write(driver.page_source)
            f.close()
            print(f"HTML saved: {filename}")

            reviews = scrape_reviews(filename)
            reviews_file = os.path.join(args.output_dir, f"reviews_{book_id}.csv")
            FIELDS = ['name', 'user_type', 'url', 'rating', 'date', 'review']
            with open(reviews_file, 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(reviews)

        except HTTPError:
            pass

    driver.quit()

    print(str(datetime.now()) + ' ' + script_name + f':\n\n')
    print(f'🎉 Success! All book reviews scraped. 🎉\n\n')
    print(f'Goodreads review files have been output to /{args.output_dir}\n')
    print(f'Goodreads scraping run time = ⏰ ' +
          str(datetime.now() - start_time) + ' ⏰')


if __name__ == '__main__':
    main()
