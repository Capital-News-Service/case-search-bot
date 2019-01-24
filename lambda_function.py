import boto
import boto.s3.connection
import boto3
import requests
import time
import json
import datetime
from datetime import timedelta
import pandas as pd
from bs4 import BeautifulSoup

def lambda_handler(event, context):

    #load in sensitive and configuration information from seperate key file
    keys={}
    with open("config.json","r") as f:
        config = json.loads(f.read())
       
        
    slack_urls = config["urls"]
    codes = config["codes"]
    partyType = config['partyType']
    county = config["county"]
    site = config['site']
    company = config['company']
    courtSystem = config["courtSystem"]

    #load in AWS bucket keys info
    db_access_key = config["db_access_key"]
    db_secret_key = config["db_secret_key"]
    bucket_name = config["db_bucket_name"] 
    object_key = config["db_object_key"] 

    # Creation of the actual interface, using authentication
    s3 = boto3.resource('s3',
             aws_access_key_id=db_access_key,
             aws_secret_access_key=db_secret_key)
    my_bucket = s3.Bucket(bucket_name)

    #Get an authenticated cookie for searches
    #before doing a request you will need to get a cookie to show yo have agreed to the disclamer, 
    #we will send a post request showing we have done this and return the cookie aquired for our later searches
    def getCookie():
        session = requests.Session()
        url = 'http://casesearch.courts.state.md.us/casesearch/'
        params = {
                'disclaimer' : 'Y',
                'action' : 'Continue'
        }
        r = session.post(url, data=params)

        cook = session.cookies['JSESSIONID']

        time.sleep(1)

        return "JSESSIONID=" + cook
        
    #search case search for single cases results by case number and return page
    def getSingleCase(cookie, caseId):

        headers = {'Cookie': cookie}

        params = {
            'caseId' : caseId,
            'action': 'Get Case',
            'locationCode': 'B'
        }

        url = 'http://casesearch.courts.state.md.us/casesearch/inquiryByCaseNum.jis'
        r = requests.post(url, params=params, headers=headers)
        return r.text

    #search casesearch for possible cases and return page
    def getPage(cookie, page):
        headers = {'Cookie': cookie}

        today = datetime.datetime.today().strftime('%m/%d/%Y')
        yesterday = (datetime.datetime.today() - timedelta(1)).strftime('%m/%d/%Y')
        params = {
            'd-16544-p': page,
            'lastName': '%', 
            'firstName' : '',
            'middleName': '',  
            'partyType': partyType,
            'site': site,
            'courtSystem': courtSystem,
            'countyName': county,
            'filingStart': yesterday,
            'filingEnd': today,
            'filingDate': '',
            'company': company,
            'action': 'Search',
        }

        url = 'http://casesearch.courts.state.md.us/casesearch/inquirySearch.jis'
        r = requests.post(url, params=params, headers=headers)
        time.sleep(1)
        return r.text

    #Get charges for one individual cases
    def getCharges(cookie, caseId):
        
        #data we will gather from individual case page
        charges = []
        cjiss = []
        text = getSingleCase(cookie, caseId)
        soup = BeautifulSoup(text)
        windows = soup.find_all("div", attrs={'class':'AltBodyWindow1'})
        #search through each window in the page. for now we just go through each td on the page and it works
        #this could be more efficient if we first chack to make sure the window contains the text before searching
        for window in windows:
            #find each table in current window
            tables = window.find_all("table")
            for table in tables:
                #find every tr in this table
                for row in table.findAll('tr'):
                    #for each tr search for each td and if it is a charge information window read it. 
                    # No other point on the page will contain this text
                    cell = row.findNext('td')
                    
                    #get cjis number for each charge
                    if cell.text == 'Charge No:':
                        target = cell.next_sibling
                        spans = target.find_all("span")
                        cjis = spans[2].text
                        cjiss.append(cjis)

                    #get charge description for each charge
                    if cell.text == 'Charge Description:':
                        target = cell.next_sibling
                        spans = target.find_all("span")
                        charge = spans[0].text              
                        charges.append(charge)
         
        # build dataset from gathered information and return it
        charge_data = {"charge": charges, "cjis" : cjiss}
        return charge_data
        
    #Run search and return information on all current cases  
    def getCases(cookie):
        
        end_reached = False
        page = 1
        
        #data we will collect
        caseIds = []
        links = []
        names = []
        types = []
        dates = []
        
        #keep scraping until you have reached the last page of results
        while (end_reached == False):
            
            text = getPage(cookie, page)
            soup = BeautifulSoup(text)
            
            #test if last page reached
            banner = soup.find("span", attrs={'class':'pagebanner'}).text
            splits = banner.split(" ", 6)
            if (splits[0] == splits[6][:-1]):
                #if last page has been reach set to false so we do not continue
                end_reached = True
            table = soup.find("table", attrs={'id':'row'})
            body = table.find("tbody")
            rows = body.find_all("tr")
            cases_on_page = len(rows)

            #for every charge listed in the results page, pull out data and make a dataframe
            for row in rows:
                tds = row.find_all("td")
                caseType = tds[5].text
                if caseType == "CRSCA" or caseType == "CROVA":
                    if (tds[0].find("a") != None):
                        #collect data for individual case here 
                        links.append("http://casesearch.courts.state.md.us/casesearch/" + tds[0].find("a")['href'])
                        caseId = tds[0].find("a").text
                        caseIds.append(caseId)
                        names.append(tds[1].text)
                        types.append(caseType)
                        dates.append(tds[7].text)

            #create dataframe from gathered info
            cases = pd.DataFrame(
                {'caseId': caseIds,
                 'name': names,
                 "type": types,
                 "date": dates,
                 "link" : links
                })
            
            print("Scraping Page " + str(page))
            page = page+1

        print("Done Scraping")
        return cases

    #Post message on slack if it is qualified. We check if the charges for each case are interesting here because it is time consuming
    def send_alert(row, cookie):
        charges = ""
        charge_data = getCharges(cookie, row["caseId"])
        
        #build message text if qualified
        
        #check if any of the charges are part of our list of interesting charges, 
        #from json file codes, a list of cjis codes of interesting crimes
        qualified = False
        for charge in charges:
            if charge in codes:
                qualified = True
        
        #if one of the cases cjis codes is in our list send the alert
        if qualified:
            
            #build the message text by looking through and adding charges to a string
            charge_num = 1
            for c,j in zip(charge_data['charge'],charge_data['cjis']):
                if charges == "":
                    charges = "\n1) " + c + " : " + j
                else:
                    charges = charges + " \n" + str(charge_num) + ") " + c + " : " + j
                charge_num = charge_num + 1

            #combine interesting info and charge list insto one string
            message = row['name'] + " - " + row['date'] + charges + " \n" + row['link'] +" \n-------------------------"
            
            #build post request to send to slack bot
            slack_data = {'text': message}
            headers={'Content-Type': 'application/json'}
            
            #sedn post to every slack we have set up, it will still work if it is just one
            for slack_url in slack_urls:
                url = slack_url
                print("send alert")
                #send post request with message text
                r = requests.post(url, json=slack_data, headers=headers)

    def readDatabase():

        with open('/tmp/cases.json','wb') as data:
            my_bucket.download_fileobj(object_key, data)

        old_cases={}
        with open("/tmp/cases.json","r") as f:
             text = f.read()
        
        old_cases = pd.read_json(text)
        
        return old_cases

    def updateDatabase(json_data):

        with open('/tmp/cases.json', 'wb') as outfile:
            outfile.write(json_data)

        with open('/tmp/cases.json', 'rb') as data:
            my_bucket.upload_fileobj(data, object_key)

    #Find new cases and post them on slack
    def compare_cases(new_cases, cookie):
        #load cases from last search
        old_cases = readDatabase()
    #     old_cases = pd.read_json('cases.json')
        
        print(str(len(new_cases)-len(old_cases)) + " New Cases")

        # basically just check if this is the first time you have run the search, 
        # make sure to create a empty cases.jsons file that is just {} before starting the bot
        if (len(old_cases) != 0):
            #see if any results are new and if they are post them on slack
            for index, row in new_cases.iterrows():
                if row["caseId"] not in old_cases['caseId'].unique():
                    send_alert(row, cookie)
        else:
            #if this is the first ever run, just send all cases
            for index, row in new_cases.iterrows():
                send_alert(row, cookie)

        #save new cases to be the old cases when the script runs again
        json_data = new_cases.to_json()
        updateDatabase(json_data.encode('utf-8'))
    #     new_cases.to_json('cases.json')
      
    #Run bot
    def runBot():
        cookie = getCookie()
        cases = getCases(cookie)
        compare_cases(cases, cookie)

    runBot()