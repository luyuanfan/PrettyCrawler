# Standard Python library imports
import csv
import json
import os
import io
from pathlib import Path
from zipfile import ZipFile
import re

# Imports from Django libraries. 
from django.shortcuts import render, redirect
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import path
from django.template.loader import get_template

# Imports from elsewhere
from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa
import requests
from reportlab.pdfgen import canvas
from urllib.parse import urljoin, urlparse

# Imports from our models.
from .models import Page


def home(request):
    '''
    Default homepage. 
    '''
    return render(request, 'home.html')

def verify_user_id(request):
    '''
    Verifies the ID associated with the user.
    The ID is stored in user's browser's local storage.
    '''

    # Get user ID. 
    user_id = request.POST.get('scraper_user_id')
    print(f'In verify_user_id, we got the ID {user_id}')
    if not user_id:
        return JsonResponse({'status': 'error', 'message': 'No User ID provided'})

    # Create a User object associate with ID if it does not already exist.
    if not User.objects.filter(username=user_id).exists():
        try:
            User.objects.create_user(username=user_id)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': e})
    
    request.session['scraper_user_id'] = user_id
    return JsonResponse({'status': 'success', 'message': 'User already exists', 'user_id': user_id})
        
def validate_url(url):
    '''
    This function validates user's input URL.
    If the URL is not valid, it should notify the user. 
    # TODO: connect to frontend and notify user. 
    '''
    validate = URLValidator()

    if not url:
        return False, 'You entered an empty URL.'
    try:
        validate(url)
    except ValidationError as e:
        return False, str(e)
    return True, 'URL exists.'

def get_safe_filename(filename):
    '''
    Cleans up '\n' and any other invalid characters to HTTP response headers.
    I also just cleaned up all characters that I'm not fond of =^OwO^=. 
    Args:
      @ filename: a string.
    Returns:
      @ safe_filename: a string. 
    '''
    invalid_char_set = set("_:;.,/\"?!(){}[]@<>=-+*#$&`|~^% \n")
    safe_filename = ''.join([char if char not in invalid_char_set else '_' for char in filename])
    safe_filename = re.sub(r'^_+|_+$', '', safe_filename)
    safe_filename = re.sub(r'_{2,}', '_', safe_filename)
    print(safe_filename)
    if len(safe_filename) >= 255:
        return safe_filename[0:255]
    return safe_filename

def get_absolute_url(base, link):
    '''
    Convert a relative link to an absolute URL based on the base URL.
    Args:
      @ base: The base URL of the current page.
      @ link: The href attribute value found in the page.
    Returns:
      An absolute URL.
    '''
    return urljoin(base, link)

def is_absolute(link):
    '''
    Check is a URL is absolute. 
    Args:
      @ link: The href attribute value found in the page.
    Returns:
      Boolean. 
    '''
    return bool(urlparse(link).netloc)

def get_and_store_page_content(request, url, parent):
    '''
    Creates Page objects that represents content on one webpage.
    Args:
      @ request: Django request object.
      @ url: URL of a webpage. 
      @ parent: page object from which url is found.
    Returns:
      @ page: One Page object.
      @ hrefs: a list of URL. 
    '''

    # Check if URL is valid. 
    is_valid, error_message = validate_url(url)
    if not is_valid:
        error_message = 'ERROR: URL is not valid.'
        print(error_message)
        return None, []

    # Check if page is valid. 
    response = requests.get(url)
    if not response:
        error_message = 'ERROR: Failed to get network response.'
        print(error_message)
        return None, []

    # Use BeautifulSoup to parse response.
    soup = BeautifulSoup(response.content, 'html.parser')
    if not soup:
        error_message = 'ERROR: Failed to parse page content.'
        print(error_message)
        return None, []

    # Create and construct safe directory name from page title. 
    title = soup.find('title').string if soup.title else 'No title available'

    # Process raw filename to get one appropriate for HTTP response header.
    safe_filename = get_safe_filename(title)

    # Extract links in this page for further scraping
    hrefs = [a['href'] for a in soup.find_all('a', href=True)]

    # Retrieve user ID. 
    user_id = request.session.get('scraper_user_id')

    # Store Page object in database.
    page = Page.create(
        user_id=user_id,
        url=url,
        title=title,
        safe_filename=safe_filename,
        hrefs=str(hrefs), 
        content=str(soup),
        parent=parent
    )

    print(f'saved page {page.safe_filename} in database! url: {page.url}, parent: {page.parent}')
    return page, hrefs

def recursive_scrape(request, base, url, max_depth, curr_depth, parent):
    '''
    This function recursively get page content from a URL.
    It should collect to all URL present a current page and traverse to those links.
    Later I want to store them in a structured thing.... But now we can just append. 
    TODO: Can we add a detect add functionality, so that we rule out those links.
    TODO: Notify user that this URL is not valid on frontend. We can do all this later.
    Returns:
      @ Boolean. 
    '''
    # If we have gone through all files, return True to indicates that files are ready. 
    if curr_depth > max_depth:
        print("ALERT: max depth reached")
        return True

    # Get main page contents and all URL it links to, it is also stored in database.
    page, hrefs = get_and_store_page_content(request, url, parent)
    if not page:
        print('Alert! get page returned none from get and store page')
        return False

    print(f'hey we found the links on your current webpage: {hrefs}')

    if curr_depth < max_depth:
        # Find all URLs on page and create page for them. 
        for link in hrefs:
            if not is_absolute(link):
                link = get_absolute_url(base, link)
                print(f'absolute link {link}')
            # Here we can set the current Page object as the parent of the next one.
            ret = recursive_scrape(request, base, link, max_depth, curr_depth + 1, page)
    else:
        print("ALERT: we end at current level")
    return True
        
def scrape(request):
    '''
    Handles scrape requests.
    Args:
      @ request: Django request object.
    Returns:
      @ response: 
    '''
    if request.method == 'POST':

        # Get URL from session of the webpage that user wants to scrape.
        url = request.POST.get('input_url', None)

        # Set this URL as the root of this session (since it could be the parent of more webpages)
        request.session['root_url'] = url 

        # Get recursion depth from session. 
        max_depth = request.POST.get('depth', 1)
        if not max_depth:
            max_depth = 1
        max_depth = int(max_depth)

        # Set a base url for links that are partial. 
        base_url = url

        # Parent page should be None the first time recursive_scrape is called
        files_ready = recursive_scrape(request, base_url, url, max_depth, 1, None)
        if files_ready:
            request.session['files_ready'] = True
        else:
            request.session['files_ready'] = False

        return render(request, 'home.html')
        
    else:

        return render(request, 'home.html')

def retrieve_all_pages(user_id, root_url):
    '''
    Retrieves all files linked to the root page.
    Args:
      @ user_id: unqiue identifier of a user.
      @ root_url: URL of the webpage a user entered.
    Returns:
      @ root_page, [pages]: a pair of root_page and all other pages. 
    '''

    print(f"Retrieving pages for user ID: {user_id} with root URL: {root_url}")
    # Get root page. 
    root_page = Page.objects.filter(user_id=user_id, url=root_url, parent__isnull=True).first()
    if not root_page:
        print(f"ALERT: No root page found in the database for URL {root_url}")
        return [], []
    
    print(f"Root page found: {root_page}")
    # Get not only the direct children but grandchildren pages, etc. 
    pages = root_page.get_all_children()
    if not pages:
        print(f'There is no pages associated with this root page.')
    print(f"Total pages linked to root page (including all descendants): {len(pages)}")
    for page in pages:
        print(f"Linked page: {page.title} at {page.url}")

    print(f'returning root {root_page} and all {pages}')
    return root_page, [root_page] + pages

def download(request):
    '''
    A django view to zip files in directory and send it as downloadable response to the browser.
    Args:
      @request: Django request object
      @file_name: Name of the directory to be zipped
    Returns:
      A downloadable Http response
    '''

    if request.method == 'POST':

        # Get user ID and root_file URL from session. 
        user_id = request.session.get('scraper_user_id')
        root_url = request.session.get('root_url', None)
        if not root_url:
            print(f'ERROR: You entered an empty URL and tried to download nothing.')

        # Retrieve all files associated with this user ID and root_file URL. 
        root_page, all_pages = retrieve_all_pages(user_id, root_url)
        
        # Get download type from session. 
        download_type = request.POST.get('download_type')

        # Generate zip filename from root_page name and download type. 
        zip_filename = f'({download_type}) {root_page.safe_filename}.zip'

        # Create a downloadable zip-typ HTTP response. 
        response = HttpResponse(content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

        with ZipFile(response, 'w') as zf:
            for page in all_pages:

                # Generate one filename with folder. 
                filename = f'{root_page.safe_filename}/{page.safe_filename}.{download_type}'
                
                # Generate one file based on chosen download type. 
                match download_type:
                    case 'pdf':
                        content = generate_pdf(page)
                    case 'csv':
                        content = generate_csv(page)
                    case 'json':
                        content = generate_json(page)
                
                zf.writestr(filename, content)
        
        request.session['files_ready'] = False
        return response

    else:

        request.session['files_ready'] = False
        return render(request, 'home.html')

def generate_pdf(page):
    '''
    Generates PDF download type.
    Args: 
      @ page: one Page object. 
    Returns:
      @ response: 
    '''

    # Create a file-like buffer to receive PDF data.
    pdf_buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its 'file.'
    template = get_template('pdf_result.html')
    links_found = page.hrefs if page.hrefs else f'No links found.'
    html = template.render({ 'content': page.content, 'hrefs': links_found })
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer, encoding='utf-8')

    pdf_buffer.seek(0)

    if pisa_status.err:
        raise Exception('PDF generation failed')
    
    return pdf_buffer.getvalue()

def generate_csv(page):
    '''
    Generates CSV download type.
    Args: 
      @ pages: one Page object. 
    Returns:
      @ response: 
    '''
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['Title', 'URL', 'Content'])
    writer.writerow([page.title, page.url, page.content])
    csv_buffer.seek(0)
    return csv_buffer.getvalue().encode('utf-8')

def generate_json(page):
    '''
    Generates JSON download type. 
    Args: 
      @ page: one Page object. 
    Returns: 
      @ response: 
    '''
    data = {
        'title': page.title,
        'url': page.url,
        'content': page.content
    }
    return json.dumps(data, indent=4).encode('utf-8')