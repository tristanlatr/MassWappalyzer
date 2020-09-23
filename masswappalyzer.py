#!/usr/bin/env python3

# Run Wappalyzer asynchronously on a list of URLs and generate a excel file with all Wappalyzer informations

import argparse
import os
import subprocess
import json
import shlex
from urllib.parse import urlparse
import tempfile
import functools
import concurrent.futures
import re
from collections import namedtuple
import shutil
import csv
import copy
import requests

##### Static methods 

def ensure_keys(dictionnary, keys, default_val=""):
    row = namedtuple('row', list(set(list(dictionnary.keys()) + list(keys) )) )
    row.__new__.__defaults__ = (default_val,) * len(row._fields) # set default values to empty string if not specified
    return row(**dictionnary)._asdict()

def get_valid_filename(s):
    '''Return the given string converted to a string that can be used for a clean filename.  Stolen from Django I think'''
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def clean(s):
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '', s)
    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '', s)
    if s.isnumeric(): s = '_' + s
    return s

def _fill_xlsx_worksheet(elements, worksheet, headers=None, index_column=None):
    if not headers:
        headers={ key:str(key).title() for key in elements[0].keys() }
    # Recreate header, insert index_column first if specified
    if index_column:
            old_headers = copy.deepcopy(headers)
            old_headers.pop(index_column)
            headers=dict()
            headers[index_column]=index_column.title()
            headers.update(old_headers)
    worksheet.write_row(row=0, col=0, data=headers.values())
    header_keys = [ k for k in headers ]
    for index, item in enumerate(elements):
        row = map(lambda field_id: str(item.get(field_id, '')), header_keys)
        worksheet.write_row(row=index + 1, col=0, data=row)
    worksheet.autofilter(0, 0, len(elements)-1, len(headers.keys())-1)

def get_xlsx_file(items, index_column, headers=None):
    """
    Argments:  
    - items: list of dict  
    - headers: dict like {'key':'Key nice title for Excel'}. Leave None to auto generate  
    - index_column: str. The column name will be placed on the top left side.  
            Case sensitive.  str.title() will be then applied. Should work since python 3.7 .  

    Return excel file as tempfile.NamedTemporaryFile
    Return None if xlsxwriter is not installed
    """
    with tempfile.NamedTemporaryFile(delete=False) as excel_file:
        try: 
            import xlsxwriter
        except ImportError:
            return None
        else:
            with xlsxwriter.Workbook(excel_file.name) as workbook:
                # Ensure all item share the same set of keys
                all_keys = set()
                for i in items: [ all_keys.add(clean(str(k))) for k in i ] 
                
                elements = [ ensure_keys({ clean(str(k)):v for k,v in element.items() }, all_keys) for element in items ]
                
                worksheet = workbook.add_worksheet()
                _fill_xlsx_worksheet(elements, worksheet, headers, index_column)

                try: 
                    import pandas as pd

                except ImportError:
                    return excel_file

                else:
                    # Creates DataFrame and write the transposed data to Excel file.  
                    headers_title = [ e[index_column] for e in elements ]
                    new_elements = copy.deepcopy(elements)
                    [ e.pop(index_column) for e in new_elements ] 
                    df = pd.DataFrame(new_elements, index=headers_title)
                    transposed_data = df.transpose().reset_index().to_dict('records')
                    new_worksheet = workbook.add_worksheet()
                    _fill_xlsx_worksheet(transposed_data, new_worksheet)
                    
        return excel_file

def perform(func, data, func_args=None, asynch=False,  workers=None , progress=False, desc='Loading...'):
        """
        Wrapper arround executable and the data list object.
        Will execute the callable on each object of the list.
        Parameters:  
        
        - `func`: callable stateless function. func is going to be called like `func(item, **func_args)` on all items in data.
        - `data`: if stays None, will perform the action on all rows, else it will perfom the action on the data list.
        - `func_args`: dict that will be passed by default to func in all calls.
        - `asynch`: execute the task asynchronously
        - `workers`: mandatory if asynch is true.
        - `progress`: to show progress bar with ETA (if tqdm installed).  
        - `desc`: Message to print if progress=True  
        Returns a list of returned results
        """
        if not callable(func) :
            raise ValueError('func must be callable')
        #Setting the arguments on the function
        func = functools.partial(func, **(func_args if func_args is not None else {}))
        #The data returned by function
        returned=list() 
        elements=data
        try: import tqdm
        except ImportError: progress=False
        tqdm_args=dict()
        #The message will appear on loading bar if progress is True
        if progress is True :
            tqdm_args=dict(desc=desc, total=len(elements))
        #Runs the callable on list on executor or by iterating
        if asynch == True :
            if isinstance(workers, int) :
                if progress==True :
                    returned=list(tqdm.tqdm(concurrent.futures.ThreadPoolExecutor(
                    max_workers=workers ).map(
                        func, elements), **tqdm_args))
                else:
                    returned=list(concurrent.futures.ThreadPoolExecutor(
                    max_workers=workers ).map(
                        func, elements))
            else:
                raise AttributeError('When asynch == True : You must specify a integer value for workers')
        else :
            if progress==True:
                elements=tqdm.tqdm(elements, **tqdm_args)
            for index_or_item in elements:
                returned.append(func(index_or_item))
        return(returned)

def file_to_list(path):
    the_list=list()
    with open(path , 'r', encoding='utf-8') as the_file:
        for line in the_file.readlines() :
            item=str(line).strip()
            if(len(item)>0 and item[0]!='#' and item[0]!=';'):
                the_list.append(item)
    return(the_list)

##### Core

class WappalyzerWrapper(object):

    TIMEOUT=500

    def __init__(self, verbose=False, wappalyzerpath=None, wappalyzerargs=None, python=False):
        if not wappalyzerpath:

            if shutil.which("wappalyzer"):
                wappalyzerpath = [ 'wappalyzer' ]

            elif shutil.which("docker"):
                # Test if docker image is installed
                o = subprocess.run( args=[ 'docker', 'image', 'ls' ], stdout=subprocess.PIPE )
                if 'wappalyzer/cli' not in o.stdout.decode() :
                    self.wappalyzerpath = None
                else:
                    self.wappalyzerpath = [ 'docker', 'run', '--rm', 'wappalyzer/cli' ]
            else:
                self.wappalyzerpath = None
        else:
            self.wappalyzerpath = shlex.split(wappalyzerpath)

        if not self.wappalyzerpath :
            self.wappalyzerargs = None
            self.python = True
            
        elif python:
            self.python = True

        else:
            self.wappalyzerargs = shlex.split(wappalyzerargs) if wappalyzerargs else []
            self.python = False
        
        self.verbose = verbose

        if self.python:
            print("Using python-Wappalyzer")
            try:
                from Wappalyzer import Wappalyzer, WebPage
                self.webpage=WebPage.new_from_url
                lastest_technologies_file = requests.get('https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json')
                with open('/tmp/lastest_technologies_file.json', 'w') as t_file:
                    t_file.write(lastest_technologies_file.text)
                self.wappalyzer = Wappalyzer.latest(technologies_file='/tmp/lastest_technologies_file.json')

            except ImportError:
                print("Please install python-Wappalyzer")
                exit(1)
        else:
            print("Using Wappalyzer CLI: {}".format(' '.join(self.wappalyzerpath)))

        self.results = []

    def analyze(self, host):    

        # Strip URL string
        host=host.strip()
        # Format URL with scheme indication if not already present
        p_url=list(urlparse(host))
        if p_url[0]=="": 
            host='http://'+host
        result=None

        if self.python:

                if self.verbose:
                    print("Analyzing {} with python-Wappalyzer".format(host))
                try:
                    apps = self.wappalyzer.analyze_with_versions_and_categories(self.webpage(host))

                    if self.verbose:
                        print("{} technologies: {}".format(host, apps))
                    
                    # Make the format like the real Wappalyzer with the minimal infos
                    # Works with python-Wappalyzer 0.2.3
                    result = dict()
                    result['urls'] = {host:{'status':'OK'}}
                    result['applications'] = list()

                    for tech_name, infos in apps.items(): 
                        app_dict=dict()
                        app_dict['name']=tech_name
                        app_dict.update(infos)
                        result['applications'].append(app_dict)

                except Exception as e:
                    return RuntimeError(str(e))

        elif self.wappalyzerpath:   

            cmd = self.wappalyzerpath + [host] + self.wappalyzerargs
            if self.verbose: print("Analyzing: "+str(cmd))

            try:
                p = subprocess.run(args=cmd, timeout=self.TIMEOUT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if self.verbose:
                    print("{} technologies: {}".format(host, p.stdout))

                if p.returncode == 0:
                    result = json.loads(p.stdout)
                else:
                    return RuntimeError("Wappalyzer failed:\n{}{}".format(p.stdout.decode(), p.stderr.decode()))

            except subprocess.TimeoutExpired:
                return RuntimeError('Analyzing {} too long, process killed.'.format(host))
        else:
            return RuntimeError('No Wappalyzer engine')

        self.results.append(result)
        return result
    
class MassWappalyzer(object):

    def __init__(self, 
        urls, 
        outputfile,  
        asynch_workers=5, 
        verbose=False, 
        outputformat="xlsx",
        **kwargs):

        print('Mass Wappalyzer')
        
        self.urls=urls
        # Automatically setting output file extension if not already set
        if len(outputfile.split('.'))>0:
            if outputfile.split('.')[-1].lower() != outputformat:
                self.outputfile = outputfile + "." + outputformat
            else:
                self.outputfile = outputfile
        else: 
            self.outputfile = outputfile + "." + outputformat
        self.outputformat=outputformat
        self.asynch_workers=asynch_workers
        self.verbose=verbose
        

        self.analyzer = WappalyzerWrapper(
            verbose=verbose,
            **kwargs)

    def run(self):

        try:

            raw_results = perform(
                self.analyzer.analyze, 
                self.urls, 
                asynch=True, 
                workers=self.asynch_workers, 
                progress=True)

        except KeyboardInterrupt:
    
            raw_results = self.analyzer.results

        finally:

            # Find the template Website keys and init a new class dynamically
            # Keys: urls, applications meta
            all_apps=set()
            for item in raw_results:
                if isinstance(item, dict):
                    for app in item['applications']:
                        all_apps.add(clean(app['name']))
            
            print("All applications seen: ")
            all_apps=sorted(all_apps)
            print(all_apps)

            excel_structure = []
            # Append each Website as dict
            for item in raw_results:
                if isinstance(item, dict):

                    website_dict=dict()
                    website_dict['Urls']='\n'.join([ '{} ({})'.format(url, item['urls'][url]['status']) for url in item['urls'] ])
                    website_dict['Last_Url']= list(item['urls'].keys())[-1]

                    for app in item['applications']:
                        # Litte dict comprehsion in order to correctly and dynamically display 
                        #   values of application structure in a human readable manner
                        website_dict.update(
                            {
                                clean(app['name']):'\n'.join([
                                    '{}: {}'.format(
                                        k.title(), 
                                        v if not isinstance(v, dict) else 
                                            ', '.join([ '{} - {}'.format(k1,v1) for (k1,v1) in v.items() ])) 
                                            for (k,v) in app.items() if k not in ['name', 'icon', 'confidence'] and v
                                    ])
                            }
                        )
                    # Append dict to tructure
                    excel_structure.append(ensure_keys(website_dict, all_apps))

                elif isinstance(item, RuntimeError):
                    print(str(item))

            if not excel_structure:
                print("No valid results, quitting.")
                exit(1)

            # Writting output file
            if self.outputformat == 'xlsx':
                print("Creating Excel file {}".format(self.outputfile))

                excel_file = get_xlsx_file(excel_structure, index_column="Last_Url")
                shutil.copyfile(excel_file.name, self.outputfile)
                os.remove(excel_file.name)

            elif self.outputformat == 'csv':
                print("Creating CSV file {}".format(self.outputfile))
                with open(self.outputfile, 'w') as csvfile:
                    d = csv.DictWriter(csvfile, fieldnames=list(k.title() for k in excel_structure[0].keys()))
                    d.writeheader()
                    for row in excel_structure:
                        d.writerow({k.title():' '.join(v.splitlines()) for (k,v) in row.items()})

            else:
                print("Creating JSON file {}".format(self.outputfile))
                with open(self.outputfile, 'w') as jsonfile:
                    json.dump(excel_structure, jsonfile, indent=4)
            
            print('Done')

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Run Wappalyzer asynchronously on a list of URLs and generate a Excel file containing all results.', 
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, 
        prog="python3 -m masswappalyzer")
    parser.add_argument(
        '-i', '--inputfile', 
        metavar='Input file', 
        help='Input file, the file must contain 1 host URL per line.', 
        required=True)
    parser.add_argument('-o', '--outputfile', 
        metavar="Output file", 
        help='Output file containning all Wappalyzer informations. ', 
        default="MassWappalyzerResults")
    parser.add_argument('-f', '--outputformat', 
        metavar="Format", 
        help="Indicate output format. Choices: 'xlsx', 'csv', 'json'.", 
        default='xlsx', 
        choices=['xlsx', 'csv', 'json'])
    parser.add_argument('-w', '--wappalyzerpath', 
        metavar='Wappalyzer path', 
        help='Indicate the path to the Wappalyzer CLI executable. Auto detect by default. Use "python-Wappalyzer" if Wappalyzer CLI not found. ')
    parser.add_argument('-c', '--wappalyzerargs', 
        metavar='Wappalyzer arguments', 
        help='Indicate the arguments of the Wappalyzer CLI command as string. Not applicable if using "python-Wappalyzer".', 
        default='--pretty --probe --user-agent="Mozilla/5.0"')
    parser.add_argument('-a', '--asynch_workers', 
        metavar="Number", 
        help='Number of websites to analyze at the same time', 
        default=5, type=int)
    parser.add_argument('-p', '--python', 
        action='store_true', 
        help='Use full Python Wappalyzer implementation "python-Wappalyzer" even if Wappalyzer CLI is installed with NPM or docker.')
    parser.add_argument('-v', '--verbose', 
        help='Print what Wappalyzer prints', 
        action='store_true')
    return(parser.parse_args())

def main():

    args = vars(parse_arguments())

    urls = file_to_list(args.pop('inputfile'))

    mass_w = MassWappalyzer(urls, **args)

    mass_w.run()

if __name__=="__main__":
    main()
