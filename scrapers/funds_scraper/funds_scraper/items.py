import scrapy

class GrantItem(scrapy.Item):
    title = scrapy.Field()
    deadline = scrapy.Field()
    country = scrapy.Field()
    description = scrapy.Field()
    url = scrapy.Field()
