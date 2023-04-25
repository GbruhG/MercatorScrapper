from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime
import time

uri = "mongodb+srv://gregor:L0K0M0TIVA@mercatordb.ubbzi9v.mongodb.net/?retryWrites=true&w=majority"

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

# Set up the web driver
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run the driver in headless mode (no GUI)
driver = webdriver.Chrome(options=options)

# Navigate to the webpage
url = "https://trgovina.mercator.si/market/brskaj#"
driver.get(url)

# Wait for the desired elements to load on the page
wait = WebDriverWait(driver, 10)  # Wait for up to 10 seconds
wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "box.item.product.rotation.size11")))

# Parse the HTML content of the page using Beautiful Soup
soup = BeautifulSoup(driver.page_source, "html.parser")
#print(soup)

product_counter = 0
product_links = set()

# Loop through the product divs and extract the desired information
while True:
    # Find all the product divs on the page
    product_divs = soup.find_all("div", {"class": "box item product rotation size11"})
    # If there is no more content to load, break out of the loop
    if len(product_divs) == 0:
        break

    for product_div in product_divs:
        # Find the div element with class "product-description"
        description_div = product_div.find("div", {"class": "product-description"})
        
        # Extract the product name from the "product-name" 
        product_name_link = description_div.find("a", {"class": "lib-product-name"})
        product_name = product_name_link.text.strip()
        product_link = "https://trgovina.mercator.si" + product_name_link.get('href')
        
        # If we have already seen this product link, skip it
        if product_link in product_links:
            print(f"----------------DUPLICATE PRODUCT FOUND SKIPPING----------------")
            continue
        
        product_links.add(product_link)
        product_counter += 1
        
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

        print(f"----------------INSERTING PRODUCT #{product_counter} INTO DATABASE----------------")


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




    # Scroll down to the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Wait for the new content to load
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "box.item.product.rotation.size11")))



# Close the web driver
driver.quit()

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Retrieved and inserted {product_counter} products in {elapsed_time:.2f} seconds.")
