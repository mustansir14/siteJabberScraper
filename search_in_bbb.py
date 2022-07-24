##########################################
# Coded by Mustansir Muzaffar
# mustansir2001@gmail.com
# +923333487952
##########################################

from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
import zipfile
from utility_files.DB import DB
from multiprocessing import Process
from share.config import *
import logging, argparse
from pyvirtualdisplay import Display
from webdriver_manager.chrome import ChromeDriverManager
import os
from sys import platform
import time

db = DB()
cur = db.cur
con = db.con

manifest_json = """
{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Chrome Proxy",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version":"22.0.0"
}
"""

background_js = """
var config = {
        mode: "fixed_servers",
        rules: {
        singleProxy: {
            scheme: "http",
            host: "%s",
            port: parseInt(%s)
        },
        bypassList: ["localhost"]
        }
    };

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "%s",
            password: "%s"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ['blocking']
);
""" % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)


def get_chromedriver(use_proxy=False):

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36")
    if use_proxy:
        pluginfile = 'temp/proxy_auth_plugin.zip'
        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
        chrome_options.add_extension(pluginfile)
    driver = webdriver.Chrome(options=chrome_options, executable_path=ChromeDriverManager().install())
    return driver

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def worker(companies, pid):

    global con
    global cur
    driver = get_chromedriver(True)

    for company in companies:

        if USE_MARIA_DB:
            company_id = company[0]
        else:
            company_id = company["company_id"]

        bbb_url = None
        
        try:
            try:
                driver.get(f"https://www.bbb.org/search?find_country=USA&find_text={company_id}&page=1")
            except:
                logging.error("Error loading page. Proxy might not be working")
            name_tags = driver.find_elements(By.CLASS_NAME, "MuiTypography-root.sc-yrgwp6-0.dDdJcz.MuiTypography-h4")
            for name_tag in name_tags:
                if "advertisement" in name_tag.text:
                    continue
                bbb_url = name_tag.find_element(By.TAG_NAME, "a").get_attribute("href")
                if "bbb" not in bbb_url:
                    bbb_url = None
                    continue
                break
            if bbb_url is None or bbb_url.strip() == "":
                raise Exception("Company not found on BBB")
            if USE_MARIA_DB:
                query = "update company set bbb_url = ? where company_id = ?"
            else:
                query = "update company set bbb_url = %s where company_id = %s"
            while True:
                try:
                    cur.execute(query, (bbb_url, company_id))
                    con.commit()
                    break
                except:
                    count += 1
                    if count == 3:
                        raise Exception(e)
                    logging.error(e)
                    logging.info("Waiting for 10 seconds and trying again...")
            logging.info("Process %s: BBB URL scraped and saved to DB for %s" % (str(pid), company_id))
            logging.info("Process %s: Scraping %s using BBB API..." % (str(pid), bbb_url))
            res = requests.get(f"{BBB_API_URL.rstrip('/')}/api/v1/scrape/company?id={bbb_url}&sync=1")
            logging.info(f"Process {str(pid)}: {res.json()}")
            try:
                if res.json()["success"] == False:
                    query = "update company set bbb_url = null where company_id = ?"
                    cur.execute(query, (company_id, ))
                    con.commit()
            except:
                pass
        except:
            logging.info("Process %s: Couldn't find company %s on BBB" % (str(pid), company_id))
        if USE_MARIA_DB:
            query = "update company set bbb_check_date = ? where company_id = ?"
        else:
            query = "update company set bbb_check_date = %s where company_id = %s"
    
        count = 0
        while True:
            try:
                cur.execute(query, (datetime.now(), company_id, ))
                con.commit()
                break
            except Exception as e:
                count += 1
                if count == 3:
                    raise Exception(e)
                logging.error(e)
                logging.info("Waiting for 10 seconds and trying again...")
                time.sleep(1)

    try:
        driver.quit()
    except:
        pass

def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in {'false', 'f', '0', 'no', 'n'}:
        return False
    elif value.lower() in {'true', 't', '1', 'yes', 'y'}:
        return True
    raise ValueError(f'{value} is not a valid boolean value')



if __name__ == "__main__":
    
    if os.name != "nt": # virtual display only on linux
        display = Display(visible=0, size=(1920, 1080))
        display.start()
    parser = argparse.ArgumentParser(description="Grab BBB URLs for SiteJabber Companies")
    parser.add_argument("--threads", nargs='?', type=int, default=1, help="No of threads to run. Default 1")
    parser.add_argument("--log_file", nargs='?', type=str, default=None, help="Path for log file. If not given, output will be printed on stdout.")
    args = parser.parse_args()
    
    # setup logging based on arguments
    if args.log_file and platform == "linux" or platform == "linux2":
        logging.basicConfig(filename=args.log_file, filemode='a',format='%(asctime)s Process ID %(process)d: %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
    elif platform == "linux" or platform == "linux2":
        logging.basicConfig(format='%(asctime)s Process ID %(process)d: %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
    elif args.log_file:
        logging.basicConfig(filename=args.log_file, filemode='a',format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
    else:
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
    
    chunksize = 5000
    counter = 0
    while True:
        
        count = 0
        while True:
            try:
                cur.execute(f"SELECT company_id from company where bbb_check_date is NULL or bbb_check_date <= date_sub(now(),interval 7 day ) limit {counter*chunksize}, {chunksize};")
                break
            except Exception as e:
                count += 1
                if count == 3:
                    raise Exception(e)
                logging.error(e)
                logging.info("Waiting for 10 seconds and trying again...")
                time.sleep(10)
        companies = cur.fetchall()

        if len(companies) == 0:
            logging.info("All companies searched!! Exiting now")
            break

        companies_chunks = split(companies, args.threads)

        processes = []
        for i, chunk in enumerate(companies_chunks):
            processes.append(Process(target=worker, args=(chunk, i+1,)))
            processes[-1].start()
        
        for process in processes:
            process.join()

        counter += 1
