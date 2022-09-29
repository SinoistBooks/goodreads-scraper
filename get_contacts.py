import argparse
import csv
import emailhunt
import os
import re
from datetime import datetime


def get_emails(txt):
    # get what looks like emails
    emails = re.findall('[\w\-\_]+@[\w\-\_]+\.[a-zA-Z]+', txt)
    return set(emails)


def get_websites(txt):
    # get what looks like websites
    sites = re.findall('([http|https]+:\/\/[\w\-\.\/]+)', txt)
    # exclude truncated urls
    sites = [site for site in sites if not site.endswith('...')]
    # exclude goodreads site
    sites = [site for site in sites if not re.match('.*goodreads.*', site)]
    return set(sites)


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

    print(
        f'\nScraping contacts for book: {profiles[0]["title"]} by {profiles[0]["authors"]}')
    return profiles


def scrape_contacts(driver, filepath):
    profiles = get_profiles_from_csv(filepath)

    counter = {'instagram': 0, 'youtube': 0, 'facebook': 0,
               'twitter': 0, 'personal': 0, 'profile_w_email': 0}

    # for each profile, get the websites and emails if any
    count = 0
    profile_contacts = []
    for profile in profiles:
        websites = []
        emails = []
        for k, v in profile.items():
            if k == 'url':
                continue

            websites.extend(get_websites(v))
            emails.extend(get_emails(v))

        websites = set(websites)  # remove duplicates
        profile['websites'] = ','.join(websites)

        personal_sites = []
        if websites:
            # note what type of sites they are and get the personal sites
            for site in websites:
                if re.match('.*instagram.*', site):
                    counter['instagram'] += 1
                elif re.match('.*youtube.*', site):
                    counter['youtube'] += 1
                elif re.match('.*facebook.*', site):
                    counter['facebook'] += 1
                elif re.match('.*twitter.*', site):
                    counter['twitter'] += 1
                else:
                    counter['personal'] += 1
                    personal_sites.append(site)

        if personal_sites:
            print(f'\nName: {profile["name"]} | {profile["url"]}')
            print(f'Sites: {personal_sites}')

            # if email not found on GR profile, look on their websites.
            # only do this for personal websites.
            for site in personal_sites:
                emails.extend(emailhunt.get_emails(site))

            emails = set(emails)  # remove duplicates
            print(f'\nFound emails: {", ".join(emails)}')
            profile['emails'] = ','.join(emails)
        else:
            print(
                f'\nNo personal website for user: {profile["name"]} | {profile["url"]}. Skip..')

        if len(emails) > 0:
            counter['profile_w_email'] += 1

        profile_contacts.append(profile)

        count += 1
        print(f'{count}...')

    print(f'\nTotal profiles with websites: {len(profile_contacts)}')
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

    args = parser.parse_args()

    # create output folder if does not exist
    if not os.path.exists(args.output):
        os.mkdir(args.output)

    csvfiles = []
    for item in os.listdir(args.input):
        if item.endswith('_profiles.csv'):
            csvfiles.append(item)

    driver = None

    today = datetime.today()
    outfile = os.path.join(
        args.output, f'contacts_{today.strftime("%Y%m%d")}.txt')

    for filename in csvfiles:
        filepath = os.path.join(args.input, filename)
        profile_w_contacts = scrape_contacts(driver, filepath)

        # 2 additional fields from this process (emails and websites)
        FIELDS = ['title', 'authors', 'name', 'emails', 'websites', 'user_type', 'url', 'rating',
                  'date', 'review', 'website', 'twitter', 'details', 'activity', 'about me',
                  'interests', 'favorite books', 'genre', 'influences', 'birthday', 'member since']
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
