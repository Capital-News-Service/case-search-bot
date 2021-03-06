# Maryland Case Search Slack Bot

A slack bot designed to give local crime reporters in Maryland breaking leads. 

This code scrapes the maryland case search database and sends slack messages when new interesting cases are found. 

Customize the config file to recieve updates for the county and crimes you are interested in.

Made by Jake Gluck [jagluck.github.io](jagluck.github.io).   
jakeagluck@gmail.com jagluck@terpmail.umd.edu

Please reach out with questions.

# Output

The bot will post into a designated slack channel as the crimes are entered into the database.

![Bot output example](https://github.com/Capital-News-Service/case-search-bot/blob/master/readme-images/example.jpg)

# Code

### Here is how it works at a high level

AWS Lambda instance - hosts and runs lambda_function.py - our python code that runs a search on http://casesearch.courts.state.md.us/casesearch/

AWS Cloud Events - triggers the lambda function to run every ten minutes

S3 Bucket - holds cases.json file containing the most recent searchs results to compare our current search to

### On run steps (what happens when the script runs)
1. Load in config data from key file. Happens at top of page.   
2. Get a authenitcated cookie to use for our searches. In getCookie.    
3. Do a search for results from last day that fit your search. In getPage.  
4. Collect these searches if they are the right case type. In getPage.  
5. Load in last search results. In compare_cases. (If there are no old results just run send_alert on all new cases, this is for the first ever run)  
6. Compare new and old search results, if they are different continue. In compare_cases.  
7. For new unique cases load individual case pages. In getSingleCase.  
8. Read page and gather information and charges list. We read the page here so we can minimize the number of page loads. In getSingleCase.  
9. If any charges are in our list of cjis codes build and send message to slack. In send_alert.  
10. Save new results as old. In compare_cases. 

# Config

### Here is what the config.json file should look like :

```
{
  "urls": [""],  
  "db_access_key" : "",  
  "db_secret_key" : "",  
  "db_bucket_name" : "",    
  "db_object_key" : "",  
  "codes" : ["1-0990", "1-1107", "2-0910", "2-0920", "1-0910", "1-0911", "1-0909", "1-1611", "1-0900", "1-0693", "1-0755", "1-1436", "1-0880", "1-0879", "1-0488", "1-1415","1-1420"],  
  "partyType" : "DEF",  
  "county" : "ANNE ARUNDEL COUNTY",  
  "site" : "CRIMINAL",  
  "company" : "N",  
  "courtSystem" : "B"
}
```

### Modify for your preferences

To run you will need to update the config file with your slack webhook endpoints
This is in an array if you would like to have multiple enpoints, but if it just one that is ok too, just leave it as an array with one element

(you need to set up a slack bot and get the endpoint url, it is relativly simple follow instuctions here)
https://api.slack.com/incoming-webhooks

Set up search add in configs for search that takes place here.   
http://casesearch.courts.state.md.us/casesearch/processDisclaimer.jis

Add your cjis codes for crimes that are intersting to you.  
https://mdcourts.gov/sites/default/files/import/district/charginglanguage_102018.pdf?pdf=Charging-Language

Here is the cjis codes what we are using:

Use a - not an _ in the cjis codes

```
MURDER-FIRST DEGREE : 1-0990  
MURDER-SECOND DEGREE : 1-1107  
ATT 1ST DEG. MURDER : 2-0910  
ATT 2ND DEG. MURDER : 2-0920  
MANSLAUGHTER : 1-0910  
INVOLUNTARY MANSLAUGHTER : 1-0911  
NEG MANSL-AUTO/BOAT, ETC : 1-0909  
CRIM NEG MANSLAUGHTER BY VEH/VESS : 1-1611  
NEG AUTO/BOAT HMCD-UNDER INFLU : 1-0900  
HOMICIDE-MV/VESSEL-IMPAIR ALC : 1-0693  
HOMICIDE-MV/VESSEL-DRUGS : 1-0755  
HOMICIDE-MV/VESSEL-CDS : 1-1436  
CDS DIST/DISPENSE- LG AMT : 1-0880  
CDS MANUF - LG AMT : 1-0879  
CDS-DRUG KINGPIN : 1-0488  
ASSAULT-FIRST DEGREE : 1-1420  
ASSAULT-SEC DEGREE : 1-1415  
```

# Setting up your own version

Here is how to set up the bot if you want to use the same deployment methods as I did. Of course the script will work on a personal server, just set it up to run with a cron job. 

If you want to use AWS, you will need to make your lamda instance (to run the script) and two s3 buckets (one to hold the most recent crimes and one to hold the zip files for the script because they will be too large for lambda). 

Configurations on aws can be tricky so I would reccomend using an ec2 server to package the code together into a zip. Follow our instuctions in [our guide](cns_aws_lambda_tutorial.pdf) to package the files and deploy them.  

If you want to run the files locally (without the s3 just comment out readDatabase() and updateDatabase() and instead use the read and save from a json file that is currently commented out. 

# Files

[lambda_function.py](lambda_function.py): This is the how the file must be formatted to be uploaded to AWS Lambda (Zipped in with dependencies).   

[script-sandbox.ipynb](script-sandbox.ipynb): Where I developed the code in a notebook. Useful to play around with.

cases.json: json file containing latest results. Should just start as an empty ```{}```. Hosted in an S3 bucket.

config.json: json file holding all of your needed keys and preferences.
