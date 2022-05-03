from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json, argparse, sys, re, time, logging

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)


class WikipediaScraper():

    def __init__(self, chromedriver_path=None):
        options = Options()
        options.headless = True
        options.add_argument("window-size=1920,1080")
        options.add_argument("--log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36")
        if chromedriver_path:
            self.driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)
        else:
            self.driver = webdriver.Chrome(executable_path=ChromeDriverManager(log_level=logging.ERROR).install(), options=options)
        self.driver.get("https://www.wikipedia.org/")

    def scrape_company(self, company_name, keywords=[]):

        
        search_input = self.driver.find_element_by_id("searchInput")
        search_input.clear()
        self.driver.find_element_by_tag_name("h1").click()
        time.sleep(1)
        search_input.send_keys(company_name)
        time.sleep(1)
        try:
            dropdown = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "suggestions-dropdown")))
        except:
            raise Exception(f"Couldn't find company {company_name} on Wikipedia")
        suggestions = dropdown.find_elements_by_class_name("suggestion-link")
        found = False
        keywords += ["company", "corporation", "manufacturer", "business", "operator", "supplier", "software"]
        for suggestion in suggestions:
            if self.__check_keywords(suggestion.find_element_by_class_name("suggestion-description").text, keywords):
                found = suggestion
                break
        if not found and suggestions:
            found = suggestions[0]
        if not found:
            raise Exception(f"Couldn't find company {company_name} on Wikipedia")
        
        page_link = found.get_attribute("href")
        self.driver.execute_script('''window.open("","_blank");''')
        self.driver.switch_to.window(self.driver.window_handles[1])
        try:
            self.driver.get(page_link)
            company = {"name": company_name}
            company["official_name"] = self.driver.find_element_by_id("firstHeading").text.strip()
            rows = [row for row in self.driver.find_element_by_class_name("infobox.vcard").find_elements_by_tag_name("tr") if len(row.find_elements_by_tag_name("th")) and len(row.find_elements_by_tag_name("td"))]
            for row in rows:
                th_text = row.find_element_by_tag_name("th").text.lower().strip()
                td = row.find_element_by_tag_name("td")
                if th_text == "industry":
                    company["industry"] = [self.__clear_boxes(li.text.strip().replace("\n", ", ")) for li in td.find_elements_by_tag_name("li")]
                    if company["industry"] == []:
                        td_text = td.text.strip()
                        if "\n" in td_text:
                            company["industry"] = self.__clear_boxes(td.text.strip()).split("\n")
                        else:
                            company["industry"] = self.__clear_boxes(td.text.strip()).split(",")
                elif th_text == "isin":
                    company["isin"] = self.__clear_boxes(td.text.strip().replace("\n", ", "))
                elif th_text == "formerly":
                    company["former_names"] = [self.__clear_boxes(li.text.strip().replace("\n", " ")) for li in td.find_elements_by_tag_name("li")]
                    if company["former_names"] == []:
                        company["former_names"] = [self.__clear_boxes(td.text.strip().replace("\n", ", "))]
                elif th_text == "headquarters":
                    company["headquarters"] = self.__clear_boxes(td.text.strip().replace("\n", ", "))
                    company["country"] = self.__clear_boxes(company["headquarters"].split(",")[-1].strip().replace("\n", ", "))
                elif th_text == "type":
                    company["type"] = self.__clear_boxes(td.text.strip().replace("\n", ", "))
                elif th_text == "traded as":
                    company["traded_as"] = [self.__clear_boxes(li.text.strip().replace("\n", ", ")) for li in td.find_elements_by_tag_name("li")]
                    if company["traded_as"] == []:
                        company["traded_as"] = [self.__clear_boxes(td.text.strip().replace("\n", ", "))]
                elif th_text == "products":
                    try:
                        td.find_element_by_class_name("mw-collapsible-toggle.mw-collapsible-toggle-default.mw-collapsible-toggle-collapsed").click()
                        time.sleep(0.3)
                    except:
                        pass
                    company["product_types"] = [self.__clear_boxes(li.text.strip().replace("\n", ", ")) for li in td.find_elements_by_tag_name("li") if "\n" not in li.text]
                    if company["product_types"] == []:
                        company["product_types"] = self.__clear_boxes(td.text.strip()).split("\n")
                elif th_text == "revenue":
                    company["revenue"] = self.__clear_boxes(td.text.strip().replace("\n", ", "))
                elif th_text == "net income":
                    company["net_income"] = self.__clear_boxes(td.text.strip().replace("\n", ", "))
                elif th_text == "number of employees":
                    company["number_of_employees"] = self.__clear_boxes(td.text.split()[0].replace("\n", ", "))
                elif th_text == "founders" or th_text == "founder":
                    company["founders"] = [self.__clear_boxes(li.text.strip().replace("\n(", "(")) for li in td.find_elements_by_tag_name("li")]
                    if company["founders"] == []:
                        company["founders"] = self.__clear_boxes(td.text.strip().replace("\n(", "(")).split("\n")
                elif th_text == "key people":
                    company["key_people"] = [self.__clear_boxes(li.text.strip().replace("\n", " ")) for li in td.find_elements_by_tag_name("li")]
                    if company["key_people"] == []:
                        company["key_people"] = self.__clear_boxes(td.text.strip().replace("\n(", "(")).split("\n")
                elif th_text == "founded":
                    company["foundation_date"] = self.__clear_boxes(td.text.split(";")[0]).strip().replace("\n", ", ")
                elif th_text == "services":
                    try:
                        td.find_element_by_class_name("mw-collapsible-toggle.mw-collapsible-toggle-default.mw-collapsible-toggle-collapsed").click()
                        time.sleep(0.3)
                    except:
                        pass
                    company["services"] = [self.__clear_boxes(li.text) for li in td.find_elements_by_tag_name("li") if "\n" not in li.text]
                    if company["services"] == []:
                        company["services"] = self.__clear_boxes(td.text.strip()).split("\n")
                elif th_text == "area served":
                    company["service_area"] = self.__clear_boxes(td.text.strip().replace("\n", ", "))
                elif th_text == "website" or th_text == "url":
                    company["official_website"] = self.__clear_boxes(td.text.strip().replace("\n", ", "))
                elif th_text == "number of locations":
                    company["number_of_locations"] = self.__clear_boxes(td.text.strip().split()[0].replace("\n", ", "))
                
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return company
        
        except Exception as e:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            raise Exception(e)

    def __check_keywords(self, text, keywords):

        for keyword in keywords:
            if keyword.lower() in text.lower():
                return True

        return False

    def __clear_boxes(self, s):
        return re.sub("\[(.*?)\]", "", s)

    def __del__(self):

        try:
            self.driver.quit()
        except:
            pass
        
            


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Scrape company details from wikipedia")
    parser.add_argument("input_file", type=str, help="Name of input file with a list of companies separated by newline")
    parser.add_argument("output_file", type=str, help="Name of json output file")
    parser.add_argument("keywords", nargs='*', type=str, help="An optional list of keywords to help the scraper find the correct wikipedia page. For example: technology, agriculture, construction etc (separate by spaces)")
    if len(sys.argv) <= 2:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    if args.output_file[-5:] != ".json":
        args.output_file += ".json"

    with open(args.input_file, "r") as f:
        company_names = f.read().strip().split("\n")
    
    output_json = {"companies": []}
    scraper = WikipediaScraper()
    successful = []
    error = []
    for company_name in company_names:

        logging.info(f"Scraping data for {company_name}")
        try:
            output_json["companies"].append(scraper.scrape_company(company_name, args.keywords))
            with open(args.output_file, "w") as f:
                json.dump(output_json, f, indent=4)
            logging.info(f"Data for {company_name} scraped successfully!")
            successful.append(company_name)
        except Exception as e:
            logging.error(f"Error in scraping company {company_name}. Error info: {e}")
            error.append(company_name)
    
    with open("report.txt", "w") as f:
        f.write("Succesfully Scraped:\n\n{}\n\nError while scraping:\n\n{}".format('\n'.join(successful), '\n'.join(error)))


