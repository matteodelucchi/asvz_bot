#!/home/<user>/asvz_bot_python/bin/python

"""
Created on: Mar 20, 2019
Author: Julian Stiefel
Edited: Patrick Barton, October 2020
License: BSD 3-Clause
Description: Script for automatic enrollment in ASVZ classes
"""

############################# Edit this: ######################################

# ETH credentials:
username = 'xxxx'
password = 'xxxx'

###############################################################################

import time
import math
import argparse
import configparser
import geckodriver_autoinstaller
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


day2int = {'Montag': 0,
           'Dienstag': 1,
           'Mittwoch': 2,
           'Donnerstag': 3,
           'Freitag': 4,
           'Samstag': 5,
           'Sonntag': 6}


def waiting_fct():
    def get_lesson_datetime(day, train_time):
        # find next date with that weekday
        nextDate = datetime.today().date()
        while nextDate.weekday() != day2int[day]:
            nextDate += timedelta(days=1)

        # combine with training time for complete date and time object
        lessonTime = datetime.strptime(train_time, '%H:%M').time()
        return datetime.combine(nextDate, lessonTime)

    lessonTime = get_lesson_datetime(config['default']['day'], config['default']['lesson_time'])
    enrollmentTime = lessonTime - timedelta(hours=config['default'].getint('enrollment_time_difference'))

    # Wait till enrollment opens if script is started before registration time
    delta = enrollmentTime - datetime.today()
    while delta > timedelta(seconds=0):
        delta = enrollmentTime - datetime.today()
        print("Time till enrollment opens: " + str(delta))
        if delta < timedelta(minutes=1):
            time.sleep(math.ceil(delta.total_seconds()))
        else:
            time.sleep(60)
    return


def asvz_enroll(args):
    print('Attempting enroll...')
    options = Options()
    options.headless = True
    options.add_argument("--private")  # open in private mode to avoid different login scenario
    driver = webdriver.Firefox(options=options)

    print('Attempting to get sportfahrplan')
    driver.get(config['default']['sportfahrplan_particular'])
    driver.implicitly_wait(5)  # wait 5 seconds if not defined differently
    print("Sportfahrplan retrieved")

    # find corresponding day div:
    day_ele = driver.find_element_by_xpath(
        "//div[@class='teaser-list-calendar__day'][contains(., '" + config['default']['day'] + "')]")

    # check if the lesson is already booked out
    free_places_locator = (By.XPATH, ".//div[contains(., 'Keine freien')]")
    try:
        WebDriverWait(driver, 1).until(EC.visibility_of_element_located(free_places_locator))
        print('Lesson already fully booked. Retrying in ' + str(args.retry_time) + 'min')
        time.sleep(args.retry_time * 60)
        return False
    except:
        pass

    # search in day div after corresponding location and time
    if config['default']['description']:
        day_ele.find_element_by_xpath(
            ".//li[@class='btn-hover-parent'][contains(., '" + config['default']['facility'] + "')][contains(., '" +
            config['default']['lesson_time'] + "')][contains(., '" + config['default'][
                'description'] + "')]").click()
    else:
        day_ele.find_element_by_xpath(
            ".//li[@class='btn-hover-parent'][contains(., '" + config['default']['facility'] + "')][contains(., '" +
            config['default']['lesson_time'] + "')]").click()

    WebDriverWait(driver, args.max_wait).until(EC.element_to_be_clickable((By.XPATH,
                                                                           "//a[@class='btn btn--block btn--icon relative btn--primary-border' or @class='btn btn--block btn--icon relative btn--primary']"))).click()

    # switch to new window:
    time.sleep(2)  # necessary because tab needs to be open to get window handles
    tabs = driver.window_handles
    driver.switch_to.window(tabs[1])
    WebDriverWait(driver, args.max_wait).until(EC.element_to_be_clickable(
        (By.XPATH, "//button[@class='btn btn-default ng-star-inserted' and @title='Login']"))).click()
    WebDriverWait(driver, args.max_wait).until(EC.element_to_be_clickable(
        (By.XPATH, "//button[@class='btn btn-warning btn-block' and @title='SwitchAai Account Login']"))).click()

    # choose organization:
    organization = driver.find_element_by_xpath("//input[@id='userIdPSelection_iddtext']")
    organization.send_keys('ETH Zurich')
    organization.send_keys(u'\ue006')

    driver.find_element_by_xpath("//input[@id='username']").send_keys(username)
    driver.find_element_by_xpath("//input[@id='password']").send_keys(password)
    driver.find_element_by_xpath("//button[@type='submit']").click()

    enroll_button_locator = (By.XPATH,
                             "//button[@id='btnRegister' and @class='btn-primary btn enrollmentPlacePadding ng-star-inserted']")
    try:
        WebDriverWait(driver, args.max_wait).until(EC.visibility_of_element_located(enroll_button_locator))
    except:
        print('Element not visible. Probably fully booked. Retrying in ' + str(args.retry_time) + 'min')
        time.sleep(args.retry_time * 60)
        return False

    try:
        enroll_button = WebDriverWait(driver, args.max_wait).until(EC.element_to_be_clickable(enroll_button_locator))
    except:
        raise ('Enroll button is disabled. Enrollment is likely not open yet.')

    enroll_button.click()
    print("Successfully enrolled. Train hard and have fun!")

    WebDriverWait(driver, 2)
    driver.quit()  # close all tabs and window
    return True


# ==== run enrollment script ============================================

# Check if the current version of geckodriver exists
# and if it doesn't exist, download it automatically,
# then add geckodriver to path
geckodriver_autoinstaller.install()

parser = argparse.ArgumentParser(description='ASVZ Bot script')
parser.add_argument('config_file', type=str, help='config file name')
parser.add_argument('--retry_time', type=int, default=5,
                    help='Time between retrying when class is already fully booked in seconds')
parser.add_argument('--max_wait', type=int, default=20, help='Max driver wait time (s) when attempting an action')
args = parser.parse_args()

config = configparser.ConfigParser(allow_no_value=True)
config.read(args.config_file)

waiting_fct()

# if there is an exception (no registration possible), enrollment is tried again in total 5 times and then stopped to avoid a lock-out
success = False
while not success:
    try:
        success = asvz_enroll(args)
    except:
        raise
print("Script finished successfully")
