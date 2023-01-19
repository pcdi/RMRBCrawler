import datetime
import re

import scrapy


class RMRBSpider(scrapy.Spider):
    name = "rmrb"
    base_url = "http://paper.people.com.cn/"
    date = datetime.date(2023, 1, 19)

    def start_requests(self):
        edition_url = self.base_url + f"rmrb/html/{self.date.strftime('%Y-%m/%d')}/nbs.D110000renmrb_01.htm"
        yield scrapy.Request(url=edition_url, callback=self.get_toc)

    def get_toc(self, response):
        page_links = response.css("#pageLink::attr(href)").getall()
        for page_link in page_links:
            if page_link is not None:
                next_page = response.urljoin(page_link)
                yield scrapy.Request(url=next_page, callback=self.parse_page)

    def parse_page(self, response):
        article_links = response.css(".news a::attr(href)").getall()
        for article_link in article_links:
            if article_link is not None:
                next_article = response.urljoin(article_link)
                yield scrapy.Request(url=next_article, callback=self.parse_article)

    def parse_article(self, response):
        article_images = response.css("table.pci_c")
        article_images_list = []
        for image in article_images:
            image_caption = response.css("table.pci_c")[0].css("p").get().split("<br>")
            image_authors = split_authors(image_caption[1].removesuffix("</p>").replace("\u3000", "").removeprefix(
                "新华社记者 ")) if len(image_caption) > 1 else None,
            article_images_list.append({
                "image_url": response.urljoin(image.css("img::attr(src)").get()),
                # "image_title": image_caption[0].removeprefix("<p>").replace("\u3000", ""),
                "image_caption":  response.css("table.pci_c *::text").getall(),
                "image_authors": image_authors,
            })

        article_paragraphs = response.css("#ozoom p::text").getall()
        article_paragraphs_list = []
        for paragraph in article_paragraphs:
            article_paragraphs_list.append(paragraph.replace("\u3000", "").replace("\xa0", ""))

        authors_list = split_authors(response.css(".sec::text").getall()[1].strip().removeprefix("本报记者  "))
        if len(authors_list) == 0 and len(article_paragraphs_list) > 0:
            authors_list = re.findall('(?:（记者)([^）]+)(?:）)', article_paragraphs_list[0])

        yield {
            "url": response.url,
            "page_number": re.findall('(\d{1,2})-(\d{2})\.htm$', response.url)[0][1],
            "article_number": re.findall('(\d{1,2})-(\d{2})\.htm$', response.url)[0][0],
            "title": response.css("h1::text").get(),
            "subtitle": response.css("h2::text").get(),
            "suptitle": response.css("h3::text").get(),
            "authors": authors_list,
            "citation": response.css(".sec .date::text").get().replace("\r", "").replace("\n", "").replace(" ",
                                                                                                           "").replace(
                "\xa0", ""),
            "article_paragraphs": article_paragraphs_list,
            "article_images": article_images_list
        }

    def parse(self, response, **kwargs):
        pass


def split_authors(authors: str) -> list:
    authors_list = []
    authors = authors.replace("  ", " ")
    for index in range(0, len(authors) - 2, 4):
        authors_list.append(authors[index:index + 3].replace(" ", ""))
    return authors_list
