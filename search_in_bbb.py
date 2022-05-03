from selenium import webdriver
from selenium.webdriver.common.by import By
import zipfile
from DB import DB
from multiprocessing import Process
from config import *
import logging, argparse
from pyvirtualdisplay import Display
from webdriver_manager.chrome import ChromeDriverManager
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)

PROXY_HOST = '154.16.150.141'  # rotating proxy or host
PROXY_PORT = 45785 # port
PROXY_USER = 'Selmustansir2001' # username
PROXY_PASS = 'G0o6PkY' # password


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
        pluginfile = 'proxy_auth_plugin.zip'
        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
        chrome_options.add_extension(pluginfile)
    driver = webdriver.Chrome(options=chrome_options, executable_path=ChromeDriverManager().install())
    return driver

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def worker(companies, pid, skip_already_done, cur, con):

    driver = get_chromedriver(True)

    for company in companies:

        if USE_MARIA_DB:
            company_id = company[0]
            bbb_url = company[1]
        else:
            company_id = company["company_id"]
            bbb_url = company["bbb_url"]
        
        if skip_already_done and bbb_url is not None:
            continue
        try:
            try:
                driver.get(f"https://www.bbb.org/search?find_country=USA&find_text={company_id}&page=1")
            except:
                logging.error("Error loading page. Proxy might not be working")
            name_tags = driver.find_elements(By.CLASS_NAME, "MuiTypography-root.Name-sc-135gl8f-0.jPuzee.MuiTypography-h4")
            for name_tag in name_tags:
                if "advertisement" in name_tag.text:
                    continue
                bbb_url = name_tag.find_element(By.TAG_NAME, "a").get_attribute("href")
                break
            if bbb_url is None or bbb_url.strip() == "":
                raise Exception("Company not found on BBB")
            if USE_MARIA_DB:
                query = "update company set bbb_url = ? where company_id = ?"
            else:
                query = "update company set bbb_url = %s where company_id = %s"
            cur.execute(query, (bbb_url, company_id))
            con.commit()
            logging.info("Process %s: BBB URL scraped and saved to DB for %s" % (str(pid), company_id))
        except:
            if USE_MARIA_DB:
                query = "update company set bbb_url = '' where company_id = '?'"
            else:
                query = "update company set bbb_url = '' where company_id = %s"
            cur.execute(query, (company_id))
            con.commit()
            logging.info("Process %s: Couldn't find company %s on BBB" % (str(pid), company_id))

    del driver

def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in {'false', 'f', '0', 'no', 'n'}:
        return False
    elif value.lower() in {'true', 't', '1', 'yes', 'y'}:
        return True
    raise ValueError(f'{value} is not a valid boolean value')



if __name__ == "__main__":
    
    headless = True
    if headless:
        display = Display(visible=0, size=(1920, 1080))
        display.start()
    parser = argparse.ArgumentParser(description="Grab BBB URLs for SiteJabber Companies")
    parser.add_argument("--skip_already_done", nargs='?', type=str, default="True", help="Boolean variable to skip companies which are already done (Both found and not found). Default True.")
    parser.add_argument("--threads", nargs='?', type=int, default=1, help="No of threads to run. Default 1")
    args = parser.parse_args()
    
    db = DB()
    cur = db.cur
    con = db.con
    chunksize = 5000
    counter = 0
    while True:

        cur.execute(f"SELECT company_id, bbb_url from company limit {counter*chunksize}, {chunksize};")
        companies = cur.fetchall()

        if len(companies) == 0:
            break

        companies_chunks = split(companies, args.threads)

        processes = []
        for i, chunk in enumerate(companies_chunks):
            processes.append(Process(target=worker, args=(chunk, i+1, str_to_bool(args.skip_already_done), cur, con,)))
            processes[-1].start()
        
        for process in processes:
            process.join()

        counter += 1
