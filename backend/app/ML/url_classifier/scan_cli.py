from predict import scan_url

# Test some URLs
urls = [
    "http://secure-login.paypal.com.fake.com",
    "https://www.google.com"
]

for url in urls:
    result = scan_url(url)
    print(result)
