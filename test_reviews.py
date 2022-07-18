from share.config import *
from SiteJabberScraper import SiteJabberScraper
import mariadb
import datetime
import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)

con = mariadb.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
cur = con.cursor()

scraper = SiteJabberScraper()

reviews = scraper.scrape_company_reviews("airseacontainers.com", save_to_db=False)
for i, review in enumerate(reviews):

    cur.execute("INSERT INTO test_review (id, review_title, page_number, date_inserted) VALUES (%s, %s, %s, %s)", (i, review.review_title, review.review_page_no, datetime.datetime.now()))

con.commit()

logging.info("Inserted " + str(len(reviews)) + " rows into db.")