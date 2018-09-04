import timeit
import urllib.request
from bs4 import BeautifulSoup as Bs
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import re
import time
import sqlite3
import datetime


def create_driver(is_CSS_BLOCKED, is_IMAGES_BLOCKED, is_JS_BLOCKED, is_HEADLESS_MODE):
    """
    Setup the Selenium Browser with Firefox and some profile-configs.
    JS-Block dont work i think since 2018.

    :param is_CSS_BLOCKED: True = Block
    :param is_IMAGES_BLOCKED: True = Block
    :param is_JS_BLOCKED: True = Block

    :return: webdriver firefox
    """
    print("Create Driver")

    firefoxProfile = FirefoxProfile()

    if is_IMAGES_BLOCKED:
        firefoxProfile.set_preference('permissions.default.image', 2)  # Images aus

    if is_CSS_BLOCKED:
        firefoxProfile.set_preference('permissions.default.stylesheet', 2)  # CSS aus

    if is_JS_BLOCKED:
        firefoxProfile.set_preference("javascript.enabled", False)  # JavaScript aus

    if is_HEADLESS_MODE:
        options = Options()
        options.add_argument("--headless")

        driver = webdriver.Firefox(firefox_options=options, firefox_profile=firefoxProfile)

    if not is_HEADLESS_MODE:
        driver = webdriver.Firefox(firefoxProfile)
        driver.minimize_window()

    print("Driver created")
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
    :return: Datum in sqlite Format (Textvariante)
    """
    soup = Bs(soup, "html.parser")  # Need an explizit cast due to ducktyping problems with the find() in Python and BS

    time_box = soup.find("a", attrs={"class": "time"})
    upload_time = str(time_box["title"])

    # Rename Monthnames to Englisch

    # Januar - Keine Veränderung
    # Februar - Keine Veränderung
    # März
    upload_time = upload_time.replace("Mär", "Mar")
    # April - Keine Veränderung
    # Mai
    upload_time = upload_time.replace("Mai", "May")
    # Juni - Keine Veränderung
    # Juli - Keine Veränderung
    # August - Keine Veränderung
    # September - Keine Veränderung
    # Oktober
    upload_time = upload_time.replace("Okt", "Oct")
    # November - Keine Veränderung
    # Dezember
    upload_time = upload_time.replace("Dez", "Dec")

    upload_time = datetime.datetime.strptime(upload_time, '%d. %b %Y - %H:%M')

    return upload_time


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


def check_soup(soup):
    """
    Prüft ob der Seitenquelltext erfolgreich ausgelesen werden kann
    :param soup:
    :return: Success 0, Unbekannter Fehler -1, NSFW 1, NSFL 2, Image not there 3, 503 Server error 503
    """
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

    return 0


def print_data_programm_new(new_id):
    """
    Gibt alle Daten zu einem Post aus (Benis, Uploaddatum, Uploader, Tags...)
    :param new_id:
    :return: Success 0, Unbekannter Fehler -1, NSFW 1, NSFL 2, Image not there 3, 503 Server error 503
    """
    print("\n" + "https://pr0gramm.com/new/" + str(new_id) + "\n")

    soup = get_site_soup("https://pr0gramm.com/new/" + str(new_id)).prettify()
    soup_error = check_soup(soup)

    # Prüfen ob Soup auswertbar ist
    if soup_error != 0:
        return soup_error

    # Soup auswerten
    benis = get_benis(soup)
    upload_time = get_upload_datum(soup)
    uploader_name = get_uploader_name(soup)
    tags_good = get_good_tags(soup)
    tags_bad = get_bad_tags(soup)

    # Bildschirmausgabe
    print("Benis: " + benis)
    print("Uploaddatum: " + str(upload_time))
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

    print("Create POSTS TABLE")
    cursor.execute("""CREATE TABLE IF NOT EXISTS posts
             (new_id INTEGER PRIMARY KEY NOT NULL,
              uploader TEXT,
              upload_date TEXT,
              benis INTEGER,
              SFW INTEGER,
              NSFW INTEGER,
              NSFL INTEGER)""")

    print("POSTS TABLE Created")

    # TAGS-TABELLE

    print("Create TAGS TABLE")
    cursor.execute("""CREATE TABLE IF NOT EXISTS tags
             (new_id INTEGER ,
              tag TEXT,
              good_tag INTEGER)""")

    print("TAGS TABLE Created")

    # # Testdaten einfügen und speichern
    # cursor.execute("INSERT INTO posts VALUES (0, 'Testbert',  'YYYY-MM-DD HH:MM:SS.SSS' , 42,1,0,0)")
    # cursor.execute("INSERT INTO tags VALUES (0, 'Lang lebe Kurz', 0)")
    #
    connection.commit()
    #
    # # Auslesen und ausgeben
    # cursor.execute('SELECT * FROM posts')
    # print(cursor.fetchall())
    #
    # cursor.execute('SELECT * FROM tags')
    # print(cursor.fetchall())


def write_post_and_tags_to_db(cursor, connection, new_id, uploader, upload_date,
                              benis, is_SFW, is_NSFW, is_NSFL, good_tags, bad_tags):
    """
    Write all data of a post to the database including the tags and safe the change
    :param cursor:
    :param connection:
    :param new_id:
    :param uploader:
    :param upload_date:
    :param benis:
    :param is_SFW:
    :param is_NSFW:
    :param is_NSFL:
    :param good_tags:
    :param bad_tags:
    :return:
    """
    # Posts
    cursor.execute("INSERT INTO posts "
                   "(new_id, uploader, upload_date, benis, SFW, NSFW, NSFL)"
                   "VALUES (?,?,?,?,?,?,?)" ,
                   (new_id, uploader, upload_date, benis, is_SFW, is_NSFW, is_NSFL))

    # Tags

    # Good-Tags
    for tag in good_tags:
        cursor.execute("INSERT INTO tags"
                       "(new_id, tag, good_tag)"
                       "VALUES (?,?,?)" ,
                       (new_id, tag, 1))

    # Bad-Tags
    for tag in bad_tags:
        cursor.execute("INSERT INTO tags"
                       "(new_id, tag, good_tag)"
                       "VALUES (?,?,?)",
                       (new_id, tag, 0))

    # Commit
    connection.commit()


#####################################
#####################################
###########MAIN-BEGIN################
#####################################
#####################################

# Datenbank Anfang
connection, cursor = connect_sqlite_db_and_cursor("pr0.db")
create_tables(cursor, connection)

# Driver create
driver = create_driver(False, False, True, True)

start = timeit.default_timer()

# Bildschirmausgabe
# for i in range(1, 101):
#     error = print_data_programm_new(i)
#
#     # On Server-error cause of too many request by this programm wait a few seconds
#     while error == 503:
#         time.sleep(10)
#         print("Wait 10 Seconds")
#         error = print_data_programm_new(i)

# In pr0gramm.com-Postdaten in Datenbank schreiben
for i in range(1, 101):
    soup = get_site_soup("https://pr0gramm.com/new/" + str(i)).prettify()
    error = check_soup(soup)
driver.close()

stop = timeit.default_timer()
print()
print("################################################")
print('Durchlaufzeit: ', stop - start)



# Datenbank Anfang
#connection, cursor = connect_sqlite_db_and_cursor("pr0.db")
#create_tables(cursor, connection)