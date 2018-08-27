import timeit
import urllib.request
from bs4 import BeautifulSoup as Bs
from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import re
import time
import sqlite3


def create_driver(CSS_BLOCK, IMAGES_BLOCK, JS_BLOCK):
    """
    Setup the Selenium Browser with Firefox and some profile-configs.
    JS-Block dont work i think since 2018.

    :param CSS_BLOCK: True = Block
    :param IMAGES_BLOCK: True = Block
    :param JS_BLOCK: True = Block
    :return: webdriver firefox
    """

    firefoxProfile = FirefoxProfile()

    if IMAGES_BLOCK:
        firefoxProfile.set_preference('permissions.default.image', 2)  # Images aus

    if CSS_BLOCK:
        firefoxProfile.set_preference('permissions.default.stylesheet', 2)  # CSS aus

    if JS_BLOCK:
        firefoxProfile.set_preference("javascript.enabled", False)  # JavaScript aus

    driver = webdriver.Firefox(firefoxProfile)
    driver.minimize_window()

    return driver


def get_benis(soup):
    """
    Scrap the soup for the current Benis

    <span class="score" title="9095 up, 149 down">8946</span>
    :return: Benis (int)
    """
    soup = Bs(soup, "html.parser")  # Need an explizit cast due to ducktyping problems with the find() in Python and BS

    benis_box = soup.find("span", attrs={"class": "score"})
    benis = benis_box.text.strip()
    return benis


def get_upload_datum(soup):
    """
    Scrap the soup for the upload Datum

    <a class="time" title="23. Jan 2007 - 21:41" href="/new/1">vor 12 Jahren</a>
    :return: Datum in the format : 23. Jan 2007 - 21:41
    """
    soup = Bs(soup, "html.parser")  # Need an explizit cast due to ducktyping problems with the find() in Python and BS

    time_box = soup.find("a", attrs={"class": "time"})
    time = time_box["title"]
    return time


def get_uploader_name(soup):
    """
    Scrap the soup for the uploader_name

    <a href="/user/cha0s" class="user um3">cha0s</a>
    :return: uploader_name (str)
    """
    soup = Bs(soup, "html.parser")  # Need an explizit cast due to ducktyping problems with the find() in Python and BS

    #uploader_box = soup.find("a", attrs={"class": "user um3"}) # Es gibt mehrere Verschiedene user um3 und um2 , um0 evtl. weitere...
    uploader_box = soup.find("a", attrs={"class": re.compile("user um.*")})
    uploader_name = uploader_box.text.strip()
    return uploader_name


def get_good_tags(soup):
    """
    Good Tags are the Tags with a positive rating (Benis > 0)
    :param soup:
    :return: A List of all positiv tags
    """
    soup = Bs(soup, "html.parser")  # Need an explizit cast due to ducktyping problems with the find() in Python and BS

    # Alle Guten Tags filtern
    good_tags_soup = soup.find_all("span", attrs={"class": "tag tag-good"})
    good_tags = []

    # Von jedem gefilterten Tag den Inhalt auslesen
    for tag_soup in good_tags_soup:
        tag = tag_soup.find("a", attrs={"class": "tag-link"}).text.strip()
        good_tags.append(tag)

    return good_tags


def get_bad_tags(soup):
    """
    Bad Tags are the Tags with a negativ rating (Benis < 0)
    :param soup:
    :return: A List of all bad tags
    """
    soup = Bs(soup, "html.parser")  # Need an explizit cast due to ducktyping problems with the find() in Python and BS

    # Alle Schlechten Tags filtern
    bad_tags_soup = soup.find_all("span", attrs={"class": "tag tag-bad"})
    bad_tags = []

    # Von jedem gefilterten Tag den Inhalt auslesen
    for tag_soup in bad_tags_soup:
        tag = tag_soup.find("a", attrs={"class": "tag-link"}).text.strip()
        bad_tags.append(tag)

    return bad_tags


def get_site_soup(url):
    """
    Leider nutzt das Pr0 eine JS-Abfrage, sodass ich mit Selenium diese umgehen muss -> langsam aber geht
    :param url:
    :return: Gibt ein BeautifulSoup Objekt zu der URL zurück
    """

    # OHNE JS-Abfrage wäre dies hier möglich
    #source = urllib.request.urlopen(url)
    #soup = Bs(source, "html.parser")
    #return soup

    driver.get(url)

    soup = Bs(driver.page_source, "html.parser")
    return soup


def print_data_programm_new(new_id):
    """
    Gibt alle Daten zu einem Post aus (Benis, Uploaddatum, Uploader, Tags...)
    :param new_id:
    :return: Success 0, Unbekannter Fehler -1, NSFW 1, NSFL 2, Image not there 3, Server error 503
    """
    print("\n" + "https://pr0gramm.com/new/" + str(new_id) + "\n")

    soup = get_site_soup("https://pr0gramm.com/new/" + str(new_id)).prettify()

    # prüfen ob Bild in SFW ist
    if "Melde dich an, wenn du es sehen willst" in soup:
        print("Bild ist nicht SFW!")

        if "NSFW" in soup:
            print("Bild ist NSFW!")
            return 1

        if "NSFL" in soup:
            print("Bild ist NSFL!")
            return 2

        return -1

    # prüfen ob Bild vorhanden ist
    if "Nichts gefunden ¯\_(ツ)_/¯" in soup:
        print("Bild ist nicht mehr verfügbar/gelöscht")
        return 3

    # Prüfen ob Server korrekt antwortet 503 Error abfangen
    if "503 Service Temporarily Unavailable" in soup:
        print("503 ERROR")
        return 503

    # ZOMFG Error abfangen
    if "Irgendwas Doofes ist passiert. Probier's später nochmal" in soup:
        print("ZOMFG ERROR")
        return 503

    benis = get_benis(soup)
    upload_time = get_upload_datum(soup)
    uploader_name = get_uploader_name(soup)
    tags_good = get_good_tags(soup)
    tags_bad = get_bad_tags(soup)

    print("Benis: " + benis)
    print("Uploaddatum: " + upload_time)
    print("Uploadername: " + uploader_name)
    print("Good Tags: ")
    print(tags_good)
    print("Bad Tags: ")
    print(tags_bad)

    return 0


def connect_sqlite_db_and_cursor(db_name):
    """
    Creates a connection to a sqlite3 db
    :param db_name: filename of the db
    :return: sqllite_connection , cursor Object
    """

    print("Connect to Database")
    sqllite_connection = sqlite3.connect(db_name)
    cursor_object = sqllite_connection.cursor()
    print("Database connected")

    return sqllite_connection, cursor_object


def close_sqlite_db(sqllite_connection):
    """
    Save and close the db
    :param sqllite_connection:
    :return:
    """
    print("Safe and Close Database")
    sqllite_connection.commit()
    sqllite_connection.close()
    print("Database safed and closed")

    return


def create_tables(cursor, connection):
    # WEGEN DATUM
    #http://www.sqlitetutorial.net/sqlite-date/

    # Tabellen anlegen
    # POSTS-TABELLE
    cursor.execute("""CREATE TABLE IF NOT EXISTS posts
             (new_id INTEGER PRIMARY KEY NOT NULL,
              uploader TEXT,
              upload_date TEXT,
              benis INTEGER,
              SFW INTEGER,
              NSFW INTEGER,
              NSFL INTEGER)""")

    # TAGS-TABELLE
    cursor.execute("""CREATE TABLE IF NOT EXISTS tags
             (new_id INTEGER ,
              tag TEXT,
              good_tag INTEGER)""")

    # Testdaten einfügen und speichern
    cursor.execute("INSERT INTO posts VALUES (0, 'Testbert',  'YYYY-MM-DD HH:MM:SS.SSS' , 42,1,0,0)")
    cursor.execute("INSERT INTO tags VALUES (0, 'Lang lebe Kurz', 0)")

    connection.commit()

    # Auslesen und ausgeben
    cursor.execute('SELECT * FROM posts')
    print(cursor.fetchall())

    cursor.execute('SELECT * FROM tags')
    print(cursor.fetchall())


#####################################
#####################################
###########MAIN-BEGIN################
#####################################
#####################################

driver = create_driver(False, False, True)

start = timeit.default_timer()

for i in range(1, 2):
    error = print_data_programm_new(i)

    # On Server-error cause of too many request by this programm wait a few seconds
    while error == 503:
        time.sleep(10)
        error = print_data_programm_new(i)

driver.close()

stop = timeit.default_timer()
print('Durchlaufzeit: ', stop - start)



# Datenbank Anfang
#connection, cursor = connect_sqlite_db_and_cursor("pr0.db")
#create_tables(cursor, connection)