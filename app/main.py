from notifiers import get_notifier
from requests import get
from bs4 import BeautifulSoup
from time import sleep
import re
import os

TOKEN = os.environ.get('TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
SITE_BASE_URL = 'https://www.avito.ru'


def get_search_url(text: str, price: int, reporter_type: int):
    base_url = SITE_BASE_URL + '/moskva/noutbuki'
    price = '?pmax=' + str(price)
    query = '&q=' + text
    reporter = '&user=' + str(reporter_type)
    order = '&s=104'
    return base_url + price + query + reporter + order


def send_notifications(token: str, chat_id: str, notifications_list: list):
    for notification_text in notifications_list:
        telegram = get_notifier('telegram')
        telegram.notify(message=notification_text, token=token, chat_id=chat_id)


def get_price(div_content):
    price_span = div_content.find('span', attrs={'class': re.compile('price-price-.*')})
    price = price_span.find('meta', itemprop='price').attrs['content']
    price_currency = price_span.find('meta', itemprop='priceCurrency').attrs['content']
    return price + ' ' + price_currency


def get_link_and_name(div_content):
    link = div_content.find('div', attrs={'class': re.compile('iva-item-titleStep.*')}).find('a')
    return SITE_BASE_URL + link.attrs['href'], link.attrs['title']


def get_info(div):
    link, name = get_link_and_name(div)
    price = get_price(div)
    return link, name, price


def parse(soup):
    results = list()
    for div in soup.find_all('div', attrs={'class': re.compile('iva-item-content-.*')}):
        if div.find():
            results.append(get_info(div))
    return results


def enrich_seller_names(results: list):
    results_with_names = []
    for info in results:
        results_with_names.append((*info, get_seller_link(info[0])))
    return results_with_names


def get_seller_link(link: str):
    html_text = get(link).text
    soup = BeautifulSoup(html_text, 'html.parser')
    seller_div = soup.find('div', attrs={'class': re.compile('seller-info-name')})
    seller_a = seller_div.find('a')
#    seller_link = seller_a.attrs['href']
#    seller_name = seller_a.text
    return seller_a.prettify( formatter="html" ) #seller_link, seller_name


def prettify_result(result: list):
    pretty_result = []
    for entry in result:
        text = entry[1] + '\n' + entry[0] + '\n' + entry[2] # + "\n From\n" + entry[3]
        pretty_result.append(text)
    return pretty_result


def compile_notification(search_results: list):
    notification_entries = list()
    for result in search_results:
        notification_entries.append(result)
    return prettify_result(notification_entries)


def filter_results(search_results: list, cache: set):
    filtered_results = []
    for result in search_results:
        if not result[0] in cache:
            cache.add(result[0])
            filtered_results.append(result)
    return filtered_results


def update_cache(results: list, cache: set):
    for result in results:
        cache.add(result[0])


def main(cache: set):
    html_text = get(get_search_url('ноутбуки', 4000, 0)).text
    soup = BeautifulSoup(html_text, 'html.parser')

    search_results = parse(soup)
    filtered_results = filter_results(search_results, cache)
#    search_results_with_names = enrich_seller_names(filtered_results)

    notifications = compile_notification(filtered_results)  #search_results_with_names)
    send_notifications(TOKEN, CHAT_ID, notifications)
    update_cache(filtered_results, cache)
    print('Count {}'.format(len(cache)))


if __name__ == '__main__':
    cache = set()
    while True:
        try:
            main(cache)
            sleep(10)
        except Exception as err:
            print(err)
            print(err.__traceback__)

