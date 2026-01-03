import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime, timedelta


class PropertyCardScraper:
    def __init__(self, url):
        self.url = url
        self.browser = None
        self.context = None

    async def scrape_cards(self):
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            main_page = await self.context.new_page()

            try:
                await main_page.goto(self.url)
                await main_page.wait_for_selector('.relative.min-h-48', timeout=60000)

                # Scroll to load all posts
                await self.scroll_to_bottom(main_page)

                # Wait again to ensure all posts are loaded
                await main_page.wait_for_selector('.relative.min-h-48')

                # Get all card containers dynamically
                posts = await main_page.query_selector_all('.relative.w-full.rounded-lg.card-shadow')

                if not posts:
                    return "No cards found on this page."

                result = []
                for index, post in enumerate(posts):
                    print(f"\nProcessing card {index + 1}...")

                    # First get the title to use as identifier
                    title = await self.scrape_text(post, '.font-bold.text-lg.text-dark.line-clamp-2.break-words')
                    price = await self.scrape_text(post, '.rounded.font-bold.text-primary-dark')

                    card_data = {
                        'title': title,
                        'price': price,
                        'relative_date': await self.scrape_text(post, '.rounded.text-xs.flex.items-center.gap-1'),
                        'description': await self.scrape_description(post),
                        'image_url': await self.scrape_image(post),
                        'link': await self.scrape_link(title, price)  # Pass identifying info
                    }

                    # Extract the mobile number and views number from the link page
                    link = card_data['link']
                    if link:
                        card_data['mobile_number'] = await self.scrape_mobile_number(link)
                        card_data['views_number'] = await self.scrape_views_number(link)

                    result.append(card_data)

                # Filter cards based on relative_date format "any number ساعة"
                result = self.filter_by_relative_date(result)

                return json.dumps(result, ensure_ascii=False, indent=2)

            finally:
                await self.browser.close()

    def filter_by_relative_date(self, cards):
        """
        Filters the cards where the relative date is in the format 'any number ساعة'.
        """
        filtered_cards = []
        for card in cards:
            relative_date = card.get('relative_date', '')
            # Check if the relative date contains any number followed by 'ساعة'
            if ('ساعة' in relative_date or 'دقيقة' in relative_date) and relative_date.split()[0].isdigit():
                filtered_cards.append(card)
        return filtered_cards

    async def scrape_text(self, post, selector):
        try:
            element = await post.query_selector(selector)
            if element:
                return await element.text_content()
        except Exception as e:
            print(f"Failed to scrape {selector}: {e}")
        return None

    async def scrape_description(self, post):
        try:
            description_element = await post.query_selector('.line-clamp-2:nth-of-type(2)')
            if description_element:
                return await description_element.text_content()
        except Exception as e:
            print(f"Failed to scrape description: {e}")
        return None

    async def scrape_image(self, post):
        try:
            img_element = await post.query_selector('img[alt="Post"]')
            if img_element:
                return await img_element.get_attribute('src')
        except Exception as e:
            print(f"Failed to scrape image: {e}")
        return None

    async def scrape_link(self, title, price):
        new_page = None
        try:
            # Create a new page and navigate to the main URL
            new_page = await self.context.new_page()
            await new_page.goto(self.url)

            # Wait for cards to load
            await new_page.wait_for_selector('.relative.min-h-48')

            # Find the card with matching title and price
            card_selector = f"div.relative.w-full.rounded-lg.card-shadow:has(.font-bold.text-lg.text-dark.line-clamp-2.break-words:text-is(\"{title}\"))"
            matching_card = await new_page.wait_for_selector(card_selector)

            if matching_card:
                # Set up navigation listener
                async with new_page.expect_navigation(timeout=5000, wait_until='networkidle') as navigation_info:
                    await matching_card.click()
                    try:
                        await navigation_info.value
                        final_url = new_page.url
                        await new_page.close()
                        return final_url
                    except Exception as e:
                        print(f"Navigation failed: {e}")

            await new_page.close()
            return None

        except Exception as e:
            print(f"Failed to scrape link: {e}")
            if new_page:
                try:
                    await new_page.close()
                except:
                    pass
            return None

    async def scrape_mobile_number(self, link):
        new_page = None
        try:
            # Create a new page and navigate to the link
            new_page = await self.context.new_page()
            await new_page.goto(link)

            # Find the mobile number anchor inside the specific div
            mobile_element = await new_page.query_selector('.flex.gap-3.justify-center a')
            if mobile_element:
                mobile_number = await mobile_element.get_attribute('href')
                # Extract the number from the href (assuming it starts with tel:)
                if mobile_number and mobile_number.startswith('tel:'):
                    return mobile_number[4:]
        except Exception as e:
            print(f"Failed to scrape mobile number: {e}")

        return None

    async def scrape_views_number(self, link):
        new_page = None
        try:
            # Create a new page and navigate to the link
            new_page = await self.context.new_page()
            await new_page.goto(link)
            await new_page.wait_for_selector(
                '.flex.items-center.justify-center.gap-1.rounded.bg-whitish-transparent.py-1.px-1\\.5.text-xs.min-w-\\[62px\\] div',
                timeout=10000)

            # Find the views number
            views_element = await new_page.query_selector(
                '.flex.items-center.justify-center.gap-1.rounded.bg-whitish-transparent.py-1.px-1\\.5.text-xs.min-w-\\[62px\\] div')
            if views_element:
                views_number = await views_element.text_content()
                return views_number.strip() if views_number else None
            else:
                print("Views element not found!")
                return None
        except Exception as e:
            print(f"Failed to scrape views number: {e}")

        return None

    async def scroll_to_bottom(self, page):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        button_selector = (
            'button.text-base.shrink-0.select-none.whitespace-nowrap.transition-colors.'
            'disabled\\:opacity-50.h-12.font-bold.bg-primary.text-on-primary.active\\:bg-active-primary.'
            'w-full.cursor-pointer.z-20.max-w-2xl.py-3.md\\:py-4.px-8.rounded-full.flex.items-center.justify-center.gap-2\\.5'
        )

        # 1. Press the button ONCE if found
        try:
            button = await page.query_selector(button_selector)
            if button:
                is_disabled = await button.get_property('disabled')
                if not is_disabled:
                    await button.click()
                    await asyncio.sleep(10)  # Wait for items to load after clicking
        except Exception as e:
            print(f"Could not click 'Show More' button: {e}")

        # 2. Begin scrolling and checking card dates
        consecutive_old = 0
        while True:
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)  # Allow cards to load

            # 3. Get all relative date elements
            date_elements = await page.query_selector_all('.rounded.text-xs.flex.items-center.gap-1')
            date_texts = []
            for elem in date_elements:
                txt = await elem.text_content()
                if txt:
                    date_texts.append(txt.strip())

            # 4. Check for 3 consecutive cards with date older than yesterday
            consecutive_old = 0
            for date_str in date_texts:
                # If your cards have actual date format, use this:
                try:
                    card_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if card_date < datetime.strptime(yesterday, "%Y-%m-%d"):
                        consecutive_old += 1
                        if consecutive_old >= 3:
                            print("3 consecutive old cards found. Stopping scroll.")
                            return
                    else:
                        consecutive_old = 0
                except ValueError:
                    # If not a date string, fallback to your previous logic (e.g. "ساعة" or "دقيقة")
                    if any(word in date_str for word in ['ساعة', 'دقيقة']):
                        consecutive_old = 0  # Reset, it's a fresh card
                    else:
                        consecutive_old += 1
                        if consecutive_old >= 3:
                            print("3 consecutive old cards found. Stopping scroll.")
                            return

            # If not enough cards found to check, break to avoid infinite loop
            if len(date_texts) < 3:
                print("Not enough cards to check for consecutive old dates.")
                break

    # async def scroll_to_bottom(self, page):
    #     previous_height = await page.evaluate('document.body.scrollHeight')
    #     while True:
    #         await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    #         await asyncio.sleep(2)
    #         new_height = await page.evaluate('document.body.scrollHeight')
    #         if new_height == previous_height:
    #             break
    #         previous_height = new_height


# # Usage
# async def main():
#     url = "https://www.boshamlan.com/للبيع"
#     scraper = CardScraper(url)
#     result = await scraper.scrape_cards()
#     print(result)
#
#
# if __name__ == "__main__":
#     asyncio.run(main())

