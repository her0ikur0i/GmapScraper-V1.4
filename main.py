import asyncio
import os
import csv
import random
import time
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Ubah angka ini sesuai keinginan
max_data = 200

# Tambahkan query yang diinginkan di sini
queries = ["Cake & Bakery, Kecamatan Bojongloa Kaler"]

async def searchGoogleMaps(query, max_data):
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{query}.csv')
    zona = query.split(",")[-1].strip()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(f'https://www.google.com/maps/search/{"+".join(query.split())}', timeout=10000)
            await page.wait_for_selector('div[role="feed"]', timeout=10000)
            await autoScrollSearchResults(page)
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            results = []
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and "/maps/place/" in href:
                    if href.startswith('/'):
                        href = 'https://www.google.com' + href
                    results.append(href)
                    if len(results) >= max_data:
                        break
            
            businesses = []
            for index, result_url in enumerate(results):
                try:
                    print(f"Processing result {index + 1}/{len(results)}")
                    
                    detail_url = result_url
                    print(f"Visiting detail URL: {detail_url}")
                    await page.goto(detail_url, timeout=10000)
                    await page.wait_for_selector('div[role="main"]', timeout=10000)
                    await autoScrollDetail(page)
                    
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    parent = soup.find('div', {'role': 'main'})
                    name_elem = parent.find('h1')
                    name = name_elem.get_text().strip() if name_elem else None
                    
                    category_elem = parent.find('button', class_='DkEaL')
                    category = category_elem.get_text().strip() if category_elem else None
                    
                    phone_elem = parent.find('button', {'data-tooltip': 'Salin nomor telepon'})
                    phone = phone_elem.get_text().strip().replace('î‚°', '') if phone_elem else None
                    phone = ''.join(filter(str.isdigit, phone)) if phone else None
                    
                    website_elem = parent.find('a', class_='CsEnBe', href=True)
                    website = website_elem.get('href') if website_elem else None
                    
                    address_elem = parent.find('div', class_='Io6YTe fontBodyMedium kR99db')
                    address = address_elem.get_text().strip().replace('îƒˆ', '') if address_elem else None
                    
                    rating_elem = parent.find('div', class_='F7nice')
                    rating_value = None
                    reviews_value = None
                    if rating_elem:
                        rating_value_elem = rating_elem.find('span', {'aria-hidden': 'true'})
                        rating_value = rating_value_elem.get_text() if rating_value_elem else None
                        
                        reviews_elem = rating_elem.find_all('span', {'aria-label': True})
                        if reviews_elem:
                            for elem in reviews_elem:
                                aria_label = elem.get('aria-label')
                                if 'ulasan' in aria_label:
                                    reviews_value = ''.join(filter(str.isdigit, aria_label))
                    
                    # Debugging log untuk elemen rating dan review
                    print(f"Rating Element: {rating_elem}")
                    print(f"Rating Value: {rating_value}")
                    print(f"Reviews Value: {reviews_value}")
                    
                    business = {
                        'Name': name,
                        'Category': category,
                        'Phone': phone,
                        'Website': website,
                        'Address': address,
                        'Rating': rating_value,
                        'Reviews': reviews_value,
                        'Verified': 'Ya' if parent.find('span', class_='UY7F9') else 'Tidak',
                        'Zona': zona,
                        'Map URL': detail_url
                    }
                    
                    businesses.append(business)
                    
                    # Tulis data ke file CSV setiap selesai memproses satu entri
                    with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['Name', 'Category', 'Phone', 'Website', 'Address', 'Rating', 'Reviews', 'Verified', 'Zona', 'Map URL']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        
                        if csvfile.tell() == 0:
                            writer.writeheader()
                        
                        writer.writerow(business)
                    
                    await page.go_back()
                    await page.wait_for_selector('div[role="feed"]', timeout=10000)
                    
                    if len(businesses) >= max_data:
                        break
                
                except Exception as e:
                    print(f"Error saat memproses detail URL: {detail_url}, Error: {e}")
                    continue
            
        except Exception as e:
            print(f"Error pada searchGoogleMaps: {e}")
        
        finally:
            # Tutup browser
            await browser.close()

async def autoScrollSearchResults(page):
    await page.evaluate('''async () => {
        await new Promise((resolve, reject) => {
            var totalHeight = 0;
            var distance = 500;  // Mengurangi jarak scroll untuk menghindari penggunaan memori yang tinggi
            var scrollDelay = 2000;  // Mengurangi waktu delay untuk meningkatkan kecepatan

            var timer = setInterval(async () => {
                var wrapper = document.querySelector('div[role="feed"]');
                if (!wrapper) {
                    reject('Wrapper element not found');
                    return;
                }
                var scrollHeightBefore = wrapper.scrollHeight;
                wrapper.scrollBy(0, distance);
                totalHeight += distance;

                if (totalHeight >= scrollHeightBefore) {
                    totalHeight = 0;
                    await new Promise((resolve) => setTimeout(resolve, scrollDelay));

                    var scrollHeightAfter = wrapper.scrollHeight;

                    if (scrollHeightAfter > scrollHeightBefore) {
                        return;
                    } else {
                        clearInterval(timer);
                        resolve();
                    }
                }
            }, 100);
        });
    }''')

async def autoScrollDetail(page):
    await page.evaluate('''async () => {
        await new Promise((resolve, reject) => {
            var wrapper = document.querySelector('div[role="main"]');
            if (!wrapper) {
                reject('Wrapper element not found');
                return;
            }
            var totalHeight = 0;
            var distance = 500;  // Mengurangi jarak scroll untuk menghindari penggunaan memori yang tinggi
            var scrollDelay = 2000;  // Mengurangi waktu delay untuk meningkatkan kecepatan

            var timer = setInterval(async () => {
                var scrollHeightBefore = wrapper.scrollHeight;
                wrapper.scrollBy(0, distance);
                totalHeight += distance;

                if (totalHeight >= scrollHeightBefore) {
                    totalHeight = 0;
                    await new Promise((resolve) => setTimeout(resolve, scrollDelay));

                    var scrollHeightAfter = wrapper.scrollHeight;

                    if (scrollHeightAfter > scrollHeightBefore) {
                        return;
                    } else {
                        clearInterval(timer);
                        resolve();
                    }
                }
            }, 100);
        });
    }''')

async def main():
    for query in queries:
        await searchGoogleMaps(query, max_data)
        # Menambahkan random delay antar query untuk keamanan
        await asyncio.sleep(random.uniform(3, 6))

if __name__ == "__main__":
    asyncio.run(main())
