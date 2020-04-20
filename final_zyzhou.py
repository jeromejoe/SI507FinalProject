#################################
##### Final Project
##### Name: Ziyue Zhou
##### Uniqname: zyzhou
#################################

import sys
import json
import requests
import sqlite3
import time
from pathlib import Path
from bs4 import BeautifulSoup
import plotly.graph_objects as go

CACHE_FILENAME = "cache.json"
DB_NAME = "spot_crime.sqlite"
TYPE_LIST = ['Arrest', 'Arson', 'Assault', 'Burglary', 'Robbery',
             'Shooting', 'Theft', 'Vandalism', 'Other']

def open_cache():
    ''' Opens the cache file if it exists and loads the JSON into
    a dictionary.
    if the cache file doesn't exist, creates a new cache dictionary

    Parameters
    ----------
    None

    Returns
    -------
    The opened cache: dict
    '''
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict


def save_cache(cache_dict):
    ''' Saves the current state of the cache to disk

    Parameters
    ----------
    cache_dict: dict
        The dictionary to save

    Returns
    -------
    None
    '''
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME, "w")
    fw.write(dumped_json_cache)
    fw.close()


def build_state_url_dict():
    ''' Make a dictionary that maps state name to state page url from "www.spotcrime.com"
    Cache is used!

    Parameters
    ----------
    None

    Returns
    -------
    dict
        key is a state name and value is the url
    '''
    cache_dict = open_cache()
    base_url = "https://www.spotcrime.com"
    # check if base_url page is in cache
    if base_url in cache_dict.keys():
        print('Using cache')
        url_dict = cache_dict[base_url]
    else:
        print('Fetching')
        resp = requests.get(base_url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Fill in the dictionary
        url_dict = {}
        list_ul = soup.find('ul', class_='dropdown-menu')
        list_items = list_ul.find_all('li', recursive=False)
        for item in list_items:
            key = item.find('a').text.strip().lower()
            value = base_url + item.find('a')['href']
            url_dict[key] = value
        cache_dict[base_url] = url_dict
        save_cache(cache_dict)
    return url_dict


def build_city_url_dict(state_url):
    ''' Make a dictionary that maps each (city name + Crime Map/Most Wanted/Daily Crime Reports)
    to their page url
    Cache is used!

    Parameters
    ----------
    str
        state url

    Returns
    -------
    dict
        key is (city name + Crime Map/Most Wanted/Daily Crime Reports) and value is the url
    '''
    cache_dict = open_cache()
    base_url = "https://www.spotcrime.com"
    # check if state_url page is in cache
    if state_url in cache_dict.keys():
        print('Using cache')
        url_dict = cache_dict[state_url]
    else:
        print('Fetching')
        resp = requests.get(state_url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Fill in the dictionary
        url_dict = {}
        list_table = soup.find('table', class_="table table-condensed table-striped table-hover text-left")
        list_items = list_table.find_all('a')
        for item in list_items:
            if item.text.strip() is not None:
                key = item.text.strip().lower()
                value = base_url + item['href']
                url_dict[key] = value
        cache_dict[state_url] = url_dict
        save_cache(cache_dict)
    return url_dict


def build_daily_report_url_dict(city_url):
    ''' Make a dictionary that maps each city's crime date to their page url
    Cache is used!

    Parameters
    ----------
    str
        city url

    Returns
    -------
    dict
        key is city's crime date and value is specific date url
    '''
    cache_dict = open_cache()
    base_url = "https://www.spotcrime.com"
    # check if city_url page is in cache
    if city_url in cache_dict.keys():
        print('Using cache')
        url_dict = cache_dict[city_url]
    else:
        print('Fetching')
        resp = requests.get(city_url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Fill in the dictionary
        url_dict = {}
        list_div = soup.find('div', class_="main-content-column")
        list_items = list_div.find_all('li')
        for item in list_items:
            each_date = item.find('a')
            if each_date.text.strip() is not None:
                key = each_date.text.strip().lower()
                value = base_url + each_date['href']
                url_dict[key] = value
        cache_dict[city_url] = url_dict
        save_cache(cache_dict)
    return url_dict


def build_record_for_each_date(date_url, city, state):
    ''' Make a list that contains each date's crime records and write to database
    Cache is used!

    Parameters
    ----------
    str
        date url

    Returns
    -------
    list of dictionaries
        key is (type/date/address/link) and value is specific content
    '''
    cache_dict = open_cache()
    base_url = "https://www.spotcrime.com"
    # check if date_url page is in cache
    if date_url in cache_dict.keys():
        print('Using cache')
        crime_list = cache_dict[date_url]
    else:
        print('Fetching')
        resp = requests.get(date_url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Fill in the dictionary
        crime_list = []
        list_table = soup.find('table', class_="table table-condensed table-striped table-hover text-left")
        tr_s = list_table.find_all('tr')
        for tr in tr_s:
            td_s = tr.find_all('td')
            if len(td_s) == 5:
                record_dict = {}
                record_dict['type'] = td_s[1].string
                record_dict['date'] = td_s[2].string
                record_dict['address'] = td_s[3].string
                link = base_url + td_s[4].find('a')['href']
                record_dict['link'] = link
                crime_list.append(record_dict)
        time.sleep(1)
        # write the new records to database
        load_data(crime_list, city, state)
        # save to cache
        cache_dict[date_url] = crime_list
        save_cache(cache_dict)
    return crime_list


def create_db():
    '''Create the database and the "Type" table

    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    drop_types_sql = 'DROP TABLE IF EXISTS "Types"'
    drop_data_sql = 'DROP TABLE IF EXISTS "Data"'

    create_types_sql = '''
        CREATE TABLE IF NOT EXISTS "Types" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "Type" TEXT NOT NULL
        )
    '''

    create_data_sql = '''
        CREATE TABLE IF NOT EXISTS "Data" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "TypeId" INTEGER NOT NULL,
            "Date" TEXT NOT NULL,
            "Address" TEXT NOT NULL,
            "Link" TEXT NOT NULL,
            "City" TEXT NOT NULL,
            "State" TEXT NOT NULL
        )
    '''

    insert_types_sql = '''
        INSERT INTO Types VALUES (NULL, ?)
    '''

    cur.execute(drop_types_sql)
    cur.execute(drop_data_sql)
    cur.execute(create_types_sql)
    cur.execute(create_data_sql)
    for type in TYPE_LIST:
        cur.execute(insert_types_sql, [type])

    conn.commit()
    conn.close()


def load_data(record_list, city, state):
    '''Write data to database
    Parameters:
    -----------
    record_list
        a list of dictionaries
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    insert_data_sql = '''
        INSERT INTO Data
        VALUES (NULL, ?, ?, ?, ?, ?, ?)
    '''

    for record in record_list:
        idx = TYPE_LIST.index(record['type']) + 1
        cur.execute(insert_data_sql,
                    [idx,
                     record['date'],
                     record['address'],
                     record['link'],
                     city,
                     state])

    conn.commit()
    conn.close()


def dict_slice(adict, start, end):
    '''Return a sliced dictionary
    '''
    return {k: adict[k] for k in list(adict.keys())[start:end]}


def plot_city_num_crime_per_type(city):
    '''Plot numbers for each type of crime in certain city
    '''
    city = city.lower()
    num_crime = []
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    query = '''
        SELECT COUNT(*) FROM Data WHERE City=? AND TypeId=?
    '''
    for idx, type in enumerate(TYPE_LIST):
        cur.execute(query, [city, idx+1])
        num = list(cur)[0][0]
        num_crime.append(num)
    conn.close()
    # plot bar graph using plotly
    bar_data = go.Bar(x=TYPE_LIST, y=num_crime)
    basic_layout = go.Layout(title=f'Numbers for Each Type of Crime in {city}')
    fig = go.Figure(data=bar_data, layout=basic_layout)
    fig.show()


def plot_crime_trend_for_type(city, type_id):
    '''Plot a certain type of crime's trend in recent days
    '''
    city = city.lower()
    type_name = TYPE_LIST[type_id-1]
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # find different dates
    date_list = []
    date_list1 = []
    query = '''
        SELECT  DISTINCT substr(Date, 1, 8) FROM Data WHERE City=? AND TypeId=? 
    '''
    cur.execute(query,[city, type_id])
    for row in cur:
        date_list.append(row[0])
        date_1 = row[0] + '%'
        date_list1.append(date_1)
    date_list.reverse()
    date_list1.reverse()

    # count num for each date
    num_list = []
    query2 = '''
        SELECT COUNT(*) FROM Data WHERE City=? AND TypeId=? AND Date LIKE ?
    '''
    for date in date_list1:
        cur.execute(query2, [city, type_id, date])
        num = list(cur)[0][0]
        num_list.append(num)
    conn.close()

    # plot
    s_data = go.Scatter(x=date_list, y=num_list)
    s_layout = go.Layout(title=f'Trend for {type_name} in {city}')
    fig = go.Figure(data=s_data, layout=s_layout)
    fig.show()


def plot_sum_crime_for_cities(city_list):
    '''plot pie chart of sum of crime for all cities
    '''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # find sum
    sum_list = []
    city_name_list = []
    query = '''
        SELECT COUNT(*) FROM Data WHERE City=? 
    '''
    for city in city_list:
        city = city[0].lower()
        city_name_list.append(city)
        cur.execute(query, [city])
        num = list(cur)[0][0]
        sum_list.append(num)
    conn.close()
    # plot
    p_data = go.Pie(labels=city_name_list, values=sum_list)
    p_layout = go.Layout(title='Sum of Crime for All Cities')
    fig = go.Figure(data=p_data, layout=p_layout)
    fig.show()


def plot_type_crime_for_cities(city_list, type_id):
    '''plot pie chart of certain type of crime for all cities
    '''
    type_name = TYPE_LIST[type_id - 1]
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # find sum
    sum_list = []
    city_name_list = []
    query = '''
        SELECT COUNT(*) FROM Data WHERE City=? AND TypeId=?
    '''
    for city in city_list:
        city = city[0].lower()
        city_name_list.append(city)
        cur.execute(query, [city, type_id])
        num = list(cur)[0][0]
        sum_list.append(num)
    conn.close()
    # plot
    p_data = go.Pie(labels=city_name_list, values=sum_list)
    p_layout = go.Layout(title=f'Num of {type_name} for All Cities')
    fig = go.Figure(data=p_data, layout=p_layout)
    fig.show()


def print_menu():
    '''print user menu
    '''
    print()
    print('**********************************************************')
    print('Select one of the following options:')
    print('1. choose a city to view statistics for each type of crime')
    print('2. choose a city and a crime type to view its trend')
    print('3. view summary of all crime events for each city')
    print('4. choose a crime type to view its summary for each city')
    print('**********************************************************')


def print_city(city_list):
    '''print city list
    '''
    cities = []
    for city in city_list:
        cities.append(city[0])
    print("Available cities are:")
    print(cities)
    lowercase_cities = []
    for c in cities:
        lowercase_cities.append(c.lower())
    return lowercase_cities


def print_crime_type():
    '''print crime types
    '''
    type_list_with_idx = []
    for idx, type in enumerate(TYPE_LIST):
        type_with_idx = f'{idx+1}-' + type
        type_list_with_idx.append(type_with_idx)
    print("Crime types are:")
    print(type_list_with_idx)


if __name__ == "__main__":

    num_days = 5  # number of days to record crime data for each city
    # pre-defined cities (user may add other cities)
    selected_cities = [('Ann Arbor', 'Michigan'),
                       ('Detroit', 'Michigan'),
                       ('Flint', 'Michigan'),
                       ('San Diego', 'California'),
                       ('Los Angeles', 'California'),
                       ('Irvine', 'California'),
                       ('New York', 'New York'),
                       ('Austin', 'Texas'),
                       ('Miami', 'Florida'),
                       ('San Francisco', 'California')
                       ]

    ###########################################################################
    # Create database with selected cities

    # check if the database is already created
    database = Path(f'./{DB_NAME}')
    if not database.exists():
        create_db()

    print('Constructing database for selected cities...')
    state_dict = build_state_url_dict()
    for (city, state) in selected_cities:
        print('Adding ' + city + ', ' + state)
        city = city.lower()
        state = state.lower()
        if state in state_dict.keys():
            state_url = state_dict[state]
            city_dict = build_city_url_dict(state_url)
            city_spec = city + ' daily crime reports'
            if city_spec in city_dict.keys():
                city_url = city_dict[city_spec]
                city_daily_dict = build_daily_report_url_dict(city_url)
                if len(city_daily_dict) > num_days:
                    sliced_city_daily_dict = dict_slice(city_daily_dict, 0, num_days)
                    for date, date_url in sliced_city_daily_dict.items():
                        print('Recording ' + date)
                        build_record_for_each_date(date_url, city, state)
                else:
                    print('[Error] Crime data is not enough!')
            else:
                print('Wrong city name!')
        else:
            print('Wrong state name!')
    print('Database successfully constructed!\n')

    ###########################################################################
    # An interactive command line prompt to choose visualization options
    while True:
        print_menu()
        raw_input = input('Enter choice(1-4) or "exit": ')
        if raw_input.isnumeric():
            usr_choice = int(raw_input)
            if usr_choice == 1:
                while True:
                    cities = print_city(selected_cities)
                    city_input = input('Enter a city name: ')
                    if city_input.lower() in cities:
                        plot_city_num_crime_per_type(city_input.lower())
                        break
                    else:
                        print('[Error] City not exist! Try again!')

            elif usr_choice == 2:
                while True:
                    cities = print_city(selected_cities)
                    city_input = input('Enter a city name: ')
                    print_crime_type()
                    type_input = input('Enter a crime type\'s id: ')
                    if not type_input.isnumeric():
                        print('[Error] Type id must be a number! Try again!')
                        continue
                    type_id = int(type_input)
                    if city_input.lower() in cities and type_id >=1 and type_id <= 9:
                        city_name = city_input.lower()
                        plot_crime_trend_for_type(city_name, type_id)
                        break
                    else:
                        print('[Error] Invalid choice! Try again!')

            elif usr_choice == 3:
                plot_sum_crime_for_cities(selected_cities)

            elif usr_choice == 4:
                while True:
                    print_crime_type()
                    type_input = input('Enter a crime type\'s id: ')
                    if not type_input.isnumeric():
                        print('[Error] Type id must be a number! Try again!')
                        continue
                    type_id = int(type_input)
                    if type_id >= 1 and type_id <= 9:
                        plot_type_crime_for_cities(selected_cities, type_id)
                        break

            else:
                print('[Error] Invalid choice! Try again!')

        elif raw_input == "exit":
            print('Exiting program...')
            sys.exit()
        else:
            print('[Error] Choice must be 1, 2, 3, or 4!')
