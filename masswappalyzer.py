#!/usr/bin/env python3

# Run Wappalyzer asynchronously on a list of URLs and generate an output file (Excel, CSV, or JSON) containing all results.

import argparse
import os
import subprocess
import json
import shlex
from typing import List, Optional
from urllib.parse import urlparse
import tempfile
import functools
import concurrent.futures
import re
import shutil
import csv
import copy
import traceback

import pandas as pd
import xlsxwriter
import tqdm

##### Static methods 

def ensure_keys(dictionnary:dict, keys:list, default="") -> dict:
    for k in keys:
        dictionnary.setdefault(k, default)
    return dictionnary

def get_valid_filename(s:str) -> str:
    '''Return the given string converted to a string that can be used for a clean filename.  Stolen from Django I think'''
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def clean(s:str) -> str:
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
        
        with xlsxwriter.Workbook(excel_file.name) as workbook:
            # Ensure all item share the same set of keys
            all_keys = set()
            for i in items: [ all_keys.add(clean(str(k))) for k in i ] 
            
            elements = [ ensure_keys({ clean(str(k)):v for k,v in element.items() }, all_keys) for element in items ]
            
            worksheet = workbook.add_worksheet()
            _fill_xlsx_worksheet(elements, worksheet, headers, index_column)

            # Creates DataFrame and write the transposed data to Excel file.  
            headers_title = [ e[index_column] for e in elements ]
            new_elements = copy.deepcopy(elements)
            [ e.pop(index_column) for e in new_elements ] 
            df = pd.DataFrame(new_elements, index=headers_title)
            transposed_data = df.transpose().reset_index().to_dict('records')
            new_worksheet = workbook.add_worksheet()
            _fill_xlsx_worksheet(transposed_data, new_worksheet)
                
        return excel_file

def async_do(func, data, func_args=None, asynch=False,  workers=None , progress=False, desc='Loading...'):
        """
        Wrapper arround executable and the data list object.
        Will execute the callable on each object of the list.
        Parameters:  
        
        - `func`: Callable function. func is going to be called like `func(item, **func_args)` on all items in data.
        - `data`: Call func on each element if the list.
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

def ensure_scheme(url:str) -> str:
    # Strip URL string
    url=url.strip()
    # Format URL with scheme indication if not already present
    p_url=list(urlparse(url))
    if p_url[0]=="": 
        url='http://'+url
    return url


##### Core

class Technology:
    """
    A detected technology.
    """
    def __init__(self, url:str, name:str, version:Optional[str]=None) -> None:
        self.url = url
        self.name = name
        self.version: Optional[str] = version

class IWappalyzer:
    def analyze(self, host) -> List[Technology]:
        ...

class PythonWappalyzer(IWappalyzer):
    
    def __init__(self) -> None:
        try:
            import Wappalyzer
        except ImportError:
            print("Please install python-Wappalyzer.")
            exit(1)

        self.Wappalyzer = Wappalyzer
        self._wappalyzer = self.Wappalyzer.Wappalyzer.latest(update=True)
    
    def analyze(self, host:str) -> List[Technology]:

        results = self._wappalyzer.analyze_with_versions_and_categories(
            self.Wappalyzer.WebPage.new_from_url(ensure_scheme(host)))
        
        techs = []
        for tech_name, info in results.items():
            tech = Technology(host, name=tech_name)
            if info['versions']:
                tech.version = info['versions'][0]
            techs.append(tech)
        return techs
            
class JsWappalyzer(IWappalyzer):
    def __init__(self, path:Optional[str]=None, args:Optional[str]=None, timeout:int=1000) -> None:
        self.wappalyzerpath = None
        if not path:
            if shutil.which("wappalyzer"):
                self.wappalyzerpath = [ 'wappalyzer' ]
            elif shutil.which("docker"):
                # Test if docker image is installed
                o = subprocess.run( args=[ 'docker', 'image', 'ls' ], stdout=subprocess.PIPE )
                if 'wappalyzer/cli' in o.stdout.decode() :
                    self.wappalyzerpath = [ 'docker', 'run', '--rm', 'wappalyzer/cli' ]
            if self.wappalyzerpath is None:
                raise RuntimeError("Can't find wappalyzer/cli in your system.")
        else:
            self.wappalyzerpath = shlex.split(path)
        self.wappalyzerargs = shlex.split(args) if args else []
        self.timeout = timeout

    def analyze(self, host:str) -> List[Technology]:
        cmd = self.wappalyzerpath + [ensure_scheme(host)] + self.wappalyzerargs
        p = subprocess.run(args=cmd, timeout=self.timeout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if p.returncode == 0:
            result = json.loads(p.stdout)
        else:
            print(f"wappalyzer/cli failed: {p.stdout}\n{p.stderr}")
            return []
        
        techs = []
        for r in result['technologies']:
            t = Technology(host, name=r['name'], version=r['version'] or None)
            techs.append(t)
        return techs

class WappalyzerWrapper(object):

    def __init__(self, wappalyzerpath=None, wappalyzerargs=None, python=False):
        self._analyze = None
        
        if not python:
            try:
                wap = JsWappalyzer(path=wappalyzerpath, args=wappalyzerargs)
                self._analyze = wap.analyze
                print("Using wappalyzer/cli: {}".format(' '.join(wap.wappalyzerpath)))
            except RuntimeError:
                pass
        if not self._analyze:
            print("Using python-Wappalyzer")
            self._analyze = PythonWappalyzer().analyze
            
        
        self.results: List[List[Technology]] = []

    def analyze(self, host) -> List[Technology]:    
        techs = self._analyze(host)
        self.results.append(techs)
        return techs
    
class MassWappalyzer(object):

    def __init__(self, 
        urls, 
        outputfile,  
        asynch_workers=5, 
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

        self.analyzer = WappalyzerWrapper(
            **kwargs)

    def run(self):

        try:

            raw_results = async_do(
                self.analyzer.analyze, 
                self.urls, 
                asynch=True, 
                workers=self.asynch_workers, 
                progress=True,
                desc="Analyzing...")

        except KeyboardInterrupt:
            print("Quitting...")
            raw_results = self.analyzer.results

        except Exception as e:
            print(f"Error while analyzing: {e}\n{traceback.format_exc()}")
            raw_results = self.analyzer.results

        finally:

            # Find the template Website keys and init a new class dynamically
            # Keys: urls, applications meta
            all_apps = set()
            for items in raw_results:
                for item in items:
                    all_apps.add(clean(item.name))
            
            print("All technologies seen: ")
            all_apps = sorted(all_apps)
            print(all_apps)

            excel_structure = []
            
            # Append each Website as dict
            for items in raw_results:
                if not items:
                    continue
                website_dict = {'Url': items[0].url}
                
                for item in items:
                    # Display values of application structure in a human readable manner
                    website_dict.update( {clean(item.name): f'Detected{(", version "+item.version) if item.version else ""}'} )
                    # Append dict to structure
                
                excel_structure.append(ensure_keys(website_dict, all_apps))

            if not excel_structure:
                print("No valid results, quitting.")
                exit(1)

            # Writting output file
            if self.outputformat == 'xlsx':
                print("Creating Excel file {}".format(self.outputfile))

                excel_file = get_xlsx_file(excel_structure, index_column="Url")
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
        description='Run Wappalyzer asynchronously on a list of URLs and generate an output file (Excel, CSV, or JSON) containing all results.', 
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
        help='Use full Python Wappalyzer implementation "python-Wappalyzer" even if Wappalyzer CLI is installed with NPM or docker.',
        required=False)
    return(parser.parse_args())

def main():

    args = vars(parse_arguments())

    urls = file_to_list(args.pop('inputfile'))

    mass_w = MassWappalyzer(urls, **args)

    mass_w.run()

    exit(0)

if __name__=="__main__":
    main()
