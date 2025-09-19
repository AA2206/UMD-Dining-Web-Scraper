import scrapy
from umdDiningScrapper.items import entreeItem
from scrapy_playwright.page import PageMethod
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

class MenuSpider(scrapy.Spider):
    name = "MenuSpider"
    allowed_domains = ["nutrition.umd.edu"]
    start_urls = ["https://nutrition.umd.edu"]

    def start_requests(self):
        url = "https://nutrition.umd.edu"
        yield scrapy.Request(
            url,
            meta={"playwright": True, "playwright_include_page": True}
        )
    
    async def parse(self, response):
        page = response.meta["playwright_page"]
        await page.wait_for_selector("select#location-select-menu.form-select")

        diningHalls = await page.query_selector_all("select#location-select-menu.form-select option")

        for hall in diningHalls:
            link = "?locationNum=" + await hall.get_attribute("value")
            Dining_Hall = await hall.inner_text(); 
            dining_url = response.urljoin(link)

            yield scrapy.Request(
                dining_url,
                callback=self.parse_dining,
                meta={
                    "dining_hall": Dining_Hall,
                    "playwright": True,  
                    "playwright_include_page": True,
                }
            )
    
        await page.close()

    async def parse_dining(self, response):
        page = response.meta["playwright_page"]

        entree_page = await page.context.new_page()

        await page.wait_for_selector("ul.nav.nav-tabs li.nav-item a.nav-link")

        meals = await page.query_selector_all("ul.nav.nav-tabs li.nav-item a.nav-link")

        for meal in meals:
            meal_name = (await meal.inner_text()).strip()
            href = await meal.get_attribute("href")

            # Click the tab
            await meal.click()
            await page.wait_for_selector("div.tab-pane.active.show div.row.menu-item-row", timeout=5000)

            # Capture updated HTML
            content = await page.content()
            new_response = response.replace(body=content)
            new_response.meta["meal_name"] = meal_name
            new_response.meta["dining_hall"] = response.meta["dining_hall"]

            new_response.meta["entree_page"] = entree_page  

            # Call parse_meal_page with updated HTML
            async for item in self.parse_meal_page(new_response):
                yield item

        await entree_page.close()
        await page.close()
    
    async def parse_meal_page(self, response):
        entree_page = response.meta["entree_page"]

        entree_items = response.css(
            'div.tab-pane.fade.active.show div.row.menu-item-row'
        )

        entree_data = []
        for entree in entree_items:
            href = entree.css('a.menu-item-name::attr(href)').get()
            dietary_labels = entree.css('img.nutri-icon')
            entree_url = response.urljoin(href)

            dietary_info = dietary_labels[0].attrib.get('alt') if dietary_labels else None

            for i in range(1, len(dietary_labels)):
                dietary_info += ", " + dietary_labels[i].attrib.get('alt')
            
            entree_data.append({
                "url": response.urljoin(href),
                "dietary_info": dietary_info
            })

        for entree in entree_data:
            item_meta = response.meta.copy()
            item_meta['dietary_info'] = entree["dietary_info"]

            try:
                await entree_page.goto(entree["url"])
                await entree_page.wait_for_selector("table.facts_table span.nutfactstopnutrient", timeout=10000)
            except PlaywrightTimeoutError:
                self.logger.warning(f"Skipping {entree['url']} — table not found")
                continue

            entree_html = await entree_page.content()
            entree_response = response.replace(body=entree_html, url=entree["url"])
            entree_item = self.parse_entree_page(entree_response, item_meta)
            
            yield entree_item
    
    def parse_entree_page(self, response, meta):
        entree_item = entreeItem()

        nutritional_values = response.css('table.facts_table tbody tr td span.nutfactstopnutrient')

        entree_item["Entree"] = response.css(
            "div.editor-content.text-center h2::text"
        ).get()
        entree_item["Dining_Hall"] = meta["dining_hall"]
        entree_item['Meal'] = meta['meal_name']
        entree_item['Dietary_Information'] = meta['dietary_info']
        
        calories = response.css(
            'table.facts_table tbody tr td:first-child p:nth-of-type(2)::text'
        ).get()

        if calories:
            entree_item['Total_Calories'] = int(calories.strip())
        else:
            entree_item['Total_Calories'] = None

        for span in nutritional_values:
            texts = span.css('::text').getall()
            full_text = ''.join(texts).replace('\xa0', ' ').strip()

            nutrient_name = span.css('b::text').get()
            if nutrient_name:
                nutrient_name = nutrient_name.replace('\xa0', ' ').strip()
                value = full_text.replace(nutrient_name, '').strip()
            else:
                parts = full_text.split()
                if len(parts) > 1:
                    nutrient_name = ' '.join(parts[:-1]) 
                    value = parts[-1]                   
                else:
                    nutrient_name = full_text
                    value = None

            clean = value.lower().replace("mg", "").replace("mcg", "").replace("g", "").strip() if value is not None else None

            if "Total Fat" in nutrient_name:
                entree_item["Total_Fat"] = self.safe_float(clean)
            elif "Saturated Fat" in nutrient_name:
                entree_item["Saturated_Fat"] = self.safe_float(clean)
            elif "Trans Fat" in nutrient_name:
                entree_item["Trans_Fat"] = self.safe_float(clean)
            elif "Cholesterol" in nutrient_name:
                entree_item["Cholesterol"] = self.safe_float(clean)
            elif "Sodium" in nutrient_name:
                entree_item["Sodium"] = self.safe_float(clean)
            elif "Total Carbohydrate" in nutrient_name:
                entree_item["Total_Carbohydrate"] = self.safe_float(clean)
            elif "Dietary Fiber" in nutrient_name:
                entree_item["Dietary_Fiber"] = self.safe_float(clean)
            elif "Total Sugars" in nutrient_name:
                entree_item["Total_Sugars"] = self.safe_float(clean)
            elif "Protein" in nutrient_name:
                entree_item["Protein"] = self.safe_float(clean)
            
        return entree_item
    
    def safe_float(self, value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
