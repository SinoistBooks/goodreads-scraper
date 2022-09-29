import html
import re
import requests


def get_domain(url):
    # get domain
    m = re.match('[http|https]+:\/\/([\w\-.]+)', url)
    domain = m.groups()[0]
    print(f'domain: {domain}')
    return domain


def search_emails_links(url):
    try:
        r = requests.get(url)
        # print(f"status code: {r.status_code}")
    except requests.exceptions.ConnectionError:
        print(f'ERROR: Unable to reach url: {url}')
        return [], []

    txt = html.unescape(r.text)

    # find what looks like email
    emails = re.findall('[\w\-\_]+@[\w\-\_]+\.[a-zA-Z]+', txt)
    if emails:
        return emails, []  # if there's email, no need to find links

    # find all links
    links = re.findall('[http|https]+:\/\/[\w\-\/.]+', txt)
    links = [link.rstrip('/') for link in links]
    links = set(links)
    # for link in links:
    #     print(link)

    print(f'Total {len(links)} links found.')

    return emails, links


def get_emails(url):
    print(f'\nSearch for emails from URL: {url}')
    emails, links = search_emails_links(url)
    if len(emails) >= 1:
        # got email(s), no need to look further
        return emails

    # filter links
    valid_links = []
    for link in links:
        # ignore the files
        if re.match('.*(\.[a-zA-Z]{2,})$', link):
            continue
        elif re.match('.*profile.*', link):
            valid_links.append(link)
        elif re.match('.*about.*', link):
            valid_links.append(link)
        elif re.match('.*contact.*', link):
            valid_links.append(link)

    if valid_links:
        print('Potentially good links:')
        for link in valid_links:
            print(f' {link}')
            emails, links = search_emails_links(link)
            if len(emails) >= 1:
                # found emails!
                return emails

    return []
