import requests
from coolname import generate_slug
""" This is a simple python script that randomly generates names and items for picks """

errors = 0
for i in range(10):
    try:
        url = 'https://www.humanish.ai?counter=0&prompt=cat%20in%20the%20' + generate_slug()
        response = requests.get(url)
        print(url)
        #print(response.text)
    except requests.exceptions.ConnectionError:
        """ This happens when there is a connectivity issue, such as being offline """
        raise Exception('Connectivity issue')

    if response.status_code != 200:
        """ This means something went wrong. """
        errors += 1
        raise Exception('POST request response is status {}'.format(response.status_code))

print("number of errors was " + str(errors))
