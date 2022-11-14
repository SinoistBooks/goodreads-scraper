"""
This script:
- accepts 2 folder inputs containing csv files
- for each of the first data: searches through the second data for the same person
- for each person combine data from set 1 and 2 and order them by date
- saves the result to overlaps.csv
"""
import argparse
import os
import pandas as pd
from datetime import datetime


def get_overlaps(csvfiles1, csvfiles2, set1, set2):
    i = 0
    df1 = pd.DataFrame()
    for f in csvfiles1:
        df = pd.read_csv(f)
        row, col = df.shape
        print(f'{set1[:10]}: {i+1}) {f} {row, col}', end='\r')
        i += 1
        df1 = pd.concat([df1, df], ignore_index=True)

    i = 0
    df2 = pd.DataFrame()
    for f in csvfiles2:
        df = pd.read_csv(f)
        row, col = df.shape
        print(f'{set2[:10]}: {i+1}) {f} {row, col}', end='\r')
        i += 1
        df2 = pd.concat([df2, df], ignore_index=True)

    print()
    row, col = df1.shape
    print(f'Total reviews in {set1}: {row, col}')
    # just count unique profiles, do not drop the data
    df1_tmp = df1.drop_duplicates(subset=['url'])
    row, col = df1_tmp.shape
    print(f'Unique profiles in {set1}: {row, col}')
    person_count_df1 = row

    row, col = df2.shape
    print(f'Total reviews in {set2}: {row, col}')
    # just count unique profiles, do not drop the data
    df2_tmp = df2.drop_duplicates(subset=['url'])
    row, col = df2_tmp.shape
    print(f'Unique profiles in {set2}: {row, col}')
    person_count_df2 = row

    print()
    person_count = 0
    result = pd.DataFrame(columns=df1.columns.values)
    # insert 'set' column to indicate which set the review comes from
    result.insert(2, 'set', [])

    for idx, row1 in df1.iterrows():
        url = row1['url']
        print(f"{idx}/{df1.shape[0]}) {row1['name']} | {url}", end='\r')

        # check if the person is already included in the result data
        if url in result['url'].unique():
            continue  # continue if already included

        # check in the second df for any rows with the same url
        set2_laps = df2.loc[df2['url'] == url]
        row, col = set2_laps.shape
        if row == 0:  # no overlap
            continue

        # found overlaps
        set2_laps = set2_laps.drop_duplicates(subset=['title'])
        set2_laps = set2_laps.assign(set=set2)

        # now find this person in the first set
        set1_laps = df1.loc[df1['url'] == url]
        set1_laps = set1_laps.drop_duplicates(subset=['title'])
        set1_laps = set1_laps.assign(set=set1)

        # combine the data from df1 and df2 for this person
        person_df = pd.DataFrame(data=set1_laps)
        person_df = pd.concat([person_df, set2_laps], ignore_index=True)
        person_df['date'] = pd.to_datetime(person_df['date'])

        # sort by date from the earliest to the latest
        person_df = person_df.sort_values(by=['date'])

        # add the data to the total result
        result = pd.concat([result, person_df], ignore_index=True)

        person_count += 1

    print()

    today = datetime.today()
    outfile = f'overlaps_{today.strftime("%Y%m%d")}.csv'
    result.to_csv(outfile, index=False)
    print(f'Overlapped reviews saved to: {outfile}')

    print(f'Unique persons from {set1}: {person_count_df1}')
    print(f'Unique persons from {set2}: {person_count_df2}')
    print(
        f'Total overlapping persons: {person_count} | '
        f'{person_count/person_count_df1*100:.2f}% from {set1} | '
        f'{person_count/person_count_df2*100:.2f}% from {set2}'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input1',
        type=str,
        help='The first input directory containing the csv files',
    )
    parser.add_argument(
        '--input2',
        type=str,
        help='The second input directory containing the csv files',
    )
    args = parser.parse_args()

    csvfiles1 = []
    for root, dirs, files in os.walk(args.input1):
        for name in files:
            f = os.path.join(root, name)
            if f.endswith('.csv'):
                csvfiles1.append(f)

    csvfiles2 = []
    for root, dirs, files in os.walk(args.input2):
        for name in files:
            f = os.path.join(root, name)
            if f.endswith('.csv'):
                csvfiles2.append(f)

    get_overlaps(csvfiles1, csvfiles2, args.input1, args.input2)


if __name__ == '__main__':
    main()
