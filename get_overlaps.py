"""
This script:
- accepts 2 folder inputs containing csv files
- removes the duplicates from the first input
- for each of the first data: searches through the second data for the same person
- saves the result to overlaps.csv
"""
import argparse
import os
import pandas as pd


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
    print(f'Total set 1: {row, col}')
    df1 = df1.drop_duplicates(subset=['url'])
    row, col = df1.shape
    print(f'Unique set 1: {row, col}')
    person_count_df1 = row

    row, col = df2.shape
    print(f'Total set 2: {row, col}')
    # just count unique for df2, do not drop the data
    df2_tmp = df2.drop_duplicates(subset=['url'])
    row, col = df2_tmp.shape
    print(f'Unique set 2: {row, col}')
    person_count_df2 = row

    print()
    person_count = 0
    result = pd.DataFrame(columns=df1.columns.values)
    for idx, row1 in df1.iterrows():
        url = row1['url']
        print(f"{row1['name']} | {url}", end='\r')

        # check in the second df for any rows with the same url
        laps = df2.loc[df2['url'] == url]

        # TO REMOVE
        # if idx >= 10:
        #     break

        row, col = laps.shape
        if row == 0:  # no overlap
            continue

        # found overlaps
        laps = laps.drop_duplicates(subset=['title'])
        # laps = laps.reset_index(drop=True)

        # combine the data from df1 and df2 for this person
        person_count += 1
        rowdict = {k: v for k, v in zip(df.columns.values, row1)}
        result = pd.concat([result, pd.DataFrame(rowdict, index=['row1'])], ignore_index=True)
        result = pd.concat([result, laps], ignore_index=True)

    # print(result)

    outfile = 'overlaps.csv'
    result.to_csv(outfile, index=False)
    print(f'Overlapped reviews saved to: {outfile}')

    print(f'Unique persons from input1: {person_count_df1}')
    print(f'Unique persons from input2: {person_count_df2}')
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
