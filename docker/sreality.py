from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from scrapy.selector import Selector
from scrapy import Spider, Request
import pandas as pd
import psycopg2
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add print statements throughout the script
logger.debug("Starting sreality.py script...")

class SrealitySpider(Spider):
    name = 'sreality'
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1
    }

    def __init__(self):
        self.driver = webdriver.Chrome()
        self.all_urls = ['https://www.sreality.cz/en/search/for-sale/apartments']  # Add the first URL directly
        self.all_urls += [f'https://www.sreality.cz/en/search/for-sale/apartments?strana={i}' for i in range(2, 5)]  # Add the rest of the URLs
        self.all_urls += ['https://www.sreality.cz/en/search/for-sale/apartments']  # Add the first URL directly
        self.output_dir = '/usr/share/nginx/html'  # Output directory for static HTML files

        logger.debug("Connect to the PostgreSQL database")
        # Connect to the PostgreSQL database
        self.conn = psycopg2.connect(
            database="docker",
            user="docker",
            password="docker",
            host="localhost",
            port="5432",
        )

        # Create a cursor object
        self.cur = self.conn.cursor()

        logger.debug("Create the schema and table if they don't exist")
        # Create the schema if it doesn't exist
        self.cur.execute("CREATE SCHEMA IF NOT EXISTS docker;")

        logger.debug("Create the sreality table if it doesn't exist")
        # Create the sreality table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS docker.sreality (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                image_url VARCHAR(255),
                page_number INTEGER
            );
        """)

        # Commit the changes
        self.conn.commit()


    def start_requests(self):
        for url in self.all_urls:
            yield Request(url, self.parse)

    def parse(self, response):
        self.driver.get(response.url)

        # Wait for the page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.property.ng-scope'))
        )

        sel = Selector(text=self.driver.page_source)
        data = []
        for item in sel.css('div.property.ng-scope'):
            title = item.css('a.title span.name.ng-binding::text').get()
            image_url = item.css('a._2vc3VMce92XEJFrv8_jaeN img::attr(src)').get()
            
            # Get the page number from the URL
            page_number = response.url.split('=')[-1]

            data.append((title, image_url, page_number))
        logger.debug(data)
        df = pd.DataFrame(data, columns=['Title', 'Image URL', 'Page'])
        logger.debug(df)

        logger.debug("Write data to HTML file")
        # Write data to HTML file
        filename = f"{self.output_dir}/data_{page_number}.html"
        with open(filename, 'w') as f:
            f.write('<html><head><title>Sreality Data</title></head><body>')
            f.write('<h1>Sreality Data</h1>')
            f.write('<table border="1"><tr><th>Title</th><th>Image URL</th></tr>')
            for index, row in df.iterrows():
                f.write(f'<tr><td>{row["Title"]}</td><td>{row["Image URL"]}</td></tr>')
            f.write('</table></body></html>')

        logger.debug("Insert the data into the database")
        # Insert the data into the database
        for index, row in df.iterrows():
            self.cur.execute(
                "INSERT INTO sreality (title, image_url, page) VALUES (%s, %s, %s)",
                (row['Title'], row['Image URL'], row['Page'])
            )

        # Commit the changes
        self.conn.commit()

    def closed(self, reason):
        print(self.all_urls)  # Print all the URLs
        self.driver.quit()