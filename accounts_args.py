import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--account', help='Twitter account name')
args = parser.parse_args()

def account_info():
    if args.account:
        return args.account
    else:
        print('Specify an -a or --account argument')
        exit()