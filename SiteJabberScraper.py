from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

class SiteJabberScraper():

    def __init__(self, chromedriver_path=None) -> None:
        options = Options()
        options.headless = True
        options.add_argument("window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36")
        if chromedriver_path:
            self.driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)
        self.dealt_with_popup = False
        if not os.path.exists("file/logo/"):
            os.makedirs("file/logo")
        self.db = DB()


    def scrape_url(self, url, save_to_db=True) -> Company:
        
        if "https://www.sitejabber.com/reviews/" not in url and "https://www.sitejabber.com/edit-business/" not in url:
            raise Exception("Invalid URL")
        company_id = url.strip("/").split("/")[-1]
        company = self.scrape_company_details(company_id, save_to_db)
        company.reviews = self.scrape_company_reviews(company_id, save_to_db)
        return company


    def scrape_company_details(self, company_id, save_to_db=True) -> Company:

        print("Scraping Company Details for " + company_id)
        company = Company()
        company.id = company_id
        company.url = "https://www.sitejabber.com/reviews/" + company_id
        self.driver.get(company.url)
        try:
            res = requests.get(self.driver.find_element_by_class_name("website-thumbnail__image.object-fit").get_attribute("src"))
            filename = "file/logo/" + company_id.replace("/", "_").replace(".", "_").replace("\\", "_") + ".jpg"
            with open(filename, "wb") as f:
                f.write(res.content)
            company.logo = filename
        except:
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
            company.email = self.driver.find_element_by_id("email").get_attribute("value")
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
            company.street_address1 = self.driver.find_element_by_id("street-address").get_attribute("value")
            company.street_address2 = self.driver.find_element_by_id("street-address-2").get_attribute("value")
            company.city = self.driver.find_element_by_id("city").get_attribute("value")
            company.state = self.driver.find_element_by_id("state").get_attribute("value")
            company.zip_code = self.driver.find_element_by_id("postal-code").get_attribute("value")
            company.country = self.driver.find_element_by_id("country").get_attribute("value")
            company.wikipedia_url = self.driver.find_element_by_id("wikipedia-url").get_attribute("value")
            company.facebook_url = self.driver.find_element_by_id("facebook-url").get_attribute("value")
            company.twitter_url = self.driver.find_element_by_id("twitter-url").get_attribute("value")
            company.linkedin_url = self.driver.find_element_by_id("linkedin-url").get_attribute("value")
            company.youtube_url = self.driver.find_element_by_id("youtube-url").get_attribute("value")
            company.pinterest_url = self.driver.find_element_by_id("pinterest-url").get_attribute("value")
            company.instagram_url = self.driver.find_element_by_id("instagram-url").get_attribute("value")
        except:
            company.name = company.id
            company.status = "error"
            company.log = "edit-business page error"
        if not company.status:
            company.status = "success"
        if save_to_db:
            self.db.insert_or_update_company(company)
        return company


    def scrape_company_reviews(self, company_id, save_to_db=True, scrape_specific_review=None) -> List[Review]:

        if scrape_specific_review:
            print("Scraping review with id %s for %s" % (scrape_specific_review, company_id))
        else:
            print("Scraping reviews for " + company_id)
        review_url = "https://www.sitejabber.com/reviews/" + company_id
        self.driver.get(review_url)
        
        if scrape_specific_review:
            self.db.cur.execute("SELECT username, review_date from review where review_id = %s", (scrape_specific_review))
            review_results = self.db.cur.fetchall()
            got_review = False
    
        reviews = []
        page = 1
        while True:
            print("Page", page)
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
                        review.log += "Error while scraping/parsing date"
                        review.status = "error"
                    if scrape_specific_review and str(review.date) != str(review_results[0]["review_date"]):
                        continue
                    review.no_of_helpful_votes = helpful_count
                    review.review_title = review_content.find_element_by_class_name("review__title__text").text.strip()
                    try:
                        review.review_text = review_content.find_element_by_class_name("review__text").find_element_by_tag_name("p").text.strip()
                    except:
                        review.review_text = ""
                    review.review_stars = float(review_content.find_element_by_class_name("stars").get_attribute("title").split()[0])
                    reviews.append(review)
                    if scrape_specific_review:
                        got_review = True
                        break

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

        if save_to_db and reviews:
            self.db.insert_or_update_reviews(reviews)
            
        return reviews


    def bulk_scrape(self, get_urls_from_file=False, continue_from_last_scrape=False, skip_if_exists=False):
 
        if get_urls_from_file:
            with open("category_urls.json", "r") as f:
                self.__total_categories_urls = json.load(f)
        else:
            print("Scraping Category URLs...")
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
                print("No backup file found. Scraping from beginning")
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
                company_urls = self.__scrape_company_urls_from_category(url)
                for company_url in company_urls:
                    if not url_flag and company_url == last_company_url:
                        url_flag = True
                        continue
                    if url_flag:

                        if skip_if_exists:
                            self.db.cur.execute("SELECT * from company where url = %s;", (company_url))
                            if len(self.db.cur.fetchall()) > 0:
                                continue

                        self.scrape_url(company_url)
                        
                        last_scrape["url"] = company_url
                        last_scrape["category"] = category
                        with open("last_scrape_info.json", "w") as f:
                            json.dump(last_scrape, f)


    def __collect_category_urls(self, category=None):
        if not category:
            categories = self.driver.find_elements_by_class_name("categories-browse__row")
            self.__total_categories_urls = {}
        else:
            try:
                if category.text.strip()[-1] == ")" or category.find_element_by_tag_name("a").get_attribute("href") != "https://www.sitejabber.com/categories#":
                    name = category.text.strip().split()
                    if name[-1] == ")":
                        name = " ".join(name.split()[:-1])
                    url = category.find_element_by_tag_name("a").get_attribute("href")
                    if name not in (self.__total_categories_urls.keys()):
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



if __name__ == '__main__':

    
    

    parser = argparse.ArgumentParser(description="SiteGrabberScraper CLI to grab company and reviews from URL")
    parser.add_argument("--bulk_scrape", nargs='?', type=bool, default=False, help="Boolean variable to bulk scrape companies. Default False. If set to True, save_to_db will also be set to True")
    parser.add_argument("--urls", nargs='*', help="url(s) for scraping. Separate by spaces")
    parser.add_argument("--save_to_db", nargs='?', type=bool, default=False, help="Boolean variable to save to db. Default False")
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    scraper = SiteJabberScraper()
    if args.bulk_scrape:
        if os.path.isfile("category_urls.json") and os.path.isfile("last_scrape_info.json"):
            scraper.bulk_scrape(get_urls_from_file=True, continue_from_last_scrape=True)
        elif os.path.isfile("category_urls.json"):
            scraper.bulk_scrape(get_urls_from_file=True, continue_from_last_scrape=False)
        elif os.path.isfile("last_scrape_info.json"):
            scraper.bulk_scrape(get_urls_from_file=False, continue_from_last_scrape=True)
        else:
            scraper.bulk_scrape(get_urls_from_file=False, continue_from_last_scrape=False)
    else:
        for url in args.urls:
            id = url.strip("/").split("/")[-1]
            company = scraper.scrape_company_details(id, save_to_db=args.save_to_db)
            print("Company Details for %s scraped successfully.\n" % company.id)
            print(company)
            print("\n")
            company.reviews = scraper.scrape_company_reviews(id, save_to_db=args.save_to_db)
            print("Reviews for %s scraped successfully.\n" % company.id)
            for i, review in enumerate(company.reviews, start=1):
                print("Review# " + str(i))
                print(review)
                print("\n")

        
    
    