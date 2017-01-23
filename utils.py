import csv

from scrape_quotes import OUTPUT_FILE_DELIMITER


def read_bens_quotes_file(file_path):
    """Reads file containing either scraped posts or quotes.

    :param file_path: Path to the file.
    :return: The scraped data.
    """
    content = []
    with open(file_path, newline='') as csvfile:
        content_reader = csv.reader(csvfile, delimiter=OUTPUT_FILE_DELIMITER)
        for row in content_reader:
            content.append(row)
    return content
