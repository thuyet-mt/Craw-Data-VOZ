from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json
import time
import re


def crawl_voz_comments(thread_url, max_pages=3):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Bật nếu không cần quan sát
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=chrome_options)
    results = []
    seen_comments = set()  # Để tránh trùng lặp

    for page in range(1, max_pages + 1):
        url = f"{thread_url}page-{page}"
        print(f"⏳ Crawling: {url}")
        driver.get(url)
        time.sleep(2)

        posts = driver.find_elements(By.XPATH, "//article[contains(@class, 'message')]")
        posts
        for post in posts:
            # Lấy ID comment
            try:
                comment_id = post.get_attribute("id")  # vd: post-123456
                if not comment_id or comment_id == "":
                    continue  # Bỏ qua comment không có ID
            except:
                continue

            # Lấy tên tác giả
            try:
                author = post.find_element(By.XPATH, ".//h4//a").text.strip()
                if not author or author == "N/A":
                    continue  # Bỏ qua comment không có tác giả
            except:
                continue

            # Lấy phần bbWrapper chứa nội dung
            try:
                content_element = post.find_element(By.XPATH, ".//div[contains(@class, 'bbWrapper')]")
            except:
                continue

            # Xử lý quote nếu có
            quote_data = None
            try:
                quote_block = content_element.find_element(By.XPATH, ".//div[contains(@class, 'bbCodeBlock--quote')]")

                # Lấy ID của comment được quote từ data-quote attribute
                quote_id = quote_block.get_attribute("data-quote")
                if quote_id and not quote_id.startswith("post-"):
                    quote_id = f"post-{quote_id}"

                # Tên người được trích dẫn - cải thiện cách lấy
                quote_author = "unknown"
                try:
                    # Thử lấy từ thẻ strong đầu tiên
                    quote_author_element = quote_block.find_element(By.XPATH, ".//strong")
                    quote_author = quote_author_element.text.strip()
                    # Loại bỏ dấu ":" nếu có
                    if quote_author.endswith(":"):
                        quote_author = quote_author[:-1].strip()
                except:
                    # Nếu không có thẻ strong, thử lấy từ dòng đầu tiên
                    quote_text_full = quote_block.text.strip()
                    if "\n" in quote_text_full:
                        first_line = quote_text_full.split("\n")[0].strip()
                        if first_line.endswith(":"):
                            quote_author = first_line[:-1].strip()

                # Lấy nội dung quote (loại bỏ dòng đầu chứa tên tác giả)
                quote_text_full = quote_block.text.strip()
                quote_text = quote_text_full
                
                # Tách nội dung quote từ dòng thứ 2 trở đi
                if "\n" in quote_text_full:
                    lines = quote_text_full.split("\n")
                    # Bỏ qua dòng đầu (tên tác giả) và lấy phần còn lại
                    quote_text = "\n".join(lines[1:]).strip()

                quote_data = {
                    "author": quote_author,
                    "id_comment": quote_id,
                    "comment": quote_text
                }

                # Xóa phần quote khỏi comment chính để lấy nội dung comment
                driver.execute_script("""
                    let quote = arguments[0].querySelector('.bbCodeBlock--quote');
                    if (quote) quote.remove();
                """, content_element)

            except:
                # Nếu không có quote HTML, kiểm tra quote dạng text thường
                main_comment_text = content_element.text.strip()
                # Pattern: Tên tác giả + ' said:' ở đầu comment
                match = re.match(r"^(.*?) said:\n(.+)", main_comment_text, re.DOTALL)
                if match:
                    quote_author = match.group(1).strip()
                    rest = match.group(2).strip()
                    # Tìm comment gốc để lấy id_comment nếu có
                    quote_id = None
                    for item in results:
                        if item["author"] == quote_author and item["comment"] in main_comment_text:
                            quote_id = item["id_comment"]
                            break
                    # Lấy phần quote là đoạn đầu tiên (tới 2 dấu xuống dòng liên tiếp hoặc hết đoạn)
                    quote_lines = rest.split("\n\n", 1)
                    quote_comment = quote_lines[0].strip()
                    # Phần còn lại là comment chính
                    main_comment = rest[len(quote_comment):].strip()
                    quote_data = {
                        "author": quote_author,
                        "id_comment": quote_id,
                        "comment": quote_comment
                    }
                    # Gán lại main_comment cho phần sau
                    content_element_text = main_comment
                else:
                    content_element_text = main_comment_text

            # Lấy nội dung comment chính sau khi đã xóa quote hoặc xử lý text thường
            try:
                main_comment = content_element_text if 'content_element_text' in locals() else content_element.text.strip()
            except:
                main_comment = ""

            # Chỉ thêm vào kết quả nếu có nội dung comment và chưa tồn tại
            if main_comment:
                # Tạo key để kiểm tra trùng lặp
                comment_key = f"{author}_{comment_id}_{main_comment[:100]}"  # Lấy 100 ký tự đầu
                
                if comment_key not in seen_comments:
                    seen_comments.add(comment_key)
                    results.append({
                        "author": author,
                        "id_comment": comment_id,
                        "quote": quote_data,
                        "comment": main_comment
                    })

    driver.quit()
    return results


def save_to_json(data, filename="voz_comments.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(data)} comment vào {filename}")


def save_to_csv(data, filename="voz_comments.csv"):
    import csv
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["author", "id_comment", "quote_author", "quote_id", "quote_comment", "comment"])
        
        for item in data:
            quote_author = item["quote"]["author"] if item["quote"] else ""
            quote_id = item["quote"]["id_comment"] if item["quote"] else ""
            quote_comment = item["quote"]["comment"] if item["quote"] else ""
            
            writer.writerow([
                item["author"],
                item["id_comment"],
                quote_author,
                quote_id,
                quote_comment,
                item["comment"]
            ])
    print(f"✅ Đã lưu {len(data)} comment vào {filename}")


def save_to_txt(data, filename="voz_comments.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for i, item in enumerate(data, 1):
            f.write(f"=== Comment {i} ===\n")
            f.write(f"Tác giả: {item['author']}\n")
            f.write(f"ID: {item['id_comment']}\n")
            
            if item["quote"]:
                f.write(f"Quote từ: {item['quote']['author']}\n")
                f.write(f"Quote ID: {item['quote']['id_comment']}\n")
                f.write(f"Nội dung quote: {item['quote']['comment']}\n")
            
            f.write(f"Nội dung: {item['comment']}\n")
            f.write("-" * 50 + "\n\n")
    print(f"✅ Đã lưu {len(data)} comment vào {filename}")


# --- CHẠY ---
if __name__ == "__main__":
    thread_url = "https://voz.vn/t/so-sanh-flutter-react-native-kotlin.138331/"
    data = crawl_voz_comments(thread_url, max_pages=3)
    
    # Lưu theo nhiều format
    save_to_json(data, f"{thread_url.split('/')[-1]}.json")
    # save_to_csv(data, "voz_comments.csv")
    # save_to_txt(data, "voz_comments.txt")
