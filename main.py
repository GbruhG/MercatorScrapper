from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime
import time

uri = "" #mongodb uri

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client["mercator"]
collection = db["products"]

start_time = time.time()

# Array of all the product categories that the program will go through because beautifulsoup breaks if you do over 2200 products on one page 
urls = ["https://trgovina.mercator.si/market/brskaj#categories=14535405;offset=0",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535446",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535463",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535481",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535512",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535548",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535588",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535612",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535661",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535681",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535711",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535736",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535749",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535768",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535803",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535810",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535837",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535864",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535906",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535941",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14535984",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14536021",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14536058",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=14536089",    "https://trgovina.mercator.si/market/brskaj#offset=0;categories=16873196"]

total_products = 0
for url in urls:
    # Set up the web driver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "box.item.product.rotation.size11")))
    soup = BeautifulSoup(driver.page_source, "html.parser")
    numberOfProducts = int(soup.find("span", {"class": "product-find-counter"}).text.strip()) #Finds the number of products to extract
    print(f"----------------STARTING TO EXTRACT NEW CATEGORY----------------")
    print(url)
    print(numberOfProducts)
    product_links = set()
    product_counter = 0
    # Loop through the product divs and extract the desired information
    while product_counter <= numberOfProducts:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # Find all the product divs on the page
        product_divs = soup.find_all("div", {"class": "box item product rotation size11"})

        if product_counter == numberOfProducts:
            break

        for product_div in product_divs:
            # Find the div element with class "product-description"
            description_div = product_div.find("div", {"class": "product-description"})
            
            # Extract the product name from the "product-name" 
            product_name_link = description_div.find("a", {"class": "lib-product-name"})
            product_name = product_name_link.text.strip()
            product_link = "https://trgovina.mercator.si" + product_name_link.get('href')

            if product_counter == numberOfProducts:
                break
            # If we have already seen this product link, skip it
            if product_link in product_links:
                if product_counter == numberOfProducts:
                    break
                print(f"----------------DUPLICATE PRODUCT FOUND SKIPPING----------------")
                continue
            
            product_counter += 1
            total_products += 1

            product_links.add(product_link)
            
            print("Product name:", product_name)
            print("Product link:", product_link)

            # Extract the price from the "price" 
            price = description_div.find("strong", {"class": "lib-product-price"}).text.strip()
            print("Price:", price)

            # Extract the image source from the "product-image" 
            product_image_link = product_div.find("div", {"class": "default sideA lib-cart"}).find("a", {"class": "product-image"})
            product_image = product_image_link.find("img").get("src")
            print("Product image:", product_image)

            # Create a new document to insert into the MongoDB collection
            document = {
                "name": product_name,
                "image": product_image,
                "link": product_link,
                "prices": [
                    {
                        "value": price,
                        "date": datetime.datetime.now()
                    }
                ],
            }

            print(f"----------------INSERTING PRODUCT #{product_counter} INTO DATABASE | TOTAL PRODUCTS: {total_products} | NUMBER OF PRODUCTS: {numberOfProducts}----------------")

            existing_document = collection.find_one({"name": product_name})
            if existing_document:
                # If the product exists, append the new price to the "prices" array
                existing_document["prices"].append({
                    "value": price,
                    "date": datetime.datetime.now()
                })
                # Update the existing document with the new price
                collection.replace_one({"_id": existing_document["_id"]}, existing_document)
            else:
                # If the product does not exist, insert the new document into the collection
                collection.insert_one(document)

        if product_counter == numberOfProducts:
                break
        
        # Wait for the new content to load
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='box item product rotation size11'][last()]")))

        # Scroll down to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

# Close the web driver
driver.quit()

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Retrieved and inserted {total_products} products in {elapsed_time:.2f} seconds.")

