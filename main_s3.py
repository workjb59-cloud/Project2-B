import asyncio
import os
from datetime import datetime
from CategoryScraper import CategoryScraper
from S3Uploader import S3Uploader


class MainS3Scraper:
    """
    Main orchestrator for scraping Boshamlan data and uploading to AWS S3.
    
    This script:
    1. Scrapes data from all categories (rent, sale, exchange) filtered by yesterday's date
    2. Creates Excel files with sheets for each subcategory
    3. Uploads files to S3 with date-based partitioning
    """
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None):
        """
        Initialize the main scraper.
        
        Args:
            aws_access_key_id: AWS access key (optional, can use environment variables)
            aws_secret_access_key: AWS secret key (optional, can use environment variables)
        """
        self.category_scraper = CategoryScraper()
        
        # Get AWS credentials from environment if not provided
        access_key = aws_access_key_id or os.environ.get('AWS_ACCESS_KEY_ID')
        secret_key = aws_secret_access_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        self.s3_uploader = S3Uploader(
            bucket_name='data-collection-dl',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
    
    async def run(self):
        """
        Main execution method:
        1. Scrapes all categories and subcategories
        2. Creates Excel files with multiple sheets
        3. Uploads Excel files to S3 in 'excel files' folder
        4. Uploads images to S3 in 'images' folder
        """
        print("="*80)
        print("BOSHAMLAN SCRAPER - S3 Edition")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target S3: s3://data-collection-dl/boshamlan-data/properties/")
        print("  - Excel files -> excel files/")
        print("  - Images -> images/")
        print("="*80)
        
        # Step 1: Check S3 bucket accessibility
        print("\n[1/4] Checking S3 bucket accessibility...")
        if not self.s3_uploader.check_bucket_exists():
            print("ERROR: Cannot access S3 bucket. Please check your AWS credentials and bucket permissions.")
            return
        
        # Step 2: Scrape all categories
        print("\n[2/4] Scraping data from all categories...")
        excel_files = await self.category_scraper.scrape_all_categories()
        
        if not excel_files:
            print("WARNING: No Excel files were generated. Nothing to upload.")
            return
        
        print(f"\n✓ Successfully created {len(excel_files)} Excel file(s):")
        for category, file_path in excel_files.items():
            print(f"  - {category}: {file_path}")
        
        # Step 3: Upload Excel files to S3
        print("\n[3/4] Uploading Excel files to S3...")
        upload_results = self.s3_uploader.upload_multiple_files(excel_files)
        
        if upload_results:
            print(f"\n✓ Successfully uploaded {len(upload_results)} Excel file(s) to S3:")
            for category, s3_uri in upload_results.items():
                print(f"  - {category}: {s3_uri}")
        else:
            print("\nERROR: Failed to upload Excel files to S3.")
        
        # Step 4: Upload images to S3
        print("\n[4/4] Uploading images to S3...")
        total_images = 0
        for category_name in excel_files.keys():
            # Load the scraped data from the category
            category_data = self.category_scraper.categories.get(category_name)
            if not category_data:
                continue
            
            # Get all cards data for this category
            all_cards = []
            for subcat_name in category_data.get('subcategories', {}).keys():
                # Read the data from the saved category_data
                if hasattr(self.category_scraper, 'last_scraped_data'):
                    subcat_data = self.category_scraper.last_scraped_data.get(category_name, {}).get(subcat_name, [])
                    all_cards.extend(subcat_data)
            
            if all_cards:
                image_results = await self.s3_uploader.upload_images_from_data(all_cards, category_name)
                total_images += len(image_results)
        
        # Summary
        print("\n" + "="*80)
        print("SCRAPING COMPLETED")
        print("="*80)
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Categories processed: {len(excel_files)}")
        print(f"Excel files uploaded to S3: {len(upload_results)}")
        print(f"Images uploaded to S3: {total_images}")
        print("="*80)


async def main():
    """
    Entry point for the scraper.
    
    AWS credentials can be provided via:
    1. Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
    2. AWS credentials file (~/.aws/credentials)
    3. IAM role (if running on EC2)
    """
    # Option 1: Use environment variables or default credentials
    scraper = MainS3Scraper()
    
    # Option 2: Provide credentials explicitly (not recommended for production)
    # scraper = MainS3Scraper(
    #     aws_access_key_id='your-access-key',
    #     aws_secret_access_key='your-secret-key'
    # )
    
    await scraper.run()


if __name__ == "__main__":
    """
    Usage:
    
    1. Set environment variables (recommended):
       export AWS_ACCESS_KEY_ID=your-access-key
       export AWS_SECRET_ACCESS_KEY=your-secret-key
       python main_s3.py
    
    2. Or use AWS credentials file:
       Configure ~/.aws/credentials
       python main_s3.py
    
    3. For Windows PowerShell:
       $env:AWS_ACCESS_KEY_ID="your-access-key"
       $env:AWS_SECRET_ACCESS_KEY="your-secret-key"
       python main_s3.py
    """
    asyncio.run(main())
