##########################################
# Coded by Mustansir Muzaffar
# mustansir2001@gmail.com
# +923333487952
##########################################

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pyvirtualdisplay import Display
import time
from typing import List
from utility_files.DB import DB
from utility_files.models import Company, Review
import datetime
import requests
import os
import argparse
import json
import sys
import logging, traceback
from multiprocessing import Process, Queue
from sys import platform
logging.getLogger('WDM').setLevel(logging.ERROR)
os.environ['WDM_LOG'] = "false"

class SiteJabberScraper():

    def __init__(self, chromedriver_path=None) -> None:
        if os.name != "nt":
            self.display = Display(visible=0, size=(1920, 1080))
            self.display.start()
            
        options = Options()
        # need to set sort 
        options.add_argument("window-size=1920,1080")
        options.add_argument("--log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        # options.add_argument('--single-process'); # one process to take less memory
        options.add_argument('--renderer-process-limit=1'); # do not allow take more resources
        options.add_argument('--disable-crash-reporter'); # disable crash reporter process
        options.add_argument('--no-zygote'); # disable zygote process
        options.add_argument('--disable-crashpad')
        
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36")
        if chromedriver_path:
            self.driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        else:
            self.driver = webdriver.Chrome(options=options, service=Service(ChromeDriverManager().install()))
            
        self.dealt_with_popup = False
        
        if not os.path.exists("file/logo/"):
            os.makedirs("file/logo")
        if not os.path.exists("file/review/"):
            os.makedirs("file/review")
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

        logging.info("Scraping Company Details for " + "https://www.sitejabber.com/reviews/" + company_id)
        
        company = Company()
        
        company.id = company_id
        company.url = "https://www.sitejabber.com/reviews/" + company_id
        
        self.driver.get(company.url)
        
        # get description
        try:
            company.description = self.driver.find_element(By.CSS_SELECTOR, ".url-business__description").get_attribute('innerText')
        except Exception as e:
            company.description = ""
            
        # fill empty fields via ld+json
        try:
            scripts = self.driver.find_elements(By.CSS_SELECTOR, "script[type='application/ld+json']")
            for script in scripts:
                content = script.get_attribute("innerText").strip()
                content = content.replace( "\n", "" ).replace( "\r", "" )
                content = json.loads( content )
                
                if "@type" in content and content["@type"] == "Organization" and "address" in content:
                    addressData = content["address"]

                    if "addressLocality" in addressData:
                        company.city = addressData["addressLocality"]

                    if "addressRegion" in addressData:
                        company.state = addressData["addressRegion"]

                    if "addressCountry" in addressData:
                        company.country = addressData["addressCountry"]["name"]
                        
                        
                    company.name = content['name']
            
        except Exception as e:
            logging.error(traceback.format_exc())
        
        try:
            res = requests.get(self.driver.find_element(By.CSS_SELECTOR, ".website-thumbnail__image.object-fit").get_attribute("src"))
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
            categories = self.driver.find_elements(By.CSS_SELECTOR, ".suggest-categories__breadcrumb")
            company.category1 = company.category2 = company.category3 = ""

            if len(categories) > 0:
                company.category1 = categories[0].text.strip()
            if len(categories) > 1:
                company.category2 = categories[1].text.strip()
            if len(categories) > 2:
                company.category3 = categories[2].text.strip()

            company.email = self.driver.find_element(By.CSS_SELECTOR, "#location-email").get_attribute("value")
            company.phone = ""

            wait_counter = 0
            while wait_counter < 5:
                try:
                    phone = self.driver.find_element(By.CSS_SELECTOR, "#inpt_verification_phone").get_attribute("value").replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
                    if not phone.strip():
                        company.phone = ""
                        break 
                    country_code = Select(self.driver.find_element(By.CSS_SELECTOR, "#inpt_verification_country")).first_selected_option.get_attribute("data-isd").replace("-", "")
                    company.phone =  country_code + phone 
                    break
                except:
                    time.sleep(1)
                    wait_counter += 1

            company.street_address1 = self.driver.find_element(By.CSS_SELECTOR, "#location-street-address").get_attribute("value")
            company.street_address2 = self.driver.find_element(By.CSS_SELECTOR, "#location-street-address-2").get_attribute("value")

            city = self.driver.find_element(By.CSS_SELECTOR, "#location-city").get_attribute("value")
            if city:
                company.city = city

            state = self.driver.find_element(By.CSS_SELECTOR, "#location-state").get_attribute("value")
            state = company.state.replace( "non-us", "" ) if company.state is not None else ""
            if state:
                company.state = state

            company.zip_code = self.driver.find_element(By.CSS_SELECTOR, "#location-postal-code").get_attribute("value")

            country = self.driver.find_element(By.CSS_SELECTOR, "#location-country").get_attribute("value")
            if country:
                company.country = country

            usStates = ["alaska", "alabama", "arkansas", "american samoa", "arizona", "california", "colorado", "connecticut", "district of columbia", "delaware", "florida", "georgia", "guam", "hawaii", "iowa", "idaho", "illinois", "indiana", "kansas", "kentucky", "louisiana", "massachusetts", "maryland", "maine", "michigan", "minnesota", "missouri", "mississippi", "montana", "north carolina", "north dakota", "nebraska", "new hampshire", "new jersey", "new mexico", "nevada", "new york", "ohio", "oklahoma", "oregon", "pennsylvania", "puerto rico", "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah", "virginia", "virgin islands", "vermont", "washington", "wisconsin", "west virginia", "wyoming"]
            if not country and company.state and company.state.lower() in usStates:
                company.country = "United States"

            company.wikipedia_url = self.driver.find_element(By.CSS_SELECTOR, "#wikipedia-url").get_attribute("value")
            company.facebook_url = self.driver.find_element(By.CSS_SELECTOR, "#facebook-url").get_attribute("value")
            company.twitter_url = self.driver.find_element(By.CSS_SELECTOR, "#twitter-url").get_attribute("value")
            company.linkedin_url = self.driver.find_element(By.CSS_SELECTOR, "#linkedin-url").get_attribute("value")
            company.youtube_url = self.driver.find_element(By.CSS_SELECTOR, "#youtube-url").get_attribute("value")
            company.pinterest_url = self.driver.find_element(By.CSS_SELECTOR, "#pinterest-url").get_attribute("value")
            company.instagram_url = self.driver.find_element(By.CSS_SELECTOR, "#instagram-url").get_attribute("value")
            
            if company.zip_code and company.country and ( not company.state or not company.city ):
                zipDataUrl = "http://www.vcharges.com/get-zip.php?country=" + requests.utils.quote( company.country ) + "&zip=" + requests.utils.quote( company.zip_code ) + "&type=all&output=json"
                
                print(zipDataUrl)
                
                response = requests.get( zipDataUrl, timeout = 5 )
                if response.status_code == 200:
                    print(response.json())
                
                
        except Exception as e:
            logging.error( "Error looking fields values: " + str(e) )

            company.name = company.id
            company.status = "error"
            company.log = "edit-business page error : " + str(e)

        if not company.status:
            company.status = "success"
            
        if save_to_db:
            if company.status == "success":
                self.db.insert_or_update_company( company )
            
        return company


    def scrape_company_reviews(self, company_id, save_to_db=True, scrape_specific_review=None, continue_from_last_page=None) -> List[Review]:

        if scrape_specific_review:
            logging.info("Scraping review with id %s for %s" % (scrape_specific_review, company_id))
        else:
            logging.info("Scraping reviews for " + company_id)
            
        review_url = "https://www.sitejabber.com/reviews/" + company_id
        logging.info(review_url)

        self.driver.get(review_url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#business_owners")
            )
        )

        logging.info("set sorting...")

        # change sort newest to oldest
        searchForm = self.driver.find_element(By.CSS_SELECTOR, '#UrlReviewsFiltersForm')
        self.driver.execute_script("arguments[0].scrollIntoView();", searchForm)
        time.sleep(1)

        sortSelectBoxIt = self.driver.find_element(By.ID,"sortSelectBoxIt")
        self.driver.execute_script("arguments[0].click();", sortSelectBoxIt)
        time.sleep(1)

        self.driver.find_element(By.CSS_SELECTOR,"#sortSelectBoxItOptions li[data-val='published']").click()
        
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
                        logging.info("Dealt popup delay...")

                        popup = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "ad-popup__dialog.ad-popup__widget")))
                        popup.find_element(By.CSS_SELECTOR, ".ad-popup__widget__title_close").click()
                        self.dealt_with_popup = True
                    except:
                        pass

                    try:
                        self.driver.find_element(By.CSS_SELECTOR, ".cookie-consent__close").click()
                    except:
                        pass
                        
                review_tags = self.driver.find_elements(By.CSS_SELECTOR, ".review")
                logging.info("Total reviews: " + str(len(review_tags)))

                for review_tag in review_tags:
                    username = review_tag.find_element(By.CSS_SELECTOR, ".review__author__name").text.strip()
                    
                    if scrape_specific_review and username != review_results[0]["username"]:
                        continue

                    try:
                        helpful_count = int(review_tag.find_element(By.CSS_SELECTOR, ".helpful__count").text.strip("()"))
                    except:
                        helpful_count = 0
                        
                    review_contents = review_tag.find_elements(By.CSS_SELECTOR, ".review__content")
                    
                    for review_content in review_contents:
                        review = Review()
                        review.company_id = company_id
                        review.username = username
                        
                        try:
                            date = review_content.find_element(By.CSS_SELECTOR, ".review__date").text.strip().replace("st,", "").replace("nd,", "").replace("rd,", "").replace("th,", "")
                            review.date = datetime.datetime.strptime(date, "%B %d %Y").strftime('%Y-%m-%d')
                        except:
                            review.date = None
                            review.log += "Error while scraping/parsing date\n"
                            review.status = "error"
                            
                        if scrape_specific_review and str(review.date) != str(review_results[0]["review_date"]):
                            continue
                            
                        review.no_of_helpful_votes = helpful_count
                        
                        try:
                            review.review_title = review_content.find_element(By.CSS_SELECTOR, ".review__title__text").text.strip()
                        except:
                            review.review_title = ""
                            review.status = "error"
                            review.log += "error while scraping review title\n"
                            
                        try:
                            review.review_text = review_content.find_element(By.CSS_SELECTOR, ".review__text").find_element(By.TAG_NAME, "p").text.strip()
                        except Exception as e:
                            review.review_text = ""
                            
                        try:
                            review.review_stars = float(review_content.find_element(By.CSS_SELECTOR, ".stars").get_attribute("title").split()[0])
                        except:
                            review.status = "error"
                            review.log += "error while scraping review stars\n"
                            
                        try:
                            images = review_tag.find_element(By.CSS_SELECTOR, ".review__photos").find_elements(By.TAG_NAME, "img")
                            for image in images:
                                review.images.append(image.get_attribute("data-src"))
                        except:
                            pass
                            
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
                logging.info("Next page...")

                self.driver.execute_script("document.querySelector('.pagination__next .pagination__button--enabled').click();")
            except:
                logging.info("No more pages, break")
                break

            page += 1

            # https://www.sitejabber.com/reviews/chicme.com has 240k reviews, max 1000 reviews scrape, in page 25 reviews = 1000 / 25 = 40
            if page > 40:
                logging.info("page > 40, break")
                break
        
            
        return reviews


    def bulk_scrape(self, get_urls_from_file=False, skip_if_exists=False, no_of_threads=1):
 
        empty_file = False
        if get_urls_from_file:
            with open("temp/category_urls.json", "r") as f:
                self.__total_categories_urls = json.load(f)

            if self.__total_categories_urls == {}:
                empty_file = True
        
        if not get_urls_from_file or empty_file:
            logging.info("Scraping Category URLs...")
            self.driver.get("https://www.sitejabber.com/categories")
            time.sleep(2)
            self.__collect_category_urls()
            if not os.path.isdir("temp"):
                os.mkdir("temp")
            with open("temp/category_urls.json", "w") as f:
                json.dump(self.__total_categories_urls, f)
            
        
        for category, url in self.__total_categories_urls.items():
            logging.info("Scraping URLS for category: " + category)
            company_urls = self.__scrape_company_urls_from_category(url)
            if platform == "linux" or platform == "linux2":
                urls_to_scrape = Queue()
            else:
                urls_to_scrape = []
            found_url = False
            for company_url in company_urls:

                self.db.cur.execute("SELECT date_updated from company where url = %s", (company_url, ))
                data = self.db.cur.fetchall()
                if len(data) > 0:
                    date_updated = data[0][0]
                    if (date_updated - datetime.datetime.now()).days < 7:
                        continue
                found_url = True
                if platform == "linux" or platform == "linux2":
                    urls_to_scrape.put(company_url)
                else:
                    urls_to_scrape.append(company_url)
                        
            if not found_url:
                logging.info("All Companies from category " + category + " are already updated!")
                continue

            if platform == "linux" or platform == "linux2":
                processes = []
                for i in range(no_of_threads):
                    processes.append(Process(target=self.scrape_urls_from_queue, args=(urls_to_scrape, category)))
                    processes[i].start()

                for i in range(no_of_threads):
                    processes[i].join()
            else:
                for company_url in urls_to_scrape:
                    scraper.scrape_url(company_url, continue_from_last_page=True)

            logging.info("All Companies from category " + category + " added/updated!")

        logging.info("All Companies Scraped!")
    
    def scrape_urls_from_queue(self, q, category):

        scraper = SiteJabberScraper()
        
        while q.qsize():
            company_url = q.get()
            scraper.scrape_url(company_url, continue_from_last_page=True)
        
        scraper.kill_chrome()
            
    

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
                    category.find_element(By.CSS_SELECTOR, "a").click()
                time.sleep(0.5)
                categories = category.find_elements(By.CSS_SELECTOR, ".categories-browse__list__item")
        for category in categories:
            self.__collect_category_urls(category)


    def __scrape_company_urls_from_category(self, url):

        self.driver.get(url)
        company_urls = []
        while True:

            company_blocks = self.driver.find_elements(By.CSS_SELECTOR, ".url-list__item__content")
            company_urls += [block.find_element(By.TAG_NAME, "a").get_attribute("href") for block in company_blocks]
            try:
                next_page = self.driver.find_element(By.CSS_SELECTOR, ".pagination__next").find_element_by_tag_name("a")
                scroll_to_center = """var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0); 
                                var elementTop = arguments[0].getBoundingClientRect().top; 
                                window.scrollBy(0, elementTop-(viewPortHeight/2));"""
                self.driver.execute_script(scroll_to_center, next_page)
                time.sleep(1)
                next_page.click()
                time.sleep(1)
                while True:
                    if self.driver.find_element(By.CSS_SELECTOR, ".categories-view__loading").get_attribute("style") == "":
                        break
                    time.sleep(1)
            except:
                break

        return company_urls



    def kill_chrome(self):
        try:
            self.driver.quit()
        except:
            pass

def scrapeCompanyThread( urlsQueue, options ):
    scraper = SiteJabberScraper()

    while urlsQueue.qsize():
        companyUrl = urlsQueue.get()
        scrapeCompanyDataByID( scraper, companyUrl, options )
    
    scraper.kill_chrome()

def scrapeCompaniesInThreads( urls, options ):
    print("Scrape in threads, urls: %d..." % ( len(urls) ) )

    if options["threads"] > 1:
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
    parser.add_argument("--urls", nargs='*', help="url(s) for scraping. Separate by spaces")
    parser.add_argument("--urls_from_file", nargs='?', type=str, help="Parse urls from file")
    parser.add_argument("--skip_reviews", nargs='?', type=bool, default=False, help="Skip reviews if loaded by --urls or --urls_from_file")
    parser.add_argument("--save_to_db", nargs='?', type=bool, default=False, help="Boolean variable to save to db. Default False")
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    
    logging.basicConfig(handlers=[
        logging.FileHandler("logs/SiteJabberScraper.py.log"),
        logging.StreamHandler()
    ], format='%(asctime)s Process ID %(process)d: %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
    
    scraper = SiteJabberScraper()
    if args.bulk_scrape:
        if os.path.isfile("temp/category_urls.json"):
            scraper.bulk_scrape(get_urls_from_file=True, no_of_threads=args.no_of_threads)
        else:
            scraper.bulk_scrape(get_urls_from_file=False, no_of_threads=args.no_of_threads)
    elif args.urls_from_file:
        urls = []
        with open( args.urls_from_file ) as file:
            for line in file:
                urls.append( line.strip() )
                    
        scrapeCompaniesInThreads( urls, { "saveToDatabase": args.save_to_db, "skipReviews":  args.skip_reviews, "threads": args.no_of_threads } )
                    
    else:
        scrapeCompaniesInThreads( args.urls, { "saveToDatabase": args.save_to_db, "skipReviews":  args.skip_reviews, "threads": args.no_of_threads } )

    scraper.kill_chrome()

        
    
    