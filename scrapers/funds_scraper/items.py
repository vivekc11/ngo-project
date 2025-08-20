import scrapy

class ListPagesItem(scrapy.Item):
    url = scrapy.Field()
    html = scrapy.Field()

class GrantPagesItem(scrapy.Item):
    url = scrapy.Field()
    html = scrapy.Field()