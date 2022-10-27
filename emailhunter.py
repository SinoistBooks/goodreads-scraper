import html
import os
import re
import requests

from instaloader import Instaloader
from instaloader.structures import Profile


def get_domain(url):
    # get domain
    m = re.match('[http|https]+:\/\/([\w\-.]+)', url)
    domain = m.groups()[0]
    print(f'domain: {domain}')
    return domain


def get_emails(txt):
    # get what looks like email from a given text
    emails = set(re.findall('[\w\-\_\.]{2,}@[\w\-\_]{2,}(?:\.[a-zA-Z]{2,})+', txt))
    valid_emails = set()
    # remove "emails" that are images
    for email in emails:
        _, ext = os.path.splitext(email)
        if ext == '.jpg' or ext == '.png' or ext == '.gif':
            continue
        else:
            valid_emails.add(email)
    return valid_emails


def get_links(txt, include_incomplete=True):
    # get what looks like websites from a given text
    links = re.findall('([http|https]+:\/\/[\w\-]+\.{1,}[\w\-\/\=\?\.]+)', txt)
    # if no links found, get incomplete links (without http and with .com)
    if include_incomplete and not links:
        incomplete_links = re.findall('(www\.{1,}[\w\-\/\=\?\.]+)', txt)
        links.extend(incomplete_links)
    # exclude truncated urls (with ...)
    links = [link for link in links if not re.findall('\.{3}', link)]
    # exclude goodreads site
    links = [link for link in links if not re.match('.*goodreads.*', link)]
    return set(links)


def get_emails_links_by_url(url):
    try:
        r = requests.get(url, timeout=5)
        # print(f"status code: {r.status_code}")
    except requests.exceptions.ConnectionError:
        print(f'ERROR: Unable to reach url: {url}')
        return [], []
    except requests.exceptions.MissingSchema:
        # missing http:// so add and try again
        url = f'http://{url}'
        try:
            r = requests.get(url, timeout=5)
        except Exception as e:
            print(e)
            print(f'ERROR connecting to {url}. Skipping..')
            return [], []
    except Exception as e:
        print(e)
        print(f'ERROR connecting to {url}. Skipping..')
        return [], []

    # unescape html characters
    txt = html.unescape(r.text)

    # find what looks like email
    possible_emails = get_emails(txt)

    # blogger puts a trap, so remove the `blog` prefix and `.biz` suffix
    emails = []
    if re.match('.*blogger.com/profile.*', url):
        for email in possible_emails:
            m = re.match('blog([\w\-\_\.]{2,}@[\w\-\_]{2,}(?:\.[a-zA-Z]{2,})+).biz', email)
            if m:
                emails.append(m.groups()[0])
    else:
        emails = possible_emails

    if emails:
        return emails, []  # if there's email, no need to find links

    links = get_links(txt, include_incomplete=False)
    return emails, links


def hunt_emails(url):
    """Hunt emails by a given url.
    It will try to find emails from the url, and from likely links found on
    the first url.
    """
    print(f'\nHunt emails on URL: {url}')
    emails, links = get_emails_links_by_url(url)
    if len(emails) >= 1:
        # got email(s), no need to look further
        return emails

    # filter links and get those with potential
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
        elif re.match('.*review.*policy.*', link):
            valid_links.append(link)

    if valid_links:
        print('Potentially good links:')
        for link in valid_links:
            print(f'- {link}')
            emails, _ = get_emails_links_by_url(link)
            if len(emails) >= 1:
                # found emails!
                return emails

    return []


def get_insta_profile(url, loader):
    """
    loader: instance of Instaloader

    Return: insta profile (dict) and emails (list)
    """
    m = re.match('.*instagram.com\/([\w\.]+)', url)
    if not m:
        print(f'ERROR: Unable to get instagram username from: {url}')
        return None, []

    username = m.groups()[0]
    profile = Profile.from_username(loader.context, username)

    insta = {}
    insta['biography'] = profile.biography
    insta['external_url'] = profile.external_url
    insta['followers'] = profile.followers
    insta['following'] = profile.followees

    # check if there's email in bio
    emails = get_emails(profile.biography)
    if len(emails) >= 1:
        # got email(s), no need to look further
        return insta, emails

    # if not found, search in the external url
    if profile.external_url:
        emails, _ = get_emails_links_by_url(profile.external_url)

    return insta, emails
