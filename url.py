class URL:
    def __init__(self, url):
        self.url_details = {
            "Url": url.strip('\n'),
        }
         
    def __str__(self) -> str:
        return f'This is a URL: {self.url_details}'
    
    def __repr__(self) -> str:
        return f'This is a URL: {self.url_details}'