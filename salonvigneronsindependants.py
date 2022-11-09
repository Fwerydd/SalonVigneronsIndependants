import csv
from enum import Enum
import math
import re
import typing

from bs4 import BeautifulSoup
import requests
import typer


headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
}

COLOR_HTML_TEXT = 'Couleur : '


class NumberOfItemsChoice(str, Enum):
    five = '5'
    ten = '10'
    twenty = '20'
    forty = '40'
    sixty = '60'


def parse_establishment_information(establishment_url: str) -> typing.Optional[list[str]]:
    # Parse URL
    req = requests.get(establishment_url, headers)
    soup = BeautifulSoup(req.content, 'html.parser')

    # Retrieve establishment name
    establishment_name = soup.find('h2', class_='pane-title')
    establishment_name_text = establishment_name.text.strip(
    ) if establishment_name is not None else ''

    # Retrieve all shows information
    show_blocs = soup.find_all('div', class_='establishment-show-desc')
    stand_text = ''
    for show_bloc in show_blocs:
        # Convert data to BeautifulSoup object
        show_bloc_soup = BeautifulSoup(str(show_bloc), 'html.parser')

        # Parse bloc data
        show_place_soup = show_bloc_soup.find('div', class_='establishment-show-place')
        if show_place_soup is not None and 'Paris' in show_place_soup.text.strip():
            show_stand_soup = show_bloc_soup.find('div', class_='establishment-show-stand')
            if show_stand_soup is not None:
                stand_text = show_stand_soup.text.strip()
                break

    # Retrieve all wines information
    wine_blocs = soup.find_all('div', class_='wine-bloc')
    for wine_bloc in wine_blocs:
        # Convert data to BeautifulSoup object
        wine_bloc_soup = BeautifulSoup(str(wine_bloc), 'html.parser')

        # Parse bloc data
        wine_name_soup = wine_bloc_soup.find('div', class_='wine-name')
        wine_place_soup = wine_bloc_soup.find('div', class_='wine-place')
        wine_competitions_soup = wine_bloc_soup.find('li', class_='i-concours')
        wine_col_first_soup = wine_bloc_soup.find('div', class_='wine-col first')

        # Retrieve wine texts
        wine_name_soup_text = wine_name_soup.text.strip() if wine_name_soup is not None else ''
        wine_place_soup_text = wine_place_soup.text.strip() if wine_place_soup is not None else ''
        wine_competitions_soup_text = wine_competitions_soup.text.strip() if wine_competitions_soup is not None else ''
        wine_col_first_soup_text = ''

        if wine_col_first_soup is not None:
            wine_col_first_lis_soup = wine_bloc_soup.find_all('li')
            for wine_col_first_li_soup in wine_col_first_lis_soup:
                wine_col_first_li_soup_text = wine_col_first_li_soup.text.strip()
                if wine_col_first_li_soup_text.startswith(COLOR_HTML_TEXT):
                    wine_col_first_soup_text = wine_col_first_li_soup.text.replace(COLOR_HTML_TEXT, '')

        # Write entry in the CSV file
        return [
            establishment_name_text,
            stand_text,
            wine_name_soup_text.replace(establishment_name_text + ' ', ''),
            wine_col_first_soup_text,
            wine_place_soup_text,
            wine_competitions_soup_text
        ]


def extract_salon_number_establishment(salon_url: str) -> typing.Optional[int]:
    number_of_establishments = None

    # Parse URL
    salon_url_req = requests.get(salon_url, headers)
    salon_url_soup = BeautifulSoup(salon_url_req.content, 'html.parser')

    # Retrieve number of establishment(s)
    establishment_number = salon_url_soup.find('div', class_='search-performance')
    establishment_number_text = establishment_number.text.strip(
    ) if establishment_number is not None else None

    # Extract number of establishments
    if establishment_number_text is not None:
        number_of_establishments_regex_results = re.findall(r'\d+', establishment_number_text)
        if len(number_of_establishments_regex_results) == 1:
            number_of_establishments = int(number_of_establishments_regex_results[0])

    return number_of_establishments


def main(salon_id: int = 128555, items_per_page: NumberOfItemsChoice = '60'):
    # URLs
    base_url = 'https://www.vigneron-independant.com'
    salon_url = base_url + '/search-salon?keywords=&salon=' + str(salon_id)
    search_url = salon_url + '&items_per_page=' + str(items_per_page.value) + '&page='

    # Retrieve the number of establishments
    max_results = extract_salon_number_establishment(salon_url)

    try:
        # Determine the number of iteration to find all establishments
        nb_iteration = math.ceil(max_results/int(str(items_per_page.value)))

        # Open the output file
        with open('stands.csv', 'w', newline='', encoding='utf-8-sig') as csv_file:
            csv_writer = csv.writer(
                csv_file,
                delimiter=',',
                quotechar='|',
                quoting=csv.QUOTE_MINIMAL
            )
            csv_writer.writerow(['Nom', 'Stand', 'Vin', 'Couleur', 'Lieu', 'Concours'])

            for page_index in range(1, nb_iteration+1):
                # Parse URL
                base_req = requests.get(search_url + str(page_index), headers)
                base_soup = BeautifulSoup(base_req.content, 'html.parser')

                # Parse bloc data
                result_names_soup = base_soup.find_all('div', class_='result-name')
                for result_name_soup in result_names_soup:
                    # Convert data to BeautifulSoup object
                    result_name_bloc_soup = BeautifulSoup(
                        str(result_name_soup), 'html.parser')
                    result_link_soup = result_name_bloc_soup.find('a')
                    if (
                            result_link_soup is not None and
                            result_link_soup.attrs is not None and
                            result_link_soup.attrs['href'] is not None
                    ):
                        establishment_url = base_url + \
                            result_link_soup.attrs['href']
                        row = parse_establishment_information(establishment_url=establishment_url)
                        csv_writer.writerow(row)

                        # Force file writing
                        csv_file.flush()
    except (TypeError, ValueError, ZeroDivisionError) as error:
        print(error)


if __name__ == '__main__':
    typer.run(main)
