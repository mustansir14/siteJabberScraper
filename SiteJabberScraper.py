from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType
import time
from typing import List
from DB import DB
from models import Company, Review
import datetime
import requests
import os
import argparse
import json
import sys
import logging
from multiprocessing import Process, Queue
from sys import platform



class SiteJabberScraper():

    def __init__(self, chromedriver_path=None) -> None:
        options = Options()
        options.headless = True
        options.add_argument("window-size=1920,1080")
        options.add_argument("--log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument('--disable-dev-shm-usage')
        
        if os.name != "nt":
            # https://peter.sh/experiments/chromium-command-line-switches/
            
            options.add_argument('--disable-extensions');
            options.add_argument('--single-process'); # one process to take less memory
            options.add_argument('--renderer-process-limit=1'); # do not allow take more resources
            options.add_argument('--disable-crash-reporter'); # disable crash reporter process
            options.add_argument('--no-zygote'); # disable zygote process
        
        # cpu optimization
        options.add_argument('--enable-low-res-tiling');
        
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36")
        if chromedriver_path:
            self.driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)
        else:
            self.driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
        self.dealt_with_popup = False
        if not os.path.exists("file/logo/"):
            os.makedirs("file/logo")
        self.db = DB()


    def scrape_url(self, url, save_to_db=True, continue_from_last_page=False) -> Company:
        
        if "https://www.sitejabber.com/reviews/" not in url and "https://www.sitejabber.com/edit-business/" not in url:
            raise Exception("Invalid URL")

        company_id = url.strip("/").split("/")[-1]
        company = self.scrape_company_details(company_id, save_to_db)

        if company.status == "success":
            company.reviews = self.scrape_company_reviews(company_id, save_to_db, continue_from_last_page=continue_from_last_page)

        return company


    def scrape_company_details(self, company_id, save_to_db=True) -> Company:

        logging.info("Scraping Company Details for " + company_id)
        
        company = Company()
        
        company.id = company_id
        company.url = "https://www.sitejabber.com/reviews/" + company_id
        
        self.driver.get(company.url)
        
        # get description
        try:
            company.description = self.driver.find_element_by_class_name("url-business__description").get_attribute('innerText')
        except Exception as e:
            company.description = ""
            
        # fill empty fields via ld+json
        try:
            scripts = self.driver.find_elements_by_css_selector("script[type='application/ld+json']")
            for script in scripts:
                content = script.get_attribute("innerText").strip()
                content = json.loads( content )
                
                if content["@type"] is not None and content["@type"] == "Organization" and content["address"]:
                    addressData = content["address"]

                    if addressData["addressLocality"] is not None:
                        company.city = addressData["addressLocality"]

                    if addressData["addressRegion"] is not None:
                        company.state = addressData["addressRegion"]

                    if addressData["@type"] is not None and addressData["@type"] == "PostalAddress" and addressData["addressCountry"]:
                        company.country = addressData["addressCountry"]["name"]
            
        except Exception as e:
            logging.error( "Error parsing ld+json: " + str(e) )
        
        try:
            res = requests.get(self.driver.find_element_by_class_name("website-thumbnail__image.object-fit").get_attribute("src"))
            filename = "file/logo/" + company_id.replace("/", "_").replace(".", "_").replace("\\", "_") + ".jpg"
            with open(filename, "wb") as f:
                f.write(res.content)
            company.logo = filename
        except Exception as e:
            logging.error("Error in saving logo to disk. " + str(e))
            company.logo = ""
            
        edit_page_url = "https://www.sitejabber.com/edit-business/" + company.id
        self.driver.get(edit_page_url)
        
        time.sleep(1)
        
        try:
            company.name = self.driver.find_element_by_id("name").get_attribute("value")
            categories = self.driver.find_elements_by_class_name("suggest-categories__breadcrumb")
            company.category1 = company.category2 = company.category3 = ""
            if len(categories) > 0:
                company.category1 = categories[0].text.strip()
            if len(categories) > 1:
                company.category2 = categories[1].text.strip()
            if len(categories) > 2:
                company.category3 = categories[2].text.strip()
            company.email = self.driver.find_element_by_id("location-email").get_attribute("value")
            company.phone = ""
            wait_counter = 0
            while wait_counter < 5:
                try:
                    phone = self.driver.find_element_by_id("inpt_verification_phone").get_attribute("value").replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
                    if not phone.strip():
                        company.phone = ""
                        break 
                    country_code = Select(self.driver.find_element_by_id("inpt_verification_country")).first_selected_option.get_attribute("data-isd").replace("-", "")
                    company.phone =  country_code + phone 
                    break
                except:
                    time.sleep(1)
                    wait_counter += 1
            company.street_address1 = self.driver.find_element_by_id("location-street-address").get_attribute("value")
            company.street_address2 = self.driver.find_element_by_id("location-street-address-2").get_attribute("value")

            city = self.driver.find_element_by_id("location-city").get_attribute("value")
            if city and not company.city:
                company.city = city

            state = self.driver.find_element_by_id("location-state").get_attribute("value")
            state = company.state.replace( "non-us", "" )
            if state and not company.state:
                company.state = state

            company.zip_code = self.driver.find_element_by_id("location-postal-code").get_attribute("value")

            country = self.driver.find_element_by_id("location-country").get_attribute("value")
            if country:
                company.country = country

            company.wikipedia_url = self.driver.find_element_by_id("wikipedia-url").get_attribute("value")
            company.facebook_url = self.driver.find_element_by_id("facebook-url").get_attribute("value")
            company.twitter_url = self.driver.find_element_by_id("twitter-url").get_attribute("value")
            company.linkedin_url = self.driver.find_element_by_id("linkedin-url").get_attribute("value")
            company.youtube_url = self.driver.find_element_by_id("youtube-url").get_attribute("value")
            company.pinterest_url = self.driver.find_element_by_id("pinterest-url").get_attribute("value")
            company.instagram_url = self.driver.find_element_by_id("instagram-url").get_attribute("value")
            
            if company.zip_code and company.country and ( not company.state or not company.city ):
                zipDataUrl = "http://www.vcharges.com/get-zip.php?country=" + requests.utils.quote( company.country ) + "&zip=" + requests.utils.quote( company.zip_code ) + "&type=all&output=json"
                
                print(zipDataUrl)
                
                response = requests.get( zipDataUrl, timeout = 5 )
                if response.status_code == 200:
                    print(response.json())
                
                
        except Exception as e:
            company.name = company.id
            company.status = "error"
            company.log = "edit-business page error : " + str(e)

        if not company.status:
            company.status = "success"
            
        if save_to_db:
            if company.status == "success":
                self.db.insert_or_update_company( company )
            else:
                self.db.delete_company( company )
            
        return company


    def scrape_company_reviews(self, company_id, save_to_db=True, scrape_specific_review=None, continue_from_last_page=None) -> List[Review]:

        if scrape_specific_review:
            logging.info("Scraping review with id %s for %s" % (scrape_specific_review, company_id))
        else:
            logging.info("Scraping reviews for " + company_id)
        review_url = "https://www.sitejabber.com/reviews/" + company_id
        self.driver.get(review_url)
        
        if scrape_specific_review:
            self.db.cur.execute("SELECT username, review_date from review where review_id = %s", (scrape_specific_review))
            review_results = self.db.cur.fetchall()
            got_review = False

        last_page = None
        if continue_from_last_page:
            try:
                self.db.cur.execute("SELECT max(review_page_no) as page from review where company_id = %s", (company_id))
                last_page = int(self.db.cur.fetchall()[0]["page"])
                logging.info("Last scraped page: " + str(last_page))
                logging.info("Moving to page " + str(last_page+1) + "...")
            except:
                pass
        reviews = []
        page = 1
        while True:
            if not last_page or (last_page and page > last_page):
                page_reviews = []
                logging.info("Page " + str(page))
                if not self.dealt_with_popup:
                    try:
                        popup = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "ad-popup__dialog.ad-popup__widget")))
                        popup.find_element_by_class_name("ad-popup__widget__title_close").click()
                        self.dealt_with_popup = True
                    except:
                        pass
                    try:
                        self.driver.find_element_by_class_name("cookie-consent__close").click()
                    except:
                        pass
                review_tags = self.driver.find_elements_by_class_name("review")
                for review_tag in review_tags:
                    username = review_tag.find_element_by_class_name("review__author__name").text.strip()
                    if scrape_specific_review and username != review_results[0]["username"]:
                        continue
                    try:
                        helpful_count = int(review_tag.find_element_by_class_name("helpful__count").text.strip("()"))
                    except:
                        helpful_count = 0
                    review_contents = review_tag.find_elements_by_class_name("review__content")
                    for review_content in review_contents:
                        review = Review()
                        review.company_id = company_id
                        review.username = username
                        try:
                            date = review_content.find_element_by_class_name("review__date").text.strip().replace("st,", "").replace("nd,", "").replace("rd,", "").replace("th,", "")
                            review.date = datetime.datetime.strptime(date, "%B %d %Y").strftime('%Y-%m-%d')
                        except:
                            review.date = None
                            review.log += "Error while scraping/parsing date\n"
                            review.status = "error"
                        if scrape_specific_review and str(review.date) != str(review_results[0]["review_date"]):
                            continue
                        review.no_of_helpful_votes = helpful_count
                        try:
                            review.review_title = review_content.find_element_by_class_name("review__title__text").text.strip()
                        except:
                            review.review_title = ""
                            review.status = "error"
                            review.log += "error while scraping review title\n"
                        try:
                            review.review_text = review_content.find_element_by_class_name("review__text").find_element_by_tag_name("p").text.strip()
                        except:
                            review.review_text = ""
                        try:
                            review.review_stars = float(review_content.find_element_by_class_name("stars").get_attribute("title").split()[0])
                        except:
                            review.status = "error"
                            review.log += "error while scraping review stars\n"
                        review.review_page_no = page
                        reviews.append(review)
                        page_reviews.append(review)
                        if scrape_specific_review:
                            got_review = True
                            break

                if save_to_db and page_reviews:
                    self.db.insert_or_update_reviews(page_reviews, page=page)

                if scrape_specific_review and got_review:
                    break
            
            try:
                next_page = self.driver.find_element_by_class_name("pagination__next").find_element_by_class_name("pagination__button--enabled")

                scroll_to_center = """var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0); 
                                    var elementTop = arguments[0].getBoundingClientRect().top; 
                                    window.scrollBy(0, elementTop-(viewPortHeight/2));"""

                self.driver.execute_script(scroll_to_center, next_page)
                time.sleep(1)
                try:
                    next_page.click()
                except:
                    popup = self.driver.find_element_by_class_name("ad-popup__dialog.ad-popup__widget")
                    popup.find_element_by_class_name("ad-popup__widget__title_close").click()
                    self.dealt_with_popup = True
                    next_page.click()
                
                time.sleep(0.5)
                WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located((By.CLASS_NAME, "blockUI.blockOverlay")))
                time.sleep(1)
                page += 1

            
            except:
                break

        
            
        return reviews


    def bulk_scrape(self, get_urls_from_file=False, continue_from_last_scrape=False, skip_if_exists=False, no_of_threads=1):
 
        empty_file = False
        if get_urls_from_file:
            with open("category_urls.json", "r") as f:
                self.__total_categories_urls = json.load(f)

            if self.__total_categories_urls == {}:
                empty_file = True

        if not get_urls_from_file or empty_file:
            logging.info("Scraping Category URLs...")
            self.driver.get("https://www.sitejabber.com/categories")
            time.sleep(2)
            self.__collect_category_urls()
            with open("category_urls.json", "w") as f:
                json.dump(self.__total_categories_urls, f)

        if continue_from_last_scrape:
            if os.path.isfile("last_scrape_info.json"):
                with open("last_scrape_info.json", "r") as f:
                    last_scrape = json.load(f)
        
                last_company_url = last_scrape["url"]
                last_category = last_scrape["category"]
                category_flag = False
            else:
                logging.info("No backup file found. Scraping from beginning")
                category_flag = True
                last_scrape = {}
        else:
            category_flag = True
            last_scrape = {}
            
        url_flag = category_flag
        
        for category, url in self.__total_categories_urls.items():
            if not category_flag and last_category == category:
                category_flag = True
            if category_flag:
                logging.info("Scraping Category URLS...")
                company_urls = self.__scrape_company_urls_from_category(url)
                urls_to_scrape = Queue()
                for company_url in company_urls:
                    if not url_flag and company_url == last_company_url:
                        url_flag = True
                        continue
                    if url_flag:
                        if skip_if_exists:
                            self.db.cur.execute("SELECT * from company where url = %s;", (company_url))
                            if len(self.db.cur.fetchall()) > 0:
                                continue

                        urls_to_scrape.put(company_url)
                          
                if platform == "linux" or platform == "linux2":
                    processes = []
                    for i in range(no_of_threads):
                        processes.append(Process(target=self.scrape_urls_from_queue, args=(urls_to_scrape, category, continue_from_last_scrape)))
                        processes[i].start()

                    for i in range(no_of_threads):
                        processes[i].join()
                else:
                    for company_url in urls_to_scrape:
                        scraper.scrape_url(company_url, continue_from_last_page=continue_from_last_scrape)
                        last_scrape = {}
                        last_scrape["url"] = company_url
                        last_scrape["category"] = category
                        with open("last_scrape_info.json", "w") as f:
                            json.dump(last_scrape, f)
    
    def scrape_urls_from_queue(self, q, category, continue_from_last_scrape):

        scraper = SiteJabberScraper()
        
        while q.qsize():
            company_url = q.get()
            scraper.scrape_url(company_url, continue_from_last_page=continue_from_last_scrape)
            last_scrape = {}
            last_scrape["url"] = company_url
            last_scrape["category"] = category
            with open("last_scrape_info.json", "w") as f:
                json.dump(last_scrape, f)
        
        del scraper
            
        


    def __collect_category_urls(self, category=None):
        if not category:
            categories = self.driver.find_elements_by_class_name("categories-browse__row")
            self.__total_categories_urls = {}
        else:
            try:
                if category.text.strip()[-1] == ")" or category.find_element_by_tag_name("a").get_attribute("href") != "https://www.sitejabber.com/categories#":
                    name = category.text.strip()
                    if name[-1] == ")":
                        name = " ".join(name.split()[:-1])
                    url = category.find_element_by_tag_name("a").get_attribute("href")
                    if name not in list(self.__total_categories_urls.keys()):
                        logging.info("Got Category: " + name)
                        self.__total_categories_urls[name] = url
                    return
            except:
                return
            else:
                try:
                    category.find_element_by_tag_name("a").click()
                except:
                    scroll_to_center = """var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0); 
                                    var elementTop = arguments[0].getBoundingClientRect().top; 
                                    window.scrollBy(0, elementTop-(viewPortHeight/2));"""
                    self.driver.execute_script(scroll_to_center, category)
                    time.sleep(1)
                    category.find_element_by_tag_name("a").click()
                time.sleep(0.5)
                categories = category.find_elements_by_class_name("categories-browse__list__item")
        for category in categories:
            self.__collect_category_urls(category)


    def __scrape_company_urls_from_category(self, url):

        self.driver.get(url)
        company_urls = []
        while True:

            company_blocks = self.driver.find_elements_by_class_name("url-list__item__content")
            company_urls += [block.find_element_by_tag_name("a").get_attribute("href") for block in company_blocks]
            try:
                next_page = self.driver.find_element_by_class_name("pagination__next").find_element_by_tag_name("a")
                scroll_to_center = """var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0); 
                                var elementTop = arguments[0].getBoundingClientRect().top; 
                                window.scrollBy(0, elementTop-(viewPortHeight/2));"""
                self.driver.execute_script(scroll_to_center, next_page)
                time.sleep(1)
                next_page.click()
                time.sleep(1)
                while True:
                    if self.driver.find_element_by_class_name("categories-view__loading").get_attribute("style") == "":
                        break
                    time.sleep(1)
            except:
                break

        return company_urls



    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass

def scrapeCompanyThread( urlsQueue, options ):
    scraper = SiteJabberScraper()

    while urlsQueue.qsize():
        companyUrl = urlsQueue.get()
        scrapeCompanyDataByID( scraper, companyUrl, options )
    
    del scraper

def scrapeCompaniesInThreads( urls, options ):
    print("Scrape in threads, urls: %d..." % ( len(urls) ) )

    if options["threads"] > 1 and ( platform == "linux" or platform == "linux2" ):
        urlsQueue = Queue()

        for url in urls:
            urlsQueue.put( url )

        print("Scrape with threads: %d, urls: %d" % ( options["threads"], urlsQueue.qsize() ) )

        processes = []
        for i in range( options["threads"] ):
            processes.append( Process( target = scrapeCompanyThread, args = ( urlsQueue, options ) ) )
            processes[i].start()

        for i in range( options["threads"] ):
            processes[i].join()

        print( "Job done" )
    else:
        scraper = SiteJabberScraper()
        for url in urls:
            scrapeCompanyDataByID( scraper, url, options )


def scrapeCompanyDataByID( scraper, url, options ):
    url = url.strip()
    if url:
        companyID = url.strip("/").split("/")[-1]
        company = scraper.scrape_company_details( companyID, save_to_db = options["saveToDatabase"] )
        if company.status == "error":
            logging.error( "Error invalid company" )
            return False

        logging.info("Company Details for %s scraped successfully.\n" % company.id )

        print(company)
        print("\n")
        
        if options["skipReviews"] is False:
            print("Get reviews...")
            company.reviews = scraper.scrape_company_reviews( companyID, save_to_db = options["saveToDatabase"] )
            logging.info("Reviews for %s scraped successfully.\n" % company.id )
            for i, review in enumerate(company.reviews, start=1):
                print("Review# " + str(i))
                print(review)
                print("\n")
        else:
            print("Skiping reviews")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="SiteGrabberScraper CLI to grab company and reviews from URL")
    parser.add_argument("--bulk_scrape", nargs='?', type=bool, default=False, help="Boolean variable to bulk scrape companies. Default False. If set to True, save_to_db will also be set to True")
    parser.add_argument("--no_of_threads", nargs='?', type=int, default=1, help="No of threads to run. Default 1")
    parser.add_argument("--log_file", nargs='?', type=str, default=None, help="Path for log file. If not given, output will be printed on stdout.")
    parser.add_argument("--urls", nargs='*', help="url(s) for scraping. Separate by spaces")
    parser.add_argument("--urls_from_file", nargs='?', type=str, help="Parse urls from file")
    parser.add_argument("--skip_reviews", nargs='?', type=bool, default=False, help="Skip reviews if loaded by --urls or --urls_from_file")
    parser.add_argument("--save_to_db", nargs='?', type=bool, default=False, help="Boolean variable to save to db. Default False")
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
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
    
    if args.bulk_scrape:
        if os.path.isfile("category_urls.json") and os.path.isfile("last_scrape_info.json"):
            scraper.bulk_scrape(get_urls_from_file=True, continue_from_last_scrape=True, no_of_threads=args.no_of_threads)
        elif os.path.isfile("category_urls.json"):
            scraper.bulk_scrape(get_urls_from_file=True, continue_from_last_scrape=False, no_of_threads=args.no_of_threads)
        elif os.path.isfile("last_scrape_info.json"):
            scraper.bulk_scrape(get_urls_from_file=False, continue_from_last_scrape=True, no_of_threads=args.no_of_threads)
        else:
            scraper.bulk_scrape(get_urls_from_file=False, continue_from_last_scrape=False, no_of_threads=args.no_of_threads)
    elif args.urls_from_file:
        urls = []
        with open( args.urls_from_file ) as file:
            for line in file:
                urls.append( line.strip() )
                    
        scrapeCompaniesInThreads( urls, { "saveToDatabase": args.save_to_db, "skipReviews":  args.skip_reviews, "threads": args.no_of_threads } )
                    
    else:
        scrapeCompaniesInThreads( args.urls, { "saveToDatabase": args.save_to_db, "skipReviews":  args.skip_reviews, "threads": args.no_of_threads } )

        
    
    