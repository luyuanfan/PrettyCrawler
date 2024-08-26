# Imports from Django libraries. 
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.urls import path
from django.template.loader import get_template
import requests
import csv
import json
from bs4 import BeautifulSoup
from io import BytesIO
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa

def home(request):
    '''
    This is the default homepage. 
    '''
    return render(request, 'home.html')
        
def validate_url(url):
    '''
    This function validates user's input URL.
    If the URL is not valid, it should notify the user. 
    '''
    validate = URLValidator()

    # TODO: connect to frontend and notify user. 
    if url:
        try:
            validate(url)
        except ValidationError as e:
            return False, str(e)
        return True, 'URL exists.'
    return False, 'Please enter an URL.'

def parse_page_content(page):
    '''
    This function parses page content with BeautifulSoup. 
    It returns a JSON file? 
    '''
    soup = BeautifulSoup(page.content, 'html5lib')
    # TODO: check if soup is valid. 
    if not soup:
        error_message = "ERROR: Failed to parse page content."
        print(error_message)
        messages.error(request, error_message)

    print(f'Printing out soup content: {soup.string}')

    # title = soup.title.string

    # headings = []
    # for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
    #     headings.append(heading.text.strip())

    # paragraphs = []
    # for paragraph in soup.find_all('p'):
    #     paragraphs.append(paragraph.text.strip())

    hrefs = []
    for href in soup.find_all('a', href=True):
        hrefs.append(a['href'].text.strip())
    
    print(f'Found all hyperlinks: {hrefs}')
    
    context = {
        # 'title': title,
        # 'headings': headings,
        # 'paragraphs': paragraphs,
        'hrefs' : hrefs,
    }
    return context

def get_page_content_bundle(url, depth):
    if depth == 0:
        return []

    page = requests.get(url)
    if not page:
        error_message = "ERROR: Failed to get network response."
        print(error_message)
        messages.error(request, error_message)
        return redirect('home')

    # Use BeautifulSoup to parse the page content. 
    context = parse_page_content(page)
    # for link in context.hrefs:
    print(f'Back in get_page_content_bundle')
        

def execute(request):
    if request.method == 'POST':

        # Get user's input, check if it's valid, and submit a HTTP request. 
        url = request.POST.get('input_url', None)
        depth = request.POST.get('depth', 1) # Depth is number, ensured at frontend. 

        is_valid, error_message = validate_url(url)
        if not is_valid:
            print(f'ERROR: URL is not valid: {error_message}')
            messages.error(request, error_message)
            # TODO: Notify user that this URL is not valid.
            return redirect('home')
        
        bundle = get_page_content_bundle(url, depth)

        # print(f"\nAfter parse_page_content function: HTML content is:\n {context}\n")
        request.session['scraped_data'] = context

        return render(request, 'result.html', context)
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