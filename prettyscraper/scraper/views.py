# Imports from Django libraries. 
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.urls import path
from django.template.loader import get_template
# Import from other libraries
import requests
import csv
import json
from bs4 import BeautifulSoup
from io import BytesIO
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa
# Imports from our models.
from .models import Page, Link

def home(request):
    '''
    This is the default homepage. 
    '''
    return render(request, 'home.html')
        
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

def get_page_content_bundle(request, url, max_depth, curr_depth):
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
    page = requests.get(url)
    if not page:
        error_message = "ERROR: Failed to get network response."
        print(error_message)
        messages.error(request, error_message)
        return

    # Use BeautifulSoup to parse page.
    soup = BeautifulSoup(page.content, 'html5lib')
    if not soup:
        error_message = "ERROR: Failed to parse page content."
        print(error_message)
        messages.error(request, error_message)

    # Find all URLs on page. 
    hrefs = []
    for a in soup.find_all('a', href=True):
        hrefs.append(a['href'])
    
    # Recursively call this function with new URLs. 
    for link in hrefs:
        if link:
            get_page_content_bundle(request, link, max_depth, curr_depth + 1)

    # Construct JSON file to store current page content.
    page_content = {
        'main' : soup,
        'hrefs' : hrefs,
    }

    print(f'Soup is {soup}, with a list of links {hrefs}')
    return page_content
        
def main(request):
    '''
    This function handles requests.
    It should direct user to download page when a file bundle is ready.
    TODO: For the result page (or maybe just a new section on home page, we need an scrape another button)
    '''
    if request.method == 'POST':

        url = request.POST.get('input_url', None)
        max_depth = int(request.POST.get('depth', 1))
        bundle = get_page_content_bundle(request, url, max_depth, 1)
        return render(request, 'result.html', bundle)

    else:

        return render(request, 'home.html')
        
def download_file(request):
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