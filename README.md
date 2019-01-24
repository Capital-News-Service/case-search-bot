## This code scrapes the maryland case search database and send slack messages when new interesting cases are found. 
# To be ran on a schedule.

# Made by Jake Gluck jagluck@terpmail.umd.edu

# The script is hosted on an AWS Lambda instance
# The saved cases.json file is in an s3 bucket

# Here is how it works at a high level:

# On run
#Step 1) Load in config data from key file. Happens at top of page
#Step 2) Get a authenitcated cookie to use for our searches. In getCookie():
#Step 3) Do a search for results from last day that fit your search. In getPage(cookie, page):
#Step 4) Collect these searches if they are the right case type. In getPage(cookie, page):
#Step 5) Load in last search results. In compare_cases(new_cases, cookie):
#Step 6) Compare new and old search results, if they are different continue. In compare_cases(new_cases, cookie):
#Step 7) For new unique cases load individual case pages. In getSingleCase(cookie, caseId):
#Step 8) Read page and gather information and charges list. We read the page here so we can minimize the number of page loads. In getSingleCase(cookie, caseId):
#Step 9) If any charges are in our list of cjis codes build and send message to slack. In send_alert(row, cookie):
#Step 10) Save new results as old. In compare_cases(new_cases, cookie):

Here is what the condfig.json file should look like :

Modify for your preferences.

{"urls": [""],
"db_access_key" : "",
"db_secret_key" : "",
"db_bucket_name" : "",  
"db_object_key" : "",
"codes" : ["1_0990", "1_1107", "2_0910", "2_0920", "1_0910", "1_0911", "1_0909", "1_1611", "1_0900", "1_0693", "1_0755", "1_1436", "1_0880", "1_0879", "_0488", "1-1415","1-1420"],
"partyType" : "DEF",
"county" : "ANNE ARUNDEL COUNTY",
"site" : "CRIMINAL",
"company" : "N",
"courtSystem" : "B"}

# To run you will need to update the config file with your slack webhook endpoints
# This is in an array if you would like to have multiple enpoints, but if it just one that is ok too, just leave it as an array with one element
# (you need to set up te slack bot and get endpoint, it is relativly simple follow instuctions here)
# https://api.slack.com/incoming-webhooks
# Set up search add in configs for search that takes place here 
# http://casesearch.courts.state.md.us/casesearch/processDisclaimer.jis

# if you want to use AWS, you will need to make your lamda instance and a bucket
# also follow our instuctions in cns_aws_lambda_tutorial.pdf to package the files and deploy them. 
# if you want to run them locally just comment out readDatabase() and updateDatabase() and instead use the read and save from a json file that is currently commented out 

# Ours looks like this:
# "partyType" : "DEF",
# "county" : "ANNE ARUNDEL COUNTY",
# "site" : "CRIMINAL",
# "company" : "N",
# "courtSystem" : "B"}

# Add your cjis codes for crimes that are intersting to you
# https://mdcourts.gov/sites/default/files/import/district/charginglanguage_102018.pdf?pdf=Charging-Language
