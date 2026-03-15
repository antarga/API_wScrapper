# Flask imports
from flask import Flask, flash, request, render_template, url_for, redirect, jsonify
from flask.helpers import make_response, send_from_directory
from werkzeug.datastructures import cache_property
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Tensorflow model imports
from model.data_utils import Dataset
from model.models import HANNModel
from model.config import Config

# Web Scrapper imports
from bs4 import BeautifulSoup
import requests
import calendar
import urllib.request, urllib.parse, urllib.error
import ssl


# Other imports
from my_sentence_splitting import get_sents

import argparse, os, random, json, fileinput, shutil, glob
import re
import secrets
import pandas as pd
import seaborn as sns
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')


# Base directory of data (subject to change)
base_dir = r'{}'.format(os.getcwd())

print(base_dir)

app = Flask(__name__)

#### Basic Security Measures ####

# Set the secret key to some random bytes.
app.secret_key = secrets.token_bytes(16)

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)
##########################################

# For checking the uploaded file extention
ALLOWED_EXTENSIONS1 = ['json']
ALLOWED_EXTENSIONS2 = ['txt']
def allowed_file1(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS1
def allowed_file2(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS2


# To store variables between routes. Not good practice for multiple users due to potential conflicts, but ok if used by one person at a time.
class DataStore():
    mname = None
    mdl = None
    tst = None
    tags = None
    keyword = None
    num = None

data = DataStore()


# Defining the webpages

@app.errorhandler(429)
def ratelimit_handler(e):
    flash('Error ' + str(e))
    rule = request.url_rule
    if 'run_scrapper' in rule.rule:
        return redirect(url_for('scraby'))
    else:
        return render_template('abstract_input.html')

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/rhesextra')
def rhesextra():
    return render_template('rhesextra.html')


@app.route('/model_choice', methods=['GET','POST'])
def model_choice():

    try:
        if request.method == 'GET':
            flash(f"The URL /model_choice is accessed directly. Redirecting you to '/rhesextra' to choose a model to load first")
            return redirect(url_for('rhesextra'))
    
        if request.method == 'POST':

            # Load the model with the required changes made in the train, config and models.py files
            parser   = argparse.ArgumentParser()

            config = Config(parser, request.form.get('model'))

            model = HANNModel(config)
            model.build()

            test  = Dataset(config.filename_test, config.processing_word,
                            config.processing_tag, config.max_iter)

            model.restore_session(config.dir_model)

            if request.form.get('model') == 'd7class':
                tags_m = 7
            else:
                tags_m = 5
            
            if request.form.get('model') == 'd7class':
                data.mname = '100k'
            elif request.form.get('model') == 'pubmed-20k':
                data.mname = '20k'
            elif request.form.get('model') == 'pubmed-200k':
                data.mname = '200k'

            data.mdl = model
            data.tst = test
            data.tags = tags_m

            return redirect(url_for('abstract_input'))
    except:
        flash('You need to select one of the trained models to proceed.')
        return redirect(url_for('rhesextra'))


@app.route('/abstract_input')
def abstract_input():

    response = make_response(render_template('abstract_input.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
    response.headers["Pragma"] = "no-cache" # HTTP 1.0.
    response.headers["Expires"] = "0" # Proxies.

    return response 


@app.route('/single_ab', methods=['GET','POST'])
@limiter.limit("5 per minute")
def single_ab():
    if request.form.get('abstract_text') == '':
        flash('Input field appears to be empty! Please go back and insert an abstract text.')
        return redirect(url_for('abstract_input'))
    
    if request.method == 'GET':
        flash(f"The URL /single_ab is accessed directly. Redirected you to '/rhesextra' to choose a model to load first")
        return redirect(url_for('rhesextra'))

    if request.method == 'POST':
        final_output = []

        abstract_text = request.form.get('abstract_text')

        # Convert it to the format required by the model
        if data.tags == 7:
            tags_list = ['BACKGROUND', 'METHOD', 'OBJECTIVE', 'RESULT', 'CONCLUSION', 'INTERVENTION', 'POPULATION']
        else:
            tags_list = ['BACKGROUND', 'METHODS', 'OBJECTIVE', 'RESULTS', 'CONCLUSIONS']
        
        with open(os.path.join(base_dir, 'test_folder/temp/abstract_temp.txt'), 'w', encoding='UTF-8') as ab_tmp:
            ab_tmp.write('###' + str(random.randint(1,99999999)).zfill(8) + '\n')
            sentences_split = get_sents(abstract_text)
            for s in sentences_split:
                ab_tmp.write(''.join(random.choices(tags_list)) + ' ' + s.strip() + '\n')
            ab_tmp.write('\n')


        metrics = data.mdl.evaluate(data.tst)
        
        # Delete the file created through this run
        os.remove(os.path.join(base_dir, 'test_folder/temp/abstract_temp.txt'))
    
        # Write the results in json format of predicted_label:sentence
        result_output = {}
        result_output['Result'] = list(map(lambda x, y:(x,y), metrics, sentences_split))
        final_output.append(result_output)


        with open(os.path.join(base_dir, 'test_folder/output/final_output.json'), 'w', encoding='UTF-8') as fw:
            json.dump(final_output, fw, indent=4, ensure_ascii=False)

        return redirect(url_for('results_display_single'))


@app.route('/results_display_single')
def results_display_single():
    
    filename = os.path.join(base_dir, 'test_folder/output/final_output.json')

    with fileinput.FileInput(filename, inplace = True, backup ='.bak') as f:

        for line in f:
            if "[\n" == line:
                print("var data = [", end ='\n')
            elif "]" == line:
                print("];", end ='')
            else:
                print(line, end ='')
            
            
    shutil.move(filename, os.path.join(base_dir, 'static/js/final_output.js'))
    os.rename(os.path.join(base_dir, 'test_folder/output/final_output.json.bak'), os.path.join(base_dir,'test_folder/output/final_output.json'))

    response = make_response(render_template('results_display_single.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
    response.headers["Pragma"] = "no-cache" # HTTP 1.0.
    response.headers["Expires"] = "0" # Proxies.

    return response 


@app.route('/multi_abs', methods=['GET','POST'])
@limiter.limit("5 per minute")
def multi_abs():
    if request.files['abstracts_json'].filename == '':
        flash('No file selected.')
        return redirect(url_for('abstract_input'))

    elif not allowed_file1(request.files['abstracts_json'].filename):
        flash('Wrong file type, please use json.')
        return redirect(url_for('abstract_input'))
    
    if request.method == 'GET':
        flash(f"The URL /single_ab is accessed directly. Redirected you to '/rhesextra' to choose a model to load first")
        return redirect(url_for('rhesextra'))
    
    if request.method == 'POST':
        # Read the initial json file and convert it to the format required by the model
        final_output = []
        
        abs_json = json.load(request.files['abstracts_json'])
        
        for k, v in abs_json.items():

            result_output = {}

            if data.tags == 7:
                tags_list = ['BACKGROUND', 'METHOD', 'OBJECTIVE', 'RESULT', 'CONCLUSION', 'INTERVENTION', 'POPULATION']
            else:
                tags_list = ['BACKGROUND', 'METHODS', 'OBJECTIVE', 'RESULTS', 'CONCLUSIONS']

            with open(os.path.join(base_dir, 'test_folder/temp/abstract_temp.txt'), 'w', encoding='UTF-8') as ab_tmp:
                ab_tmp.write('###' + str(random.randint(1,99999999)).zfill(8) + '\n')
                sentences_split = get_sents(v)
                for s in sentences_split:
                    ab_tmp.write(''.join(random.choices(tags_list)) + ' ' + s.strip() + '\n')
                ab_tmp.write('\n')

            metrics = data.mdl.evaluate(data.tst)

            # Delete the file created through this run
            os.remove(os.path.join(base_dir, 'test_folder/temp/abstract_temp.txt'))
            
            # Write the results in json format of predicted_label:sentence
            result_output[k] = list(map(lambda x, y:(x,y), metrics, sentences_split))
            final_output.append(result_output)
        
        with open(os.path.join(base_dir, 'test_folder/output/final_output.json'), 'w', encoding='UTF-8') as fw:
            json.dump(final_output, fw, indent=4, ensure_ascii=False)

        return redirect(url_for('results_display_multi'))


@app.route('/results_display_multi')
def results_display_multi():
    
    filename = os.path.join(base_dir, 'test_folder/output/final_output.json')

    with fileinput.FileInput(filename, inplace = True, backup ='.bak') as f:

        for line in f:
            if "[\n" == line:
                print("var data = [", end ='\n')
            elif "]" == line:
                print("];", end ='')
            else:
                print(line, end ='')
            
            
    shutil.move(filename, os.path.join(base_dir, 'static/js/final_output.js'))
    os.rename(os.path.join(base_dir, 'test_folder/output/final_output.json.bak'), os.path.join(base_dir,'test_folder/output/final_output.json'))
    
    response = make_response(render_template('results_display_multi.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
    response.headers["Pragma"] = "no-cache" # HTTP 1.0.
    response.headers["Expires"] = "0" # Proxies.
   
    return response 


@app.route('/stats', methods=['GET','POST'])
@limiter.limit("5 per minute")
def stats():
    if request.files['abstracts_txt'].filename == '':
        flash('No file selected.')
        return redirect(url_for('abstract_input'))

    elif not allowed_file2(request.files['abstracts_txt'].filename):
        flash('Wrong file type, please use txt.')
        return redirect(url_for('abstract_input'))
    
    if request.method == 'GET':
        flash(f"The URL /single_ab is accessed directly. Redirected you to '/rhesextra' to choose a model to load first")
        return redirect(url_for('rhesextra'))
    
    if request.method == 'POST':
        # Save the filename for later
        fname = request.files['abstracts_txt'].filename.rsplit('.', 1)[0].replace(' ', '_')

        # Take the input file and save/rename it at the temp folder as the abstract_temp.txt
        abs_txt = request.files['abstracts_txt']
        abs_txt.save(os.path.join(base_dir, 'test_folder/temp/abstract_temp.txt'), buffer_size=6144000)

        # Run inference
        metrics = data.mdl.evaluate(data.tst)
          
        # Create a list with the sentence length of each abstract, a list of lists with the actual sentences and a list with each initial key
        with open(os.path.join(base_dir, 'test_folder/temp/abstract_temp.txt'), 'r', encoding='UTF-8') as fr:
            lines = fr.readlines()

        lc = 0
        sentence_count = []
        ab_keys = []
        ab_sentences = []
        sent_temp = []
        ab_labels = []
        labels_temp = []
        for line in lines:
            if re.match('###[0-9]*\n',line):
                ab_keys.append(line.replace('###', 'AB').strip())
                lc+=1
            elif re.match('\n',line):
                sentence_count.append(lc-1)
                ab_sentences.append(sent_temp)
                sent_temp = []
                ab_labels.append(labels_temp)
                labels_temp = []
                lc = 0
            else:
                sent_temp.append(line.replace('\t', ' ').strip())
                labels_temp.append(line.split('\t')[0])
                lc+=1
        
        # Split the metrics list into sublists based on number of sentences of each abstract
        it = iter(metrics)
        metrics_subl = [[next(it) for _ in range(length)] for length in sentence_count]

        # Write the results in json format of predicted_label:sentence and count common labels percentage       
        final_output = []
        ab_commons = []

        for i, ks in enumerate(ab_keys):
            result_output = {}
            common_bools = []

            result_output[ks] = list(map(lambda x, y:(x,y), metrics_subl[i], ab_sentences[i]))
            final_output.append(result_output)

            for j in range(sentence_count[i]):
                common_bools.append(metrics_subl[i][j]==ab_labels[i][j])
                
            ab_commons.append(int(sum(common_bools)/sentence_count[i]*100))

        with open(os.path.join(base_dir, 'test_folder/output/final_output.json'), 'w', encoding='UTF-8') as fw:
            json.dump(final_output, fw, indent=4, ensure_ascii=False)
        
        # Write an output file for debugging purposes unless it already exists
        if os.path.exists(os.path.join(base_dir, f'test_folder/output/graph_data_{data.mname}_model_{fname}.csv')):
            pass
        else:
            tmp_dict = {'sentences':sentence_count, 'commons':ab_commons}
            df = pd.DataFrame(tmp_dict)
            df.to_csv(os.path.join(base_dir, f'test_folder/output/graph_data_{data.mname}_model_{fname}.csv'), index=False)

        # Create-save a scatterplot of sentence number X commons percentage
        data_plot=pd.DataFrame({'Number of sentences':sentence_count, 'Common Labels (%)':ab_commons})
        sns.scatterplot(x='Number of sentences', y='Common Labels (%)', data=data_plot)
        plt.savefig(os.path.join(base_dir, 'static/images/scatterplot.png'))
        plt.clf()
        plt.close()

        # Delete the file created through this run
        os.remove(os.path.join(base_dir, 'test_folder/temp/abstract_temp.txt'))
    
        return redirect(url_for('results_display_stats'))


@app.route('/results_display_stats')
def results_display_stats():
    
    filename = os.path.join(base_dir, 'test_folder/output/final_output.json')

    with fileinput.FileInput(filename, inplace = True, backup ='.bak') as f: # Sometimes it will throw an error here about encoding but it cannot be resolved unless you change the method to use codecs.open module and os.rename/remove

        for line in f:
            if "[\n" == line:
                print("var data = [", end ='\n')
            elif "]" == line:
                print("];", end ='')
            else:
                print(line, end ='')
            
            
    shutil.move(filename, os.path.join(base_dir, 'static/js/final_output.js'))
    os.rename(os.path.join(base_dir, 'test_folder/output/final_output.json.bak'), os.path.join(base_dir,'test_folder/output/final_output.json'))
    
    response = make_response(render_template('results_display_stats.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
    response.headers["Pragma"] = "no-cache" # HTTP 1.0.
    response.headers["Expires"] = "0" # Proxies.
   
    return response


@app.route('/show_graphs')
def show_graphs():
     
    response = make_response(render_template('show_graphs.html'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1.
    response.headers["Pragma"] = "no-cache" # HTTP 1.0.
    response.headers["Expires"] = "0" # Proxies.
   
    return response


@app.route('/scraby')
def scraby():
    try:
        for file in glob.glob(os.path.join(base_dir, f'test_folder/temp/*.*')):
            os.remove(file)
        return render_template('scraby.html')
    except:
        flash('Something went wrong while trying to load the ScrAby page')
        return redirect(url_for('index'))

@app.route('/run_scrapper', methods=['GET','POST'])
@limiter.limit("2 per minute")
def run_scrapper():

    try:
        request.form.get('_KEYWORD') != ''
        request.form.get('_NUM') != ''
        request.form.get('_NUM').isnumeric()
        int(request.form.get('_NUM')) > 0 and int(request.form.get('_NUM')) <= 20
    
    except:
        flash('You have entered invalid input in one or more of the fields')
        return redirect(url_for('scraby'))

    if request.method == 'GET':
        flash(f"The URL /run_scrapper is accessed directly. Redirected you to '/scraby' to input required parameters by the web scraper")
        return redirect(url_for('scraby'))
    
    if request.method == 'POST':

        # Record the keyword and number input from the user and change the url accordingly
        data.keyword = str(request.form.get('_KEYWORD'))
        data.num = int(request.form.get('_NUM', type=int))
        
        if os.path.exists(os.path.join(base_dir, f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json')):
            filename = os.path.join(base_dir, f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json')
            with fileinput.FileInput(filename, inplace = True, backup ='.bak') as f: # Sometimes it will throw an error here about encoding but it cannot be resolved unless you change the method to use codecs.open module and os.rename/remove

                for line in f:
                    if "[\n" == line:
                        print("var data1 = [", end ='\n')
                    elif "]" == line:
                        print("];", end ='')
                    else:
                        print(line, end ='')
                    
                        
            shutil.move(filename, os.path.join(base_dir, f'static/js/scraby_output.js'))
            os.rename(os.path.join(base_dir, f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json.bak'), os.path.join(base_dir,f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json'))

            return render_template('scraby_results.html')
        
        else:    

            url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=NUM&sort=relevance&term=KEYWORD"

            url = url.replace('NUM', str(data.num))
            url = url.replace('KEYWORD', data.keyword)

            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                # Legacy Python that doesn’t verify HTTPS certificates by default
                pass
            else:
                # Handle target environment that doesn’t support HTTPS verification
                ssl._create_default_https_context = _create_unverified_https_context

            # Search a text query in a single Entrez database.    
            webpage = urllib.request.urlopen(url).read()
            dict_page =json.loads(webpage)
            idlist = dict_page["esearchresult"]["idlist"]

            # Function to extract all relevant element from the html page
            def data_extraction(soup):

                # This function creates a empty variable for each needed element and subsequently fills in the true value if it exists

                # article = soup.find('article')

                # pubmed = ''
                # if soup.find('pmid'):
                #     pubmed += soup.find('pmid').text
                    
                # abstract = ''
                # if article.find('abstracttext'):
                #     abstract = article.find('abstracttext').text
                
                # result = []
                # result.append(pubmed)
                # result.append(abstract)

                # return result
                article = soup.find('article')
                journal = soup.find('journal')

                ArticleTitle = ''
                if article.find('articletitle'):
                        ArticleTitle = '"'
                        title_str = article.find('articletitle').text
                        ArticleTitle += title_str
                        ArticleTitle += '"'

                journal_title = ''
                if journal.find('title'):
                    journal_title = journal.find('title').text
                
                volume = ''
                if journal.find('volume'):
                    volume = journal.find('volume').text
                    if soup.find('issue'):
                        volume += '('
                        volume += soup.find('issue').text
                        volume += ')'
                
                page = ''
                if article.find('pagination'):
                    if '-' in article.find('pagination').text:
                        page = 'pp. '
                        page_str = article.find('pagination').text
                        page_str = page_str.strip('\n')
                        page += page_str
                    else:
                        page = 'p. '
                        page_str = article.find('pagination').text
                        page_str = page_str.strip('\n')
                        page += page_str            
                
                JournalIssue = journal.find('journalissue')
                month = JournalIssue.find('month')
                date = ''
                if month:
                    month = JournalIssue.find('month').text
                    if len(month)<3:
                        month_int = int(str(month))
                        month = calendar.month_abbr[month_int]

                    year = JournalIssue.find('year').text
                    date = '('
                    date += month
                    date += '. '
                    date += year
                    date += '). '
                elif JournalIssue.find('year'):
                    date = '('
                    date+= JournalIssue.find('year').text
                    date += '). '      
                else: ''
                
                pubmed = ''
                if soup.find('articleid'):
                    pubmed += soup.find('pmid').text # switch for pmid articleid
                    doi_pii = article.find_all('elocationid')
                    doi_pii_str = ""
                    if len(doi_pii)>1:
                        if 'doi' in str(doi_pii[0]):
                            doi_pii = doi_pii[0].text
                            doi_pii_str += doi_pii
                        elif 'doi' in str(doi_pii[1]):
                            doi_pii = doi_pii[1].text
                            doi_pii_str += doi_pii
                    elif len(doi_pii) == 1:
                        if 'doi' in str(doi_pii[0]):
                            doi_pii = doi_pii[0].text
                            doi_pii_str += doi_pii
                        elif 'pii' in str(doi_pii[0]):
                            doi_pii = doi_pii[0].text
                            doi_pii_str += doi_pii
                
                abstract = ''
                if article.find('abstracttext'):
                    abstract = article.find('abstracttext').text
                
                result = []
                result.append(['Article Title', ArticleTitle])
                result.append(['Journal', journal_title])
                result.append(['Volume', volume])
                result.append(['Date', date])
                result.append(['PMID', pubmed])
                result.append(['DOI', doi_pii_str])
                result.append(['Abstract', abstract])

                return result


            articles_list = []

            # Loop over each element in the idlist to get the full records for each UID and feed it into the data_extraction function
            for link in idlist:
                articles_dict = {}

                url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=idlist"
                url = url.replace('idlist', link)

                try:
                    _create_unverified_https_context = ssl._create_unverified_context
                except AttributeError:
                    # Legacy Python that doesn’t verify HTTPS certificates by default
                    pass
                else:
                    # Handle target environment that doesn’t support HTTPS verification
                    ssl._create_default_https_context = _create_unverified_https_context
                
                r = requests.get(url)
                soup = BeautifulSoup(r.content, "html.parser")
                article = data_extraction(soup)
                articles_dict[f'{article[4][1]}'] = article
                articles_list.append(articles_dict)

            with open(os.path.join(base_dir, f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json'), 'w', encoding='UTF-8') as fw:
                json.dump(articles_list, fw, indent=4, ensure_ascii=False)

            filename = os.path.join(base_dir, f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json')

            with fileinput.FileInput(filename, inplace = True, backup ='.bak') as f: # Sometimes it will throw an error here about encoding but it cannot be resolved unless you change the method to use codecs.open module and os.rename/remove

                for line in f:
                    if "[\n" == line:
                        print("var data1 = [", end ='\n')
                    elif "]" == line:
                        print("];", end ='')
                    else:
                        print(line, end ='')
                    
                        
            shutil.move(filename, os.path.join(base_dir, f'static/js/scraby_output.js'))
            os.rename(os.path.join(base_dir, f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json.bak'), os.path.join(base_dir,f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json'))

            return render_template('scraby_results.html')

@app.route('/scraby_log', methods=['GET','POST'])
def scraby_log():
    chosen_abs = request.get_json()
    stripped = [s.strip() for s in chosen_abs]
    with open(os.path.join(base_dir,f'test_folder/temp/tempOut.json'), 'w', encoding='UTF-8') as to:
        json.dump(chosen_abs, to, indent=4, ensure_ascii=False)

    try:
        with open(os.path.join(base_dir,f'test_folder/output/scraby_{data.keyword}_{str(data.num)}.json'), 'r', encoding='UTF-8') as fr, open(os.path.join(base_dir,f'test_folder/temp/scraby_{data.keyword}_{str(data.num)}_temp.json'), 'w', encoding='UTF-8') as fw:
            json2change = json.load(fr)
            
            ndict =  {}

            for elem in json2change:
                for k, v in elem.items():
                    if chosen_abs:
                        if k in stripped:
                            ndict[k] = v[6][1]
                    else:
                        ndict[k] = v[6][1]

            json.dump(ndict, fw, indent=4, ensure_ascii=False)

        return render_template('scraby_results.html')
    
    except FileNotFoundError:
        # abort(404)
        flash ('Error 404: File not found')
        return render_template('scraby_results.html')



@app.route('/scraby_save', methods=['GET','POST'])
def scraby_save():
    try:
        return send_from_directory(os.path.join(base_dir, f'test_folder/temp'), filename = f'scraby_{data.keyword}_{str(data.num)}_temp.json', as_attachment=True, cache_timeout=-1)
    except FileNotFoundError:
        # abort(404)
        flash ('Error 404: File not found. You need to log choices first')
        return render_template('scraby_results.html')
    


if __name__ == '__main__':
    app.jinja_env.cache = {}
    app.jinja_env.autoescape = True 
    app.run(debug=True, threaded=True, use_reloader=False)