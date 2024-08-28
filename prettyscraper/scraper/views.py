# Standard Python library imports
import csv
import json
import os
import io
from pathlib import Path
from zipfile import ZipFile

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
            return JsonResponse({'status': 'success', 'message': 'User created', 'user_id': user_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': e})
    else:
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


def get_and_store_page_content(request, url, parent):
    '''
    Creates Page objects that represents content on one webpage.
    Args:
      @ request: Django request object.
      @ url: url of a webpage. 
      @ parent: page object from which url is found.
    Returns:
      @ page: Page object. 
    '''

    # Check if URL is valid. 
    is_valid, error_message = validate_url(url)
    if not is_valid:
        error_message = "ERROR: URL is not valid."
        print(error_message)
        messages.error(request, error_message)
        return

    # Check if page is valid. 
    response = requests.get(url)
    if not response:
        error_message = "ERROR: Failed to get network response."
        print(error_message)
        messages.error(request, error_message)
        return

    # Use BeautifulSoup to parse response.
    soup = BeautifulSoup(response.content, 'html.parser')
    if not soup:
        error_message = "ERROR: Failed to parse page content."
        print(error_message)
        messages.error(request, error_message)
        return

    # Create and construct safe directory name from page title. 
    title = soup.find('title').string if soup.title else 'No title available'
    print(f"Before converting title to safe title, it is: {title}")
    safe_filename = title.replace('/', '_').replace(' ','_').replace(':', '_')
    print(f"After converting title to safe title, it is: {safe_filename}")

    user_id = request.POST.get('scraper_user_id', None)

    page = Page.create(
        user_id=user_id,
        url=url,
        title=title,
        safe_filename = safe_filename,
        content=str(soup),
        parent=parent
    )

    return page

def recursive_scrape(request, url, max_depth, curr_depth, parent):
    '''
    This function recursively get page content from a URL.
    It should collect to all URL present a current page and traverse to those links.
    Later I want to store them in a structured thing.... But now we can just append. 
    TODO: Can we add a detect add functionality, so that we rule out those links.
    TODO: Notify user that this URL is not valid on frontend. We can do all this later.
    '''
    
    if curr_depth > max_depth: return

    page = get_and_store_page_content(request, url, parent)
    if not page:
        return

    # If curr_depth indicates we should go to the next level. 
    if curr_depth < max_depth:

        # Find all URLs on page and create page for them. 
        hrefs = []
        for a in soup.find_all('a', href=True):
            link = a['href']
            recursive_scrape(request, link, max_depth, curr_depth + 1, page)

    return True
        
def main(request):
    '''
    This function handles requests.
    It should direct user to download page when a file bundle is ready.
    '''
    if request.method == 'POST':

        url = request.POST.get('input_url', None)
        request.session['root_url'] = url 
        print(f'In MAIN input url is {url}')
        max_depth = int(request.POST.get('depth'))
        if not max_depth:
            max_depth = 1
        
        # Parent page should be None the first time recursive_scrape is called
        files_ready = recursive_scrape(request, url, max_depth, 1, None)
        if files_ready:
            request.session['files_ready'] = True

        return render(request, 'home.html')
        
    else:

        return render(request, 'home.html')

def retrieve_pages(user_id, url):
    '''
    '''
    root_page = Page.objects.filter(user_id=user_id, url=url, parent__isnull=True).first()
    pages = [root_page] + list(root_page.linked_pages.all())
    return pages

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

        user_id = request.session.get('scraper_user_id')
        print(f'user id is {user_id}')
        root_url = request.session.get('root_url', None)
        print(f'input url is {root_url}')

        is_valid, error_message = validate_url(root_url)
        if not is_valid:
            error_message = "ERROR: URL is not valid."
            print(error_message)
            return HttpResponse(error_message, status=400)

        pages = retrieve_pages(user_id, root_url)

        download_type = request.POST.get('download_type')

        zip_filename = f"{download_type}_files.zip"

        response = HttpResponse(content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

        with ZipFile(response, 'w') as zf:
            for page in pages:
                filename = f"{page.safe_filename}.{download_type}"
                if download_type == 'pdf':
                    content = generate_pdf(page)
                elif download_type == 'csv':
                    content = generate_csv(page)
                elif download_type == 'json':
                    content = generate_json(page)
                zf.writestr(filename, content)
        
        return response

    else:

        return render(request, 'home.html')

def generate_pdf(page):
    '''
    Generates PDF download type.
    Args: 
      @ page: file
    Returns:
      @ response: 
    '''
    pdf_buffer = io.BytesIO()
    template_path = 'result.html'
    template = get_template(template_path)
    html = template.render({'page': page})
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer, encoding='utf-8')
    pdf_buffer.seek(0)
    if pisa_status.err:
        raise Exception('PDF generation failed')
    return pdf_buffer.getvalue()

def generate_csv(page):
    '''
    Generates CSV download type.
    Args: 
      @ pages: files
    Returns:
      @ response: 
    '''
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['Title', 'URL', 'Content'])
    writer.writerow([page.title, page.url, page.content])
    csv_buffer.seek(0)
    return csv_buffer.getvalue().encode('utf-8')


def generate_json(pages):
    '''
    Generates JSON download type. 
    Args: 
      @ pages: files
    Returns:
      @ response: 
    '''

    data = {
        'title': page.title,
        'url': page.url,
        'content': page.content
    }
    return json.dumps(data, indent=4).encode('utf-8')