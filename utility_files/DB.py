from share.config import *
from typing import List
from utility_files.models import Company, Review
import datetime
if USE_MARIA_DB:
    import mariadb
else:
    import pymysql
import logging
import time
import requests

class DB:

    def __init__(self):
        self.host = DB_HOST
        self.user = DB_USER
        self.password = DB_PASSWORD
        self.db = DB_NAME
        if USE_MARIA_DB:
            self.con = mariadb.connect(host=self.host, user=self.user, password=self.password, db=self.db)
        else:
            self.con = pymysql.connect(host=self.host, user=self.user, password=self.password, db=self.db, cursorclass=pymysql.cursors.DictCursor)
        self.cur = self.con.cursor()
        
    def getDbCursor(self):
        if USE_MARIA_DB:
            return self.con.cursor(dictionary=True)
            
        return self.con.cursor()
    
    def queryArray(self,sql,args):
        cur = self.getDbCursor()
        
        cur.execute( sql,args )
        rows = cur.fetchall()

        cur.close()

        return rows

    def delete_company( self, company: Company ):
        try:
            self.cur.execute( "DELETE FROM `company` WHERE `company_id` = %s", ( company.id, ) )
        except Exception as e:
            logging.error( "delete_company error: " + str(e) )

    def insert_or_update_company(self, company : Company):
        while True:
            try:
                self.cur.execute("SELECT company_id from company where company_id = %s;", (company.id,))
                if len(self.cur.fetchall()) == 1:
                    sql = """UPDATE company set company_name = %s, url = %s, logo = %s, category1 = %s, category2 = %s, category3 = %s, email = %s, 
                    phone = %s, street_address1 = %s, street_address2 = %s, city = %s, state = %s, zip_code = %s, country = %s, wikipedia_url = %s,
                    facebook_url = %s, twitter_url = %s, linkedin_url = %s, youtube_url = %s, pinterest_url = %s, instagram_url = %s, date_updated = %s,
                    status = %s, log = %s, description = %s where company_id = %s"""
                    args = (company.name, company.url, company.logo, company.category1, 
                    company.category2, company.category3, company.email, company.phone, company.street_address1, company.street_address2, 
                    company.city, company.state, company.zip_code, company.country, company.wikipedia_url, company.facebook_url, company.twitter_url,
                    company.linkedin_url, company.youtube_url, company.pinterest_url, company.instagram_url, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    company.status, company.log, company.description, company.id)
                    success_statement = "Company " + company.id + " details updated successfully!"
                else:
                    sql = """INSERT INTO company (company_id, company_name, url, logo, category1, category2, category3, email, 
                    phone, street_address1, street_address2, city, state, zip_code, country, wikipedia_url,
                    facebook_url, twitter_url, linkedin_url, youtube_url, pinterest_url, instagram_url, date_created, date_updated,
                    status, log, description) VALUES (""" + "%s, " * 26 + "%s);"
                    args = (company.id, company.name, company.url, company.logo, company.category1, 
                    company.category2, company.category3, company.email, company.phone, company.street_address1, company.street_address2, 
                    company.city, company.state, company.zip_code, company.country, company.wikipedia_url, company.facebook_url, company.twitter_url,
                    company.linkedin_url, company.youtube_url, company.pinterest_url, company.instagram_url, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), company.status, company.log, company.description)
                    success_statement = "Company " + company.id + " details added to DB successfully!"
                self.cur.execute(sql, args)
                self.con.commit()
                logging.info(success_statement)
                break
            except Exception as e:
                logging.error(e)
                for i in range(3):
                    logging.info("Reconnecting after 10 seconds")
                    time.sleep(10)
                    try:
                        if USE_MARIA_DB:
                            self.con = mariadb.connect(host=self.host, user=self.user, password=self.password, db=self.db)
                        else:
                            self.con = pymysql.connect(host=self.host, user=self.user, password=self.password, db=self.db, cursorclass=pymysql.cursors.DictCursor)
                        success = True
                        self.cur = self.con.cursor()
                        break
                    except Exception as e:
                        logging.error(e)
                        success = False
                if not success:
                    raise Exception(e)


    def insert_or_update_reviews(self, reviews : List[Review], page=None):
        
        while True:
            try:
                for review in reviews:
                    if review.status == None:
                        review.status = "success"
                    self.cur.execute("SELECT review_id from review where company_id = %s and review_date = %s and username = %s;", (review.company_id, review.date, review.username))
                    fetched_results = self.cur.fetchall()
                    review_id = None
                    if len(fetched_results) >= 1:
                        if USE_MARIA_DB:
                            review_id = fetched_results[0][0]
                        else:
                            review_id = fetched_results[0]["review_id"]
                        sql = """UPDATE review SET no_of_helpful_votes = %s, review_title = %s, review_text = %s, review_stars = %s, review_page_no = %s,
                        date_updated = %s , status = %s, log = %s where review_id = %s"""
                        args = (review.no_of_helpful_votes, review.review_title, review.review_text, review.review_stars, review.review_page_no,
                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), review.status, review.log, review_id)
                    else:    
                        sql = """INSERT INTO review (company_id, review_date, username, no_of_helpful_votes, review_title, review_text, review_stars, review_page_no,
                        date_created, date_updated, status, log) VALUES (""" + "%s, " * 11 + "%s);"
                        args = (review.company_id, review.date, review.username, review.no_of_helpful_votes, review.review_title, review.review_text, 
                        review.review_stars, review.review_page_no, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                        review.status, review.log)

                    self.cur.execute(sql, args)
                    if not review_id:
                        review_id = self.cur.lastrowid
                    
                    image_paths = []
                    for i, image in enumerate(review.images):
                        try:
                            res = requests.get(image)
                            filename = "file/review/" + str(review_id) + "_" + str(i) + ".jpg"
                            with open(filename, "wb") as f:
                                f.write(res.content)
                            image_paths.append(filename)
                        except Exception as e:
                            logging.error("Error downloading review image: " + image)
                            logging.error(e)
                    
                    if image_paths:
                        self.cur.execute("UPDATE review set images = %s where review_id = %s", (str(image_paths), review_id, ))

                if reviews:
                    self.con.commit()
                    if page:
                        logging.info("Company " + review.company_id + " page " + str(page) + " reviews added/updated to DB successfully!")
                    else:
                        logging.info("Company " + review.company_id + " reviews added/updated to DB successfully!")
                break
            
            except Exception as error:
                logging.error(error)
                for i in range(3):
                    logging.info("Reconnecting after 10 seconds")
                    time.sleep(10)
                    try:
                        if USE_MARIA_DB:
                            self.con = mariadb.connect(host=self.host, user=self.user, password=self.password, db=self.db)
                        else:
                            self.con = pymysql.connect(host=self.host, user=self.user, password=self.password, db=self.db, cursorclass=pymysql.cursors.DictCursor)
                        self.cur = self.con.cursor()
                        success = True
                        break
                    except Exception as e:
                        logging.error(e)
                        success = False
                if not success:
                    raise Exception(error)

    

    def __del__(self):
        self.con.close()

