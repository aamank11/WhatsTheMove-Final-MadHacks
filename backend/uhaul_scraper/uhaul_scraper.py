# Possibly used LLM for data cleaning for all other scrapes we do.

# imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import time
import sys
import json

# Config
UHAUL_TRUCK_URL = "https://www.uhaul.com/Truck-Rentals/"
MOVING_HELP_URL = "https://www.uhaul.com/MovingHelp/"

# Selenium setup / shared helpers

# Create a headless Chrome WebDriver.
def create_driver():
    options = ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    return driver

# Wait until an element is present in the DOM and return it.
def wait_for(driver, by, value, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

# Check if a captcha page is shown and bail out if so.
def check_captcha(driver):
    try:
        captcha_elements = driver.find_elements(
            By.XPATH, "/html/body/main/div/div/div/div/div/div/p"
        )
        if captcha_elements and "captcha" in captcha_elements[0].text.lower():
            # In backend mode we raise instead of printing & sys.exit
            raise RuntimeError(
                "U-Haul is showing a captcha. Please solve it once in a "
                "real browser and try again."
            )
    except Exception:
        # If anything goes wrong here, just continue.
        pass


# Truck search + parsing
def search_trucks(driver, pickup, dropoff, date_str):
    driver.get(UHAUL_TRUCK_URL)
    check_captcha(driver)
    time.sleep(2)  # let the page render

    try:
        pickup_input = wait_for(driver, By.ID, "PickupLocation-TruckOnly")
        dropoff_input = wait_for(driver, By.ID, "DropoffLocation")
        date_input = wait_for(driver, By.ID, "PickupDate")
        get_rates_button = wait_for(driver, By.ID, "getRates")
    except Exception as e:
        raise RuntimeError(
            "Could not find one of the form fields or the Get Rates button. "
            "The page layout might have changed, or U-Haul is A/B testing."
        ) from e

    # Fill form
    pickup_input.clear()
    pickup_input.send_keys(pickup)
    time.sleep(1)
    pickup_input.send_keys(Keys.ARROW_DOWN)
    pickup_input.send_keys(Keys.ENTER)

    dropoff_input.clear()
    dropoff_input.send_keys(dropoff)
    time.sleep(1)
    dropoff_input.send_keys(Keys.ARROW_DOWN)
    dropoff_input.send_keys(Keys.ENTER)

    date_input.clear()
    date_input.send_keys(date_str)

    # Click Get Rates
    get_rates_button.click()
    time.sleep(4)

# Returns a list[dict] of truck options. Each dict has keys:
# Pickup Location, Dropoff Location, Truck Type, Rate, Date
def parse_truck_results(driver, pickup_input, dropoff_input, date_str):
    # Try to parse pickup/dropoff from the header (h1)
    try:
        locations_element = wait_for(driver, By.TAG_NAME, "h1")
        locations_text = locations_element.text.strip()
        try:
            pickup_location, dropoff_location = locations_text.split(" to ")
        except ValueError:
            pickup_location = pickup_input
            dropoff_location = dropoff_input

        if "for " in pickup_location:
            pickup_location = pickup_location.split("for ")[1]
        if " on " in dropoff_location:
            dropoff_location = dropoff_location.split(" on ")[0]
    except Exception:
        pickup_location = pickup_input
        dropoff_location = dropoff_input

    results = []
    cards = driver.find_elements(By.XPATH, "//*[@id='equipmentList']/li")

    if not cards:
        return results

    for card in cards:
        try:
            name_el = card.find_element(By.TAG_NAME, "h3")
            truck_type = name_el.text.strip()

            try:
                price_el = card.find_element(By.XPATH, ".//dl/dd[1]/b")
            except Exception:
                price_el = card.find_element(
                    By.XPATH, ".//b[contains(text(), '$')]"
                )
            rate = price_el.text.strip()

            results.append(
                {
                    "Pickup Location": pickup_location,
                    "Dropoff Location": dropoff_location,
                    "Truck Type": truck_type,
                    "Rate": rate,
                    "Date": date_str,
                }
            )
        except Exception:
            continue

    return results


# Moving Help search + parsing
def search_movers(
    driver,
    loading_address,
    unloading_address,
    loading_date,
    loading_time,    # "Morning", "Afternoon", "Evening"
    unloading_date,
    unloading_time,  # "Morning", "Afternoon", "Evening"
):
    driver.get(MOVING_HELP_URL)
    check_captcha(driver)
    time.sleep(2)

    wait = WebDriverWait(driver, 20)

    # Choose BOTH (loading + unloading)
    try:
        both_label = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/main/div[1]/div/div/form/fieldset/div/fieldset/div/div[2]/ul/li[3]/label",
                )
            )
        )
        both_label.click()
    except Exception:
        # Non-fatal; we can still try to proceed
        pass

    # Loading section
    try:
        loading_address_input = wait.until(
            EC.element_to_be_clickable((By.ID, "mhLocation1"))
        )
        loading_date_input = wait.until(
            EC.element_to_be_clickable((By.ID, "Location1Date"))
        )
        loading_time_select = wait.until(
            EC.element_to_be_clickable((By.ID, "PreferredTime1"))
        )

        loading_address_input.clear()
        loading_address_input.send_keys(loading_address)

        loading_date_input.clear()
        loading_date_input.send_keys(loading_date)

        loading_time_select.send_keys(loading_time.title())
    except Exception as e:
        raise RuntimeError("Error filling loading section") from e

    # Unloading section
    try:
        unloading_address_input = wait.until(
            EC.element_to_be_clickable((By.ID, "mhLocation2"))
        )
        unloading_date_input = wait.until(
            EC.element_to_be_clickable((By.ID, "Location2Date"))
        )
        unloading_time_select = wait.until(
            EC.element_to_be_clickable((By.ID, "PreferredTime2"))
        )

        unloading_address_input.clear()
        unloading_address_input.send_keys(unloading_address)

        unloading_date_input.clear()
        unloading_date_input.send_keys(unloading_date)

        unloading_time_select.send_keys(unloading_time.title())
    except Exception as e:
        raise RuntimeError("Error filling unloading section") from e

    # Click search
    try:
        search_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/main/div[1]/div/div/form/fieldset/div/div[2]/div[2]/button",
                )
            )
        )
        search_button.click()
    except Exception:
        # Non-fatal; the results might still load
        pass

    time.sleep(4)



# Returns a list[dict] of moving-help providers. Each dict has keys:
# Loading Address, Unloading Address, Loading Date, Loading Time,
# Unloading Date, Unloading Time, Company, Price
def parse_mover_results(
    driver,
    loading_address,
    unloading_address,
    loading_date,
    loading_time,
    unloading_date,
    unloading_time,
):
    results = []
    cards = driver.find_elements(By.XPATH, "//*[@id='movingHelperResults']/ul/li")

    if not cards:
        return results

    for card in cards:
        try:
            try:
                name_el = card.find_element(By.TAG_NAME, "h3")
            except Exception:
                name_el = card.find_element(By.TAG_NAME, "h2")
            company_name = name_el.text.strip()

            price_el = card.find_element(
                By.XPATH, ".//*[contains(text(), '$')]"
            )
            price_text = price_el.text.strip()

            results.append(
                {
                    "Loading Address": loading_address,
                    "Unloading Address": unloading_address,
                    "Loading Date": loading_date,
                    "Loading Time": loading_time,
                    "Unloading Date": unloading_date,
                    "Unloading Time": unloading_time,
                    "Company": company_name,
                    "Price": price_text,
                }
            )
        except Exception:
            continue

    return results


# PUBLIC BACKEND-FRIENDLY FUNCTIONS

def get_truck_options(pickup: str, dropoff: str, pickup_date_str: str) -> dict:
    """
    High-level function for backend use.

    Returns a JSON-serializable dict:
    {
      "provider": "uhaul",
      "mode": "truck_rental",
      "pickup_location": ...,
      "dropoff_location": ...,
      "pickup_date": ...,
      "options": [ { ...truck card... }, ... ]
    }
    """
    driver = create_driver()
    try:
        search_trucks(driver, pickup, dropoff, pickup_date_str)
        truck_results = parse_truck_results(driver, pickup, dropoff, pickup_date_str)
        return {
            "provider": "uhaul",
            "mode": "truck_rental",
            "pickup_location": pickup,
            "dropoff_location": dropoff,
            "pickup_date": pickup_date_str,
            "options": truck_results,
        }
    finally:
        driver.quit()


def get_moving_help_options(
    loading_address: str,
    unloading_address: str,
    loading_date: str,
    loading_time: str,
    unloading_date: str,
    unloading_time: str,
) -> dict:
    """
    High-level function for backend use.

    Returns a JSON-serializable dict:
    {
      "provider": "uhaul",
      "mode": "moving_help",
      "loading_address": ...,
      "unloading_address": ...,
      "loading_date": ...,
      "loading_time": ...,
      "unloading_date": ...,
      "unloading_time": ...,
      "options": [ { ...mover card... }, ... ]
    }
    """
    driver = create_driver()
    try:
        search_movers(
            driver,
            loading_address,
            unloading_address,
            loading_date,
            loading_time,
            unloading_date,
            unloading_time,
        )
        mover_results = parse_mover_results(
            driver,
            loading_address,
            unloading_address,
            loading_date,
            loading_time,
            unloading_date,
            unloading_time,
        )
        return {
            "provider": "uhaul",
            "mode": "moving_help",
            "loading_address": loading_address,
            "unloading_address": unloading_address,
            "loading_date": loading_date,
            "loading_time": loading_time,
            "unloading_date": unloading_date,
            "unloading_time": unloading_time,
            "options": mover_results,
        }
    finally:
        driver.quit()


def get_truck_and_moving_help_options(
    origin: str,
    destination: str,
    pickup_date_str: str,
    loading_time: str,
    unloading_date_str: str,
    unloading_time: str,
) -> dict:

    # Combined flow that reuses a single driver session for trucks + movers.
    # Useful when the user wants both (reduces captcha risk).
    driver = create_driver()
    try:
        # Trucks
        search_trucks(driver, origin, destination, pickup_date_str)
        truck_results = parse_truck_results(driver, origin, destination, pickup_date_str)

        # Movers
        search_movers(
            driver,
            origin,
            destination,
            pickup_date_str,
            loading_time,
            unloading_date_str,
            unloading_time,
        )
        mover_results = parse_mover_results(
            driver,
            origin,
            destination,
            pickup_date_str,
            loading_time,
            unloading_date_str,
            unloading_time,
        )

        return {
            "provider": "uhaul",
            "mode": "truck_and_moving_help",
            "origin": origin,
            "destination": destination,
            "pickup_date": pickup_date_str,
            "loading_time": loading_time,
            "unloading_date": unloading_date_str,
            "unloading_time": unloading_time,
            "truck_options": truck_results,
            "moving_help_options": mover_results,
        }
    finally:
        driver.quit()



# Simple terminal test (prints JSON)
if __name__ == "__main__":
    # Example: quick manual test for trucks only
    data = get_truck_options(
        pickup="Madison, WI",
        dropoff="Seattle, WA",
        pickup_date_str=datetime.now().strftime("%m/%d/%Y"),
    )
    print(json.dumps(data, indent=2))
