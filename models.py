class Company:

    def __init__(self) -> None:
        self.id = None
        self.name = None
        self.url = None
        self.logo = None
        self.category1 = None
        self.category2 = None
        self.category3 = None
        self.email = None
        self.phone = None
        self.street_address1 = None
        self.street_address2 = None
        self.city = None
        self.state = None
        self.zip_code = None
        self.country = None
        self.wikipedia_url = None
        self.facebook_url = None
        self.twitter_url = None
        self.linkedin_url = None
        self.youtube_url = None
        self.pinterest_url = None
        self.instagram_url = None
        self.reviews = []
        self.log = None
        self.status = None

    def __str__(self) -> str:
        return_string  = "Name: " + self.name
        return_string  += "\nLogo: " + self.logo
        if self.category1:
            return_string  += "\nCategory 1: " + self.category1
        if self.category2:
            return_string  += "\nCategory 2: " + self.category2
        if self.category3:
            return_string  += "\nCategory 3: " + self.category3
        return_string  += "\nEmail: " + str(self.email)
        return_string  += "\nPhone: " + str(self.phone)
        return_string  += "\nStreet Address 1: " + str(self.street_address1)
        return_string  += "\nStreet Address 2: " + str(self.street_address2)
        return_string  += "\nCity: " + str(self.city)
        return_string  += "\nState: " + str(self.state)
        return_string  += "\nCountry: " + str(self.country)
        return_string  += "\nZip Code: " + str(self.zip_code)
        social_media_urls = [self.wikipedia_url, self.facebook_url, self.twitter_url, self.linkedin_url, self.youtube_url, self.pinterest_url, self.instagram_url]
        return_string  += "\nSocial Media URLs: " + " | ".join([url for url in social_media_urls if url])
        return return_string 

class Review:

    def __init__(self) -> None:
        self.company_id = None
        self.date = None
        self.username = None
        self.no_of_helpful_votes = None
        self.review_title = None
        self.review_text = None
        self.review_stars = None
        self.review_page_no = None
        self.log = ""
        self.status = None

    def __str__(self) -> str:
        return_string  = "Company: " + self.company_id
        return_string  += "\nDate Posted: " + self.date
        return_string  += "\nUser: " + self.username
        return_string  += "\nNo of Helpful Votes: " + str(self.no_of_helpful_votes)
        return_string  += "\nReview Stars: " + str(self.review_stars)
        return_string  += "\nReview Title: " + self.review_title
        return_string  += "\nReview Text: " + self.review_text
        return_string  += "\nReview Page No: " + str(self.review_page_no)
        return return_string