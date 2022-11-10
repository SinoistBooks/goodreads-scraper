import argparse
import os
import pandas as pd
import pycountry
import re
import spacy
import spacy_fastlang
from datetime import datetime


def add_lang(df):
    if 'lang' in df.columns:
        print("There is an existing 'lang' column in the table, so do nothing about it..")
        return df

    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("language_detector")

    reviews = df['review']
    total = len(reviews)

    languages = []
    i = 0
    for review in reviews:
        lang = ''
        if not pd.isna(review):
            review = str(review)  # explicitly cast to string if not NaN
            try:
                doc = nlp(review)
                lang = doc._.language
            except Exception as e:
                print(e)
        else:  # NaN
            review = ''

        languages.append(lang)
        i += 1
        print(f'{i}/{total}) [{lang}]: {review[:100]}', end='\r')

    # df['lang'] = languages # this adds to the end
    df.insert(8, 'lang', languages)
    return df


def add_age(df):
    # add "current" age or age at the time of scraping, and age when reading/reviewing
    if 'age' in df.columns:
        print("There is an existing 'age' column in the table, so do nothing about it..")
        return df

    print('Analysing ages...')

    cur_ages = []
    read_ages = []

    details = df['details']
    dates = df['date']

    i = 0
    for detail in details:
        date = dates.iat[i]
        i += 1

        if pd.isna(detail):
            cur_ages.append('')
            read_ages.append('')
            continue

        m = re.match('Age (\d+)', detail)
        if not m:
            cur_ages.append('')
            read_ages.append('')
            continue

        cur_age = int(m.groups()[0])

        # calculate the age when reviewing/reading the book
        try:
            read_age = cur_age - (datetime.today().year - datetime.strptime(date, '%B %d, %Y').year)
        except ValueError as e:
            read_age = cur_age - (datetime.today().year - datetime.strptime(date, '%m/%d/%Y').year)
        except Exception as e:
            read_age = cur_age

        print(
            f'Cur age={cur_age} Review date={date} Reading age={read_age}...',
            end='\r',
            flush=True,
        )
        cur_ages.append(cur_age)
        read_ages.append(read_age)

    df.insert(12, 'age', cur_ages)
    df.insert(13, 'read_age', read_ages)

    return df


def add_country(df):
    if 'country' in df.columns:
        print("There is an existing 'country' column in the table, so do nothing about it..")
        return df

    print('Analysing countries...')

    details = df['details']
    countries = []
    usstates = []

    i = 0
    for detail in details:
        if pd.isna(detail) or "hasn't added" in detail:
            countries.append('')
            usstates.append('')
            continue

        # country if exists, is on the last part
        parts = detail.split(',')
        parts = [p.strip() for p in parts]
        country = parts[-1]

        # not the right part
        if (
            country in ['Female', 'Male']
            or 'Age' in country
            or 'gender' in country.lower()
            or 'binary' in country.lower()
        ):
            countries.append('')
            usstates.append('')
            continue

        # numbers do not seem like anything
        if any(char.isdigit() for char in country):
            countries.append('')
            usstates.append('')
            continue

        # looks like the UK postcode
        us_state = ''
        if re.match('^([A-Za-z]{0,2}[\d]{1,2})$', country):
            country = 'United Kingdom'
        # looks like the UK postcode
        elif re.match('^([A-Za-z]{1,2}[\d]{1,2} [\d]{1,}[A-Za-z]{1,2})$', country):
            country = 'United Kingdom'
        # looks like US states
        elif re.match('^([A-Z]{2})$', country):
            us_state = country
            country = 'United States'
        # 2-part country name
        elif 'Republic of' in country:
            country = f'{parts[-1]} {parts[-2]}'

        usstates.append(us_state)

        # remove the 'The' suffix
        m = re.match('The ([\w\s]+)', country)
        if m:
            country = m.groups()[0]

        pycountries = sorted([c.name for c in pycountry.countries])
        if country in pycountries:
            countries.append(country)
            print(f'Detail: {detail} | country: {country}...', end='\r')
        else:
            # if not, do a country lookup
            try:
                potentials = pycountry.countries.search_fuzzy(country)
            except Exception as e:
                print(e)
                print(f'Failed lookup for country: [country].')
                countries.append('')
                usstates.append('')
                continue

            name = potentials[0].name
            parts = name.split(',')  # take the short name (the first part)
            if len(parts) >= 2:
                actual_country = parts[0]
            else:
                actual_country = name
            countries.append(actual_country)
            print(f'Detail: {detail} | country: {actual_country}...', end='\r')

    df.insert(14, 'country', countries)
    df.insert(15, 'US_state', usstates)

    return df


def analyse(csvfile, outputdir):
    """read csv file, analyse, and save a new file in the output dir with the extra info"""
    df = pd.read_csv(csvfile)
    print(f'Row, col: {df.shape}')

    df = add_lang(df)
    df = add_age(df)
    df = add_country(df)

    filename = os.path.basename(csvfile)
    name, ext = os.path.splitext(filename)
    outfile = os.path.join(outputdir, name.replace('_profiles', '_analysed') + ext)

    df.to_csv(outfile, index=False)
    print(f'Analysed file saved to: {outfile}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        type=str,
        help='Input directory containing the csv files',
    )
    args = parser.parse_args()

    outputdir = os.path.join(args.input, 'analysed')

    if not os.path.exists(outputdir):
        os.mkdir(outputdir)

    csvfiles = []
    for root, dirs, files in os.walk(args.input):
        for name in files:
            f = os.path.join(root, name)
            if f.endswith('.csv'):
                csvfiles.append(f)

    i = 0
    for csvfile in csvfiles:
        print(f'{i+1}) {csvfile}')
        analyse(csvfile, outputdir)
        i += 1


if __name__ == '__main__':
    main()
