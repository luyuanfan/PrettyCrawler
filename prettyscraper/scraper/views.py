# Standard Python library imports
import csv
import json
import os
from io import BytesIO
from pathlib import Path
import zipfile

# Imports from Django libraries. 
from django.shortcuts import render, redirect
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib import messages
from django.urls import path
from django.template.loader import get_template
from bs4 import BeautifulSoup
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa
import requests

# Imports from our models.
from .models import Page, User

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
    user_id = request.POST.get('scraper_user_id')
    print(f'In verify_user_id, we got the ID {user_id}')
    if not user_id:
        return JsonResponse({'status': 'error', 'message': 'No User ID provided'})

    # Create a new User object associate with ID. 
    user = User.objects.filter(username=user_id).exists()
    if not user:
        user = User.objects.create_user(user_id)

    return JsonResponse({'status': 'success', 'message': 'User ID verified', 'user_id': user_id})
        
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

def get_page_content(request, url, max_depth, curr_depth):
    '''
    This function recursively get page content from a URL.
    It should collect to all URL present at current page and traverse to those links.
    Later I want to store them in a structured thing.... But now we can just append. 
    TODO: Can we add a detect add functionality, so that we rule out those links.
    TODO: Also rememeber to check max depth reached.
    TODO: Notify user that this URL is not valid on frontend. We can do all this later.
    '''

    if curr_depth > max_depth: return

    # Check if URL is valid. 
    is_valid, error_message = validate_url(url)
    if not is_valid:
        print(f'ERROR: URL is not valid: {error_message}')
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

    print(f'Soup is {soup}')
    # Create and construct safe directory name from page title. 
    title = soup.find('title').string if soup.title else url
    print(f"Before converting title to safe title, it is: {title}")
    file_name = title.replace('/', '_').replace(' ','_').replace(':', '_')
    print(f"After converting title to safe title, it is: {title}")
    # new_dir_path = os.path.join(curr_path, file_name)
    # try:
    #     os.makedir(new_dir_path, exist_ok=True)
    # except OSError as e: print(e)

    page = Page.objects.create(
        user=user,
        url=url,
        title=title,
        content=str(soup),
        parent=parent
    )

    # If curr_depth indicates we should go to the next level. 
    if curr_depth < max_depth:
        # Find all URLs on page. 
        hrefs = []
        for a in soup.find_all('a', href=True):
            hrefs.append(a['href'])
        
        # Recursively call this function with new URLs. 
        for link in hrefs:
            if link:
                get_page_content(request, link, max_depth, curr_depth + 1)

    # # Construct file with path. 
    # page_content = {
    #     'title' : title,
    #     'main' : soup,
    #     'hrefs' : hrefs,
    # }

    # file = ContentFile(page_content, name=page_content.title)
    # Page.objects.create(file=file)

    print(f'Soup is {soup}, with a list of links {hrefs}')
    # return page_content
        
def main(request):
    '''
    This function handles requests.
    It should direct user to download page when a file bundle is ready.
    TODO: For the result page (or maybe just a new section on home page, we need an scrape another button)
    '''
    if request.method == 'POST':
        url = request.POST.get('input_url', None)
        max_depth = int(request.POST.get('depth', 1))

        bundle = get_page_content(request, url, max_depth, 1)
        return render(request, 'result.html', bundle)

    else:
        return render(request, 'home.html')
        
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

        context = request.session.get('scraped_data', {})
        download_type = request.POST.get('download_type')

        if download_type == 'pdf':
            return generate_pdf(context)
        elif download_type == 'csv':
            return generate_csv(context)
        elif download_type == 'json':
            return generate_json(context)
        else:
            return render(request, 'home.html')

    else:

        return render(request, 'home.html')

    # def add_to_zip(page, path=''):
    #     filename = f'{path}{page.title}.html'
    #     archive.writestr(filename, page.content)
    #     for child in page.linked_pages.all():
    #         child_path = f'{path}{page.title}/'
    #         add_to_zip(child, path=child_path)
        
    # root_page = Page.objects.get(id=root_page_id, user=request.user)

    # byte_data = io.BytesIO()
    # pisa_status = pisa.CreatePDF(html, dest=response, encoding='utf-8')
    # if pisa_status.err:
    #     print(f'ERROR: PDF generation failed')
    #     return HttpResponse('ERROR: PDF generation failed')
    # zipfile = zipfile.ZipFile(byte_data, 'w')
        
    # add_to_zip(root_page)

    # byte_data.seek(0)

    response = HttpResponse(byte_data.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{root_page.title}.zip"'

    return response

def generate_pdf(context):
    '''
    Generates... 
    '''

    template_path = 'result.html'
    template = get_template(template_path)
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    filename = f"{context.get('title', 'download')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=response, encoding='utf-8')
    if pisa_status.err:
        return HttpResponse('PDF generation failed')
    return response

def generate_csv(context):
    '''
    Generates... 
    '''

    response = HttpResponse(content_type='text/csv')
    filename = f"{context.get('title', 'download')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['Title', 'Headings', 'Paragraphs'])
    rows = zip([context.get('title', 'N/A')], context.get('headings', []), context.get('paragraphs', []))
    for row in rows:
        writer.writerow(row)
    return response

def generate_json(context):
    '''
    Generates... 
    '''

    response = HttpResponse(content_type='application/json')
    filename = f"{context.get('title', 'download')}.json"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    json.dump(context, response, indent=4)
    return response


def zip_file(context):
    '''
    Compresses PDF/CSV/JSON file folders into a downloadable zip.
    Args:
     @
    Returns:
     @ 
    '''
    pass

def outdated(request):
    if 'scraped_data' in request.session:
        context = request.session['scraped_data']
        response = HttpResponse(content_type='')
        if request.POST['download_type'] == 'pdf':
            template_path = 'result.html'
            template = get_template(template_path)
            html = template.render(context)
            response = HttpResponse(content_type='application/pdf')
            filename = f"{context['title']}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            buffer = BytesIO()
            pisa_status = pisa.CreatePDF(html, dest=response, encoding='utf-8')
            if pisa_status.err:
                return HttpResponse('PDF generation failed')
        elif request.POST['download_type'] == 'csv':
            response = HttpResponse(content_type='text/csv')
            filename = f"{context['title']}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)
            writer.writerow(['Title', 'Headings', 'Paragraphs'])
            rows = zip([context['title']], context['headings'], context['paragraphs'])
            for row in rows:
                writer.writerow(row)
        elif request.POST['download_type'] == 'json':
            response = HttpResponse(content_type='application/json')
            filename = f"{context['title']}.json"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            json.dump(context, response, indent=4)
        return response
    else:
        return render(request, 'home.html')