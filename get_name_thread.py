from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time


def get_thread_title(thread_url):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Bật nếu không cần quan sát
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(thread_url)
        time.sleep(2)
        title_element = driver.find_element(By.XPATH, "//h1[contains(@class, 'p-title-value')]")
        thread_title = title_element.text.strip()
    except Exception as e:
        print(f"Không lấy được tiêu đề: {e}")
        thread_title = None
    driver.quit()
    return thread_title


if __name__ == "__main__":
    thread_url = "https://voz.vn/t/so-sanh-flutter-react-native-kotlin.138331/"
    title = get_thread_title(thread_url)
    print(f"Thread title: {title}") 
