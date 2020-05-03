#!python3

###
"""
Todo list:
- Scrape FB likes
"""
###

import bs4, requests, logging, re
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def get_MPS_details(url):

    res = requests.get('https://www.parliament.gov.sg/' + url)
    #logging.error('%s' % (url))
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, 'html.parser')

    ## Get raw text from page ##
    raw_text = soup.find_all(text=True)
    text_output = ''
    blacklist = [
            '[document]',
            'noscript',
            'header',
            'html',
            'meta',
            'head', 
            'input',
            'script',
            ]

    for t in raw_text:
        if t.parent.name not in blacklist:
            text_output += '{} '.format(t)

    
            
    # Grab the addresses of the MP's Meet-The-People Sessions

    addresses = soup.find_all(string=re.compile(r'Blk'))
    addresses = [address.strip() for address in addresses]

    num_of_MPSes = len(addresses)
    
    if len(addresses) < 3:
        addresses.extend(['N.A.']*(3-len(addresses)))
    

    # Grab the timings of the MP's Meet-The-People Sessions

    timings = []

    elem = soup.select('#ui-id-1 > div > div:nth-of-type(3) > p')
    if len(elem) != 0:
        timings.append(elem[0].text)
    else:
        pass

    elem2 = soup.select('#ui-id-3 > div > div:nth-of-type(3) > p')
    if len(elem2) != 0:  #there is a second MPS
        timings.append(elem2[0].text)
    else:
        pass

    elem3 = soup.select('#ui-id-5 > div > div:nth-of-type(3) > p')
    if len(elem3) != 0:  #there is a third MPS
        timings.append(elem3[0].text)
    else:
        pass

    if len(timings) < 3:
        timings.extend(['N.A.']*(3-len(timings)))


    # Extract MPs' birth year and party using regex

    birthyearRegex = re.compile(r'''
        (Birth:)([\s\n\r\t]+)(\d{4})    # e.g. Year of Birth: \n \n \r\n\t\t\t\t\t\t1978
        ''',re.VERBOSE)
    matched = birthyearRegex.findall(text_output)
    if len(matched) == 0:
        birth_year = 'N.A.'
    else:
        birth_year = matched[0][2]

    list_of_parties = pd.read_csv('Datasets/list-of-political-parties.csv')

    partyRegex = re.compile(r'''
        (Party:)([\W]+)([\w'’\s]+)(\r)    # E.g. Party: \n \n \r\n\t\t\t\t\t\tPeople's Action Party\r\n\t\t\t\t\t \n \n
        ''',re.VERBOSE)
    matched = partyRegex.findall(text_output)
    if len(matched) == 0:
        party = 'N.A.'
    else:
        party = matched[0][2].replace("’", "'").replace("‘", "'")     # Called the replace function to clean up weird formatting with some apostrophes
        # use party abbrieviations
        party = list_of_parties[list_of_parties['political_party'].str.contains(party)]['abbreviation'].values[0]
            
    return birth_year, party, addresses, timings, num_of_MPSes

def get_MP_details():

    Url = ('https://www.parliament.gov.sg/mps/list-of-current-mps/')
    res = requests.get(Url)
    soup = bs4.BeautifulSoup(res.text, 'html.parser')

    ## initialise lists ##
    url_list = []
    name_list = []
    constituency_list = []

    for elem in soup.find_all('div',{'class':'col-md-8 col-xs-12 mp-sort-name'}):
        link = elem.find('a',href=True)
        name = elem.text.strip()
        if link is None:
            link = 'N.A.'
        elif name is None:
            name = 'N.A.'
        url_list.append(link['href'])
        name_list.append(name)

    for elem in soup.find_all('div',{'class':'col-md-6 col-xs-11 mp-sort constituency'}):
        constituency = elem.text.strip()
        if constituency is None:
            constituency = 'N.A.'
        elif 'GRC' in constituency:
            constituency = constituency[:-4]     
        constituency_list.append(constituency)

    return name_list, constituency_list, url_list

def clean_up_timings(series):
    return series.apply(lambda timing : timing.split(':  ')[1] if timing !='N.A.' else timing)

def clean_up_name(name):

    if name[:3] == 'Mrs':
        #logging.error('%s' % (name[:3]))
        name = name[4:]
    elif name[:2] in ('Mr', 'Dr', 'Ms'):
        #logging.error('%s' % (name[:2]))
        name = name[3:]
    elif name[:4] == 'Miss':
        #logging.error('%s' % (name[:4]))
        name = name[5:]
    elif name[:5] == 'Er Dr':
        #logging.error('%s' % (name[:5]))
        name = name[6:]
    elif name[:13] == 'Assoc Prof Dr':
        #logging.error('%s' % (name[:13]))
        name = name[14:]
    elif name[:10] == 'Assoc Prof':
        name = name[11:]
    elif name[:4] == 'Prof':
        #logging.error('%s' % (name[:4]))
        name = name[5:]

    return name

def get_vote_count(constituency, main_data, election_results):
    if constituency == 'Nominated Member of Parliament' or pd.isnull(constituency):
        return None
    elif constituency == 'Non-Constituency Member of Parliament':
        filt = main_data['Constituency'] == 'Non-Constituency Member of Parliament'
        count = 0
        name = main_data[filt].index[count]
        count +=1
        ward = election_results[election_results['candidates'].str.contains(name)]['constituency'].values[0]
        filt2 = election_results['constituency'] == ward
        return election_results[filt2]['vote_count'].sort_values(ascending = False).values[1]
    else:
        filt = election_results['constituency'] == constituency
        return election_results[filt]['vote_count'].max()

def get_vote_percentage(constituency, main_data, election_results):
    if constituency == 'Nominated Member of Parliament' or pd.isnull(constituency):
        return None
    elif constituency == 'Non-Constituency Member of Parliament':
        filt = main_data['Constituency'] == 'Non-Constituency Member of Parliament'
        count = 0
        name = main_data[filt].index[count]
        count +=1
        ward = election_results[election_results['candidates'].str.contains(name)]['constituency'].values[0]
        filt2 = election_results['constituency'] == ward
        return election_results[filt2]['vote_percentage'].sort_values(ascending = False).values[1]
    else:
        filt = election_results['constituency'] == constituency
        return election_results[filt]['vote_percentage'].max()

def get_constituency_type(constituency, main_data, election_results):

    if constituency in ('Nominated Member of Parliament', 'Non-Constituency Member of Parliament') or pd.isnull(constituency):
        return None
    else:
        num_of_MPs = len(election_results[election_results['constituency'] == constituency]['candidates'].values[0].split(' | '))
        if num_of_MPs == 1:
            return 'SMC'
        else:
            return 'GRC'

def get_size_of_constituency(constituency, main_data, election_results):

    if constituency in ('Nominated Member of Parliament', 'Non-Constituency Member of Parliament') or pd.isnull(constituency):
        return None
    else:
        num_of_MPs = len(election_results[election_results['constituency'] == constituency]['candidates'].values[0].split(' | '))
        return int(num_of_MPs)

def main():

    election_results = pd.read_csv('Datasets/parliamentary-general-election-results-by-candidate.csv')
    filt = election_results['year'] == 2015
    results_2015 = election_results[filt]

    name_list, constituency_list, url_list = get_MP_details()

    addresses = []
    timings = []
    birth_years = []
    parties = []
    num_of_MPSes = []
        
    for url in url_list:
        birth_year, party, address, timing, num_of_MPS = get_MPS_details(url)
        addresses.append(address)
        timings.append(timing)
        birth_years.append(birth_year)
        parties.append(party)
        num_of_MPSes.append(num_of_MPS)
        
    df = pd.DataFrame(columns=[
        'Name',
        'Birth_Year',
        'Constituency',
        'Party',
        'MPS_1 Venue',
        'MPS_1 Timing',
        'MPS_2 Venue',
        'MPS_2 Timing',
        'MPS_3 Venue',
        'MPS_3 Timing',
        'Num_of_MPS',
        ])

    for i in range(len(name_list)):
        df.loc[len(df)] = [name_list[i],
                           birth_years[i],
                           constituency_list[i],
                           parties[i],
                           addresses[i][0],
                           timings[i][0],
                           addresses[i][1],
                           timings[i][1],
                           addresses[i][2],
                           timings[i][2],
                           num_of_MPSes[i]
                           ]

    ## Data Cleaning ##

    df['MPS_1 Timing'] = clean_up_timings(df['MPS_1 Timing'])
    df['MPS_2 Timing'] = clean_up_timings(df['MPS_2 Timing'])
    df['MPS_3 Timing'] = clean_up_timings(df['MPS_3 Timing'])
    df['Name'] = df['Name'].apply(clean_up_name)
    
    df.replace('N.A.',np.NaN, inplace = True)
    df.set_index('Name', inplace= True)

    ## Derivative / Additional Cols ##

    df['Vote_Count'] = df['Constituency'].apply(lambda constituency : get_vote_count(constituency, main_data = df, election_results = results_2015))
    df['Vote_Percentage'] = df['Constituency'].apply(lambda constituency: get_vote_percentage(constituency, main_data = df, election_results = results_2015))
    df['Constituency_Type'] = df['Constituency'].apply(lambda constituency: get_constituency_type(constituency, main_data = df, election_results = results_2015))
    df['Size_of_Constituency'] = df['Constituency'].apply(lambda constituency: get_size_of_constituency(constituency, main_data = df, election_results = results_2015))

    ## Print interesting stats ##

    print("The youngest MP is %s who was born in %s." % (df['Birth_Year'].dropna().astype(float).idxmax(), int(df['Birth_Year'].dropna().astype(float).max())))
    print("The oldest MP is %s who was born in %s." % (df['Birth_Year'].dropna().astype(float).idxmin(), int(df['Birth_Year'].dropna().astype(float).min())))

    ## Export to CSV ##

    try:
        df.to_csv('Singapore MPs dataset.csv')
    except:
        print('Unable to save dataset into .csv file')

if __name__ == '__main__':
    main()

