from config import *
from wikipedia_company_scraper import WikipediaScraper
from article_generator import generate_article
import logging, argparse
from multiprocessing import Process
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
import warnings
warnings.filterwarnings("ignore")


def worker(companies, pid, skip_already_done, cur, con):

    scraper = WikipediaScraper()

    for company in companies:

        if USE_MARIA_DB:
            company_id = company[0]
            company_name = company[1]
            company_wiki_info = company[2]
        else:
            company_id = company["company_id"]
            company_name = company["company_name"]
            company_wiki_info = company["wiki_info"]
        
        if skip_already_done and company_wiki_info is not None:
            continue
        # try:
        company_json = scraper.scrape_company(company_name)
        company_json["article"] = generate_article(company_json)
        if USE_MARIA_DB:
            query = "update company set wiki_info = '%s' where company_id = '%s'"
        else:
            query = "update company set wiki_info = %s where company_id = %s"
        cur.execute(query, (str(company_json), company_id, ))
        con.commit()
        logging.info("Process %s: Wiki Info scraped and saved to DB for %s" % (str(pid), company_name))
        # except Exception:
            # if USE_MARIA_DB:
            #     query = "update company set wiki_info = '' where company_id = '%s'"
            # else:
            #     query = "update company set wiki_info = '' where company_id = %s"
            # cur.execute(query, (company_id))
            # con.commit()
            # logging.info("Process %s: Couldn't find company %s on Wikipedia" % (str(pid), company_name))
    
    del scraper

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in {'false', 'f', '0', 'no', 'n'}:
        return False
    elif value.lower() in {'true', 't', '1', 'yes', 'y'}:
        return True
    raise ValueError(f'{value} is not a valid boolean value')

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Grab Wikipedia Info for SiteJabber Companies")
    parser.add_argument("--skip_already_done", nargs='?', type=str, default="False", help="Boolean variable to skip companies which are already done (Both found and not found). Default False.")
    parser.add_argument("--threads", nargs='?', type=int, default=1, help="No of threads to run. Default 1")
    args = parser.parse_args()

    if USE_MARIA_DB:
        import mariadb
        con = mariadb.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    else:
        import pymysql
        con = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME, cursorclass=pymysql.cursors.DictCursor)

    cur = con.cursor()

    chunksize = 5000
    counter = 0
    while True:

        cur.execute(f"SELECT company_id, company_name, wiki_info from company limit {counter*chunksize}, {chunksize};")
        companies = cur.fetchall()

        if len(companies) == 0:
            break

        companies_chunks = split(companies, args.threads)

        processes = []
        for i, chunk in enumerate(companies_chunks):
            processes.append(Process(target=worker, args=(chunk, i+1, str_to_bool(args.skip_already_done), cur, con, )))
            processes[-1].start()
        
        for process in processes:
            process.join()

        counter += 1
