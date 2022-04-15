from config import *
from wikipedia_company_scraper import WikipediaScraper
import logging, argparse
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
import warnings
warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Grab Wikipedia Info for SiteJabber Companies")
parser.add_argument("--skip_already_done", nargs='?', type=bool, default=False, help="Boolean variable to skip companies which are already done (Both found and not found). Default False.")
args = parser.parse_args()

if USE_MARIA_DB:
    import mariadb
    con = mariadb.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
else:
    import pymysql
    con = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME, cursorclass=pymysql.cursors.DictCursor)

cur = con.cursor()

cur.execute("SELECT company_id, company_name, wiki_info from company;")
companies = cur.fetchall()

scraper = WikipediaScraper()

for company in companies:

    if args.skip_already_done and company["wiki_info"] is not None:
        continue
    try:
        company_json = scraper.scrape_company(company["company_name"])
        cur.execute("update company set wiki_info = %s where company_id = %s;", (str(company_json), company["company_id"]))
        con.commit()
        logging.info("Wiki Info scraped and saved to DB for " + company['company_name'])
    except Exception:
        cur.execute("update company set wiki_info = '' where company_id = %s;", (company["company_id"]))
        con.commit()
        logging.info("Couldn't find company %s on Wikipedia" % company["company_name"])
