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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import geckodriver_autoinstaller
from webdriver_manager.chrome import ChromeDriverManager


REVIEWS_TEMP_FILE = "reviews_tmp.html"


def _go_to_all_reviews(driver):
    # scroll to at the end of the reviews to get the 'see all reviews' button
    SCROLL_PAUSE_TIME = 0.5
    i = 0
    while (True):
        # Scroll down to bottom
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

        # Scroll a bit up for the All reviews button
        height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script(f"window.scrollTo(0, {height - 2000});")

        # Wait to load page
        # print(f'Scroll {i}')
        time.sleep(SCROLL_PAUSE_TIME)
        i += 1
        if i > 10:
            # too many scrollings, seems to fail
            return False

        try:
            more_reviews_button = driver.find_element(
                By.XPATH, '//div[@class="lazyload-wrapper "]/div[@class="ReviewsList"]/div[4]/a')
        except NoSuchElementException:
            time.sleep(1)
            continue  # try again

        if more_reviews_button:
            try:
                more_reviews_button.click()
            except ElementClickInterceptedException:
                time.sleep(1)  # wait, scroll up and try again
                try:
                    driver.execute_script(
                        f"window.scrollTo(0, {height - 1000});")
                    more_reviews_button.click()
                except Exception as e:
                    print(e)
                    return False
            return True
    return False


def switch_reviews_mode(driver, url):
    """
    From the book page, go to the reviews page.
    On selenium, you cannot go direct to the reviews page. (Will get message: Are you lost?)
    """

    # the first load always has the pop up to register, so need to load again
    driver.get(url)
    time.sleep(0.5)

    i = 0
    while True:
        print(f'🚨 Could not go to all reviews page - likely a pop-up or old layout🚨\n🔄 Refreshing Goodreads site..')
        driver.get(url)
        time.sleep(0.5)

        if _go_to_all_reviews(driver):
            return True  # managed to go to all reviews page

        if i > 10:  # after X reloads, we can stop trying
            break
        i += 1

    return False


def load_reviews(driver, pages):
    # click the 'Show previous reviews' near the top
    driver.execute_script(f"window.scrollTo(0, 400);")
    time.sleep(1)
    driver.find_element(By.XPATH, '//span[@data-testid="loadPrev"]').click()
    print('Show previous reviews..')
    time.sleep(2)

    SCROLL_PAUSE_TIME = 1.5

    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    i = 0
    while True:

        new_height = driver.execute_script("return document.body.scrollHeight")
        # Scroll down to bottom
        driver.execute_script(f"window.scrollTo(0, {new_height / 2});")
        time.sleep(SCROLL_PAUSE_TIME)
        driver.execute_script(f"window.scrollTo(0, {new_height});")
        time.sleep(SCROLL_PAUSE_TIME)

        if new_height >= last_height:
            driver.execute_script(f"window.scrollTo(0, {new_height - 1000});")
            # wait a bit for the button to load
            time.sleep(SCROLL_PAUSE_TIME)

            try:
                btn = driver.find_element(
                    By.XPATH, '//span[@data-testid="loadMore"]')
            except NoSuchElementException:
                print("Seems to have got all reviews.")
                break  # finish. no more reviews.

            try:
                btn.click()
                time.sleep(SCROLL_PAUSE_TIME)
            except ElementClickInterceptedException:
                print('ERROR: ElementClickInterceptedException. Sleep then continue..')
                time.sleep(1)
                continue
            except Exception as e:
                print(e)
                print('ERROR clicking button. Continue anyway..')
                continue

            print(f'Load more reviews... {i}')
            if i >= pages - 1:
                print("Ok i'm done")
                break
            i += 1

        last_height = new_height


def get_title_authors(source):
    title = source.find('a', {'data-testid': 'title'}).text
    authors = source.find('div', {'class': 'ContributorLinksList'}).text
    return title, authors


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
    title, authors = get_title_authors(soup)

    nodes = soup.find_all('article', {'class': 'ReviewCard'})

    # Iterate through and parse the reviews.
    reviews = []
    for node in nodes:
        name, url = get_reviewer(node)
        utype = get_user_type(node)
        # print(f'Name: {name} ({utype}) - {url}')

        review = get_review(node)
        rating, date = get_date_rating(node)

        reviews.append({'title': title,
                        'authors': authors,
                        'name': name,
                        'user_type': utype,
                        'url': url,
                        'rating': rating,
                        'date': date,
                        'review': review,
                        })

    print(f'Total reviews: {len(reviews)}')

    return title, reviews


def main():

    start_time = datetime.now()
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', default=200,
                        help="the number of times of the reviews to load", type=int)
    parser.add_argument('--books', type=str, help="Text file containing gooreads book urls",
                        default="goodreads_books.txt")
    parser.add_argument('--output', type=str,
                        help="Output directory", default="reviews")
    parser.add_argument('--browser', type=str,
                        help="Browser to use", default="chrome")

    args = parser.parse_args()

    book_urls = [line.strip()
                 for line in open(args.books, 'r') if line.strip()]

    # Set up driver
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

    for i, url in enumerate(book_urls):
        try:
            if not switch_reviews_mode(driver, url):
                print('Not able to go to reviews page. Skipping this book..')
                continue

            try:
                load_reviews(driver, args.pages)
            except Exception as e:
                print(e)
                print('Error loading more reviews. Take whatever we have.')

            print(f'Scraping {url} ...')

            # Save the HTML page
            filename = os.path.join(args.output, REVIEWS_TEMP_FILE)
            f = open(filename, "w")
            f.write(driver.page_source)
            f.close()

            try:
                title, reviews = scrape_reviews(filename)
            except Exception:
                print(
                    f'Error parsing the HTML {filename}. Skipping this book..')
                continue

            if len(reviews) == 0:
                print(f"No review found for {title}.")
            else:
                # write the reviews to csv
                book_filename = title.replace(' ', '_').lower()
                reviews_file = os.path.join(
                    args.output, f"{book_filename}_reviews.csv")

                FIELDS = ['title', 'authors', 'name', 'user_type',
                          'url', 'rating', 'date', 'review']
                with open(reviews_file, 'w') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
                    writer.writeheader()
                    writer.writerows(reviews)

                print(f'Reviews have been saved to: {reviews_file}')

            # done with temp reviews file
            if os.path.exists(REVIEWS_TEMP_FILE):
                os.remove(REVIEWS_TEMP_FILE)

        except HTTPError:
            pass

    driver.quit()

    print(f'🎉 Success! All book reviews scraped. 🎉\n\n')
    print(f'Goodreads scraping run time = ⏰ ' +
          str(datetime.now() - start_time) + ' ⏰')


if __name__ == '__main__':
    main()
