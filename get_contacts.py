import argparse
import csv
import emailhunter
import os
import re
from datetime import datetime
from instaloader import Instaloader

LOGIN_FILE = 'insta_login.txt'


def get_profiles_from_csv(filepath):
    profiles = []
    title = None
    with open(filepath, 'r') as csvfile:
        reader = csv.reader(csvfile)
        i = 0
        for row in reader:
            if i == 0:  # first row is the header
                assert row[0] == 'title'
                headers = row
            else:
                # convert list to dictionary with headers as keys
                profile = {}
                j = 0
                for header in headers:
                    profile[header] = row[j]
                    j += 1
                profiles.append(profile)
            i += 1

    title = profiles[0]["title"]
    authors = profiles[0]["authors"]
    print(
        f'\nScraping contacts for book: {title} by {authors}')
    return profiles, title, authors


def scrape_contacts(filepath, ig_loader=None):
    """ ig_loader: scrape instagram if there's loader instance. default to None/False, 
            as it often hits rate limit.
    """
    profiles, title, authors = get_profiles_from_csv(filepath)

    counter = {'instagram': 0, 'youtube': 0, 'facebook': 0,
               'twitter': 0, 'personal': 0, 'profile_w_email': 0}

    # for each profile, get the websites and emails if any
    count = 0
    profile_contacts = []
    for profile in profiles:
        count += 1
        print(f'\n#{count}')

        websites = []
        emails = []
        for k, v in profile.items():
            if k == 'url':
                continue

            websites.extend(emailhunter.get_links(v))
            emails.extend(emailhunter.get_emails(v))

        websites = set(websites)  # remove duplicates

        personal_sites = []
        if websites:
            # note what type of sites they are and get the personal sites
            for site in websites:
                if re.match('.*instagram.*', site):
                    counter['instagram'] += 1
                    personal_sites.append(site)
                elif re.match('.*youtube.*', site):
                    counter['youtube'] += 1
                elif re.match('.*facebook.*', site):
                    counter['facebook'] += 1
                elif re.match('.*twitter.*', site):
                    counter['twitter'] += 1
                else:
                    counter['personal'] += 1
                    personal_sites.append(site)

        print(f'Name: {profile["name"]} | {profile["url"]}')
        print(f'Sites: {", ".join(websites)}')

        insta_profile = None
        if personal_sites:
            # if email not found on GR profile, look on their websites.
            # only do this for personal websites and instagram.
            for site in personal_sites:
                if re.match('.*instagram.*', site):
                    if ig_loader:
                        try:
                            insta_profile, insta_emails = emailhunter.get_insta_profile(
                                site, ig_loader)
                        except Exception as e:
                            print(e)
                            print(f'ERROR in accessing IG: {site}. Skipping..')
                            continue

                        emails.extend(insta_emails)
                    else:
                        pass  #  not scraping IG
                else:
                    emails.extend(emailhunter.get_emails(site))

        # found extra info from instagram profile
        if insta_profile:
            # add the url found on instagram to the set of websites
            if insta_profile.get('external_url'):
                websites.add(insta_profile.get('external_url'))

            profile['insta_biography'] = insta_profile['biography']
            profile['insta_followers'] = insta_profile['followers']
            profile['insta_following'] = insta_profile['following']
            print(f"Instagram bio: {profile['insta_biography']}")
            print(
                f"Instagram stats: {profile['insta_followers']} followers | {profile['insta_following']} following")

        profile['websites'] = ','.join(websites)

        emails = set(emails)  # remove duplicates
        if len(emails) > 0:
            print(f'\nEmails: {", ".join(emails)}')
            counter['profile_w_email'] += 1
        else:
            print(f'No email found.')
        profile['emails'] = ','.join(emails)

        if len(profile['emails']) > 0 or len(profile['websites']) > 0:
            profile_contacts.append(profile)

    print(f'\nBook: {title} by {authors}')
    print(f'Total profiles with websites: {len(profile_contacts)}')
    print(
        f"instagram: {counter['instagram']} | youtube: {counter['youtube']} | facebook: {counter['facebook']} | twitter: {counter['twitter']} | personal: {counter['personal']}")
    print(
        f"From personal websites, the number of emails acquired: {counter['profile_w_email']}")

    return profile_contacts


def main():
    start_time = datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default='stage2_profiles',
                        help='Input directory containing reviews from get_reviews.py')
    parser.add_argument('--output', type=str, default='stage3_contacts',
                        help='Output directory')
    parser.add_argument('--ig', action='store_true',
                        help='Scrape instagram if set')

    args = parser.parse_args()

    # create output folder if does not exist
    if not os.path.exists(args.output):
        os.mkdir(args.output)

    csvfiles = []
    for item in os.listdir(args.input):
        if item.endswith('_profiles.csv'):
            csvfiles.append(item)

    today = datetime.today()
    outfile = os.path.join(
        args.output, f'contacts_{today.strftime("%Y%m%d")}.csv')

    ig_loader = None
    # create the instagram loader now so it can be reused for multiple sites
    if args.ig:
        # read insta login detail from the text file
        f = open(LOGIN_FILE, 'r')
        username, password = f.read().split()

        ig_loader = Instaloader()
        try:
            ig_loader.login(username, password)
        except Exception as e:
            print(e)

    profile_w_contacts = []
    for filename in csvfiles:
        filepath = os.path.join(args.input, filename)
        profiles_set = scrape_contacts(filepath, ig_loader)
        profile_w_contacts.extend(profiles_set)

    # 2 additional fields from this process (emails and websites)
    FIELDS = ['title', 'authors', 'name', 'emails', 'websites', 'insta_biography',
              'insta_followers', 'insta_following', 'user_type', 'url', 'rating', 'date', 'review',
              'website', 'twitter', 'details', 'activity', 'about me', 'interests',
              'favorite books', 'genre', 'influences', 'birthday', 'member since']
    with open(outfile, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(profile_w_contacts)

    print(
        f'\n🎉 Success! Contacts scraped. Total: {len(profile_w_contacts)} profiles with contacts 🎉')
    print(f'\nContacts have been saved to /{outfile}\n')
    print(f'Contacts scraping run time = ⏰ ' +
          str(datetime.now() - start_time) + ' ⏰')


if __name__ == '__main__':
    main()
