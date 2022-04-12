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
        
    def str( self, text ) -> str:
        return str( text ).encode( "utf-8", "ignore" ).decode( "utf-8" )

    def __str__(self) -> str:
        return_string  = "Name: " + self.str(self.name)
        return_string  += "\nLogo: " + self.str(self.logo)
        if self.category1:
            return_string  += "\nCategory 1: " + self.str(self.category1)
        if self.category2:
            return_string  += "\nCategory 2: " + self.str(self.category2)
        if self.category3:
            return_string  += "\nCategory 3: " + self.str(self.category3)
        return_string  += "\nEmail: " + self.str(self.email)
        return_string  += "\nPhone: " + self.str(self.phone)
        return_string  += "\nStreet Address 1: " + self.str(self.street_address1)
        return_string  += "\nStreet Address 2: " + self.str(self.street_address2)
        return_string  += "\nCity: " + self.str(self.city)
        return_string  += "\nState: " + self.str(self.state)
        return_string  += "\nCountry: " + self.str(self.country)
        return_string  += "\nZip Code: " + self.str(self.zip_code)
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
        
    def str( self, text ) -> str:
        return str( text ).encode( "utf-8", "ignore" ).decode( "utf-8" )

    def __str__(self) -> str:
        return_string  = "Company: " + self.str(self.company_id)
        return_string  += "\nDate Posted: " + self.str(self.date)
        return_string  += "\nUser: " + self.str(self.username)
        return_string  += "\nNo of Helpful Votes: " + self.str(self.no_of_helpful_votes)
        return_string  += "\nReview Stars: " + self.str(self.review_stars)
        return_string  += "\nReview Title: " + self.str(self.review_title)
        return_string  += "\nReview Text: " + self.str(self.review_text)
        return_string  += "\nReview Page No: " + self.str(self.review_page_no)
        return return_string