from flask import Flask, json, request
from multiprocessing import Process
import time
import requests
from SiteJabberScraper import SiteJabberScraper
from sys import platform

api = Flask(__name__)

@api.route('/api/v1/regrab-company', methods=['GET'])
def grab_company():

    def scrape_company(company_id, webhook_url):
        scraper = SiteJabberScraper()
        company = scraper.scrape_company_details(company_id)
        company.reviews = scraper.scrape_company_reviews(company_id)
        status = "success"
        if company.status == "error":
            status = "error"
            log = "Error in scraping company details"
        else:
            for review in company.reviews:
                if review.status == "error":
                    status = "error"
                    log = "Error in scraping some of the reviews"
        if status == "success":
            requests.post(webhook_url, json={"company_id": company_id, "status" : "success"})
        else:
            requests.post(webhook_url, json={"company_id": company_id, "status" : status, "log": log})

        scraper.kill_chrome()
        
    if "id" not in request.args:
        return json.dumps({"error" : "missing id argument"})
    if "webhookUrl" not in request.args:
        return json.dumps({"error" : "missing webhookUrl argument"})
    if platform == "linux" or platform == "linux2":
        p = Process(target=scrape_company, args=(request.args["id"], request.args["webhookUrl"],))
        p.start()
    else:
        scrape_company(request.args["id"], request.args["webhookUrl"])
    return json.dumps(request.args)

@api.route('/api/v1/regrab-review', methods=['GET'])
def grab_review():

    def scrape_review(review_id, webhook_url):
        scraper = SiteJabberScraper()
        scraper.db.cur.execute("SELECT company_id from review where review_id = %s;", (review_id,))
        company_id = scraper.db.cur.fetchall()[0]["company_id"]
        reviews = scraper.scrape_company_reviews(company_id, scrape_specific_review=review_id)
        status = "success"
        if reviews:
            if reviews[0].status == "error":
                status = "error"
                log = "Error in scraping review"
        else:
            status = "error"
            log = "No review found with given review_id"
        if status == "success":
            requests.post(webhook_url, json={"review_id": review_id, "status" : "success"})
        else:
            requests.post(webhook_url, json={"review_id": review_id, "status" : status, "log": log})

        scraper.kill_chrome()
        
    if "id" not in request.args:
        return json.dumps({"error" : "missing id argument"})
    if "webhookUrl" not in request.args:
        return json.dumps({"error" : "missing webhookUrl argument"})
    if platform == "linux" or platform == "linux2":
        p = Process(target=scrape_review, args=(request.args["id"], request.args["webhookUrl"],))
        p.start()
    else:
        scrape_review(request.args["id"], request.args["webhookUrl"])
    return json.dumps(request.args)



if __name__ == "__main__":
    api.run()