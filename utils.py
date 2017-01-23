import csv

from scrape_quotes import OUTPUT_FILE_DELIMITER


def read_bens_quotes_file(file_path):
    content = []
    with open(file_path, newline='') as csvfile:
        content_reader = csv.reader(csvfile, delimiter=OUTPUT_FILE_DELIMITER)
        for row in content_reader:
            content.append(row)
    return content
