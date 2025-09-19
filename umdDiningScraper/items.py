# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class UmddiningscrapperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class entreeItem(scrapy.Item):
    Entree = scrapy.Field()
    Dining_Hall = scrapy.Field()
    Meal = scrapy.Field()
    Dietary_Information = scrapy.Field()
    Total_Calories = scrapy.Field() 
    Total_Fat = scrapy.Field()
    Saturated_Fat = scrapy.Field()
    Trans_Fat = scrapy.Field()
    Cholesterol = scrapy.Field()
    Sodium = scrapy.Field()
    Total_Carbohydrate = scrapy.Field()
    Dietary_Fiber = scrapy.Field()
    Total_Sugars = scrapy.Field()
    Protein = scrapy.Field()
