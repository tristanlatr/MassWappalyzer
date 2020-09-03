#!/usr/bin/env python3

VERSION="1.0"
# Run Wappalyzer asynchronously on a list of URLs and generate a excel file with all Wappalyzer informations

import argparse
import os
import subprocess
from datetime import datetime
import json
import shlex
from urllib.parse import urlparse
import tempfile
import functools
import concurrent.futures
import re
from collections import namedtuple
import shutil

##### Static methods 

def get_valid_filename(s):
    '''Return the given string converted to a string that can be used for a clean filename.  Stolen from Django I think'''
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def get_xlsx_file(items, headers=None):
    """
    Argments:  
    - items: list of dict  
    - headers: dict like {'key':'Key nice title for Excel'}  

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
                if not headers:
                    headers={ key:key.title() for key in items[0].keys() }
                worksheet = workbook.add_worksheet()
                worksheet.write_row(row=0, col=0, data=headers.values())
                header_keys = list(headers.keys())
                cell_format = workbook.add_format()
                for index, item in enumerate(items):
                    row = map(lambda field_id: str(item.get(field_id, '')), header_keys)
                    worksheet.write_row(row=index + 1, col=0, data=row)
                    worksheet.set_row(row=index + 1, height=13, cell_format=cell_format)
                worksheet.autofilter(0, 0, len(items)-1, len(headers.keys())-1)

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

def clean(s):
    
   # Remove invalid characters
   s = re.sub('[^0-9a-zA-Z_]', '', s)

   # Remove leading characters until we find a letter or underscore
   s = re.sub('^[^a-zA-Z_]+', '', s)

   return s

##### Core

class WapalyzerWrapper(object):

    TIMEOUT=500

    def __init__(self, wappalyzerpath, verbose=False, wappalyzerargs=None):
        self.wappalyzerpath = shlex.split(wappalyzerpath)
        self.verbose = verbose
        self.wappalyzerargs = shlex.split(wappalyzerargs) if wappalyzerargs else []
        self.results = []

    def analyze(self, host):    

        # Strip URL string
        host=host.strip()
        # Format URL with scheme indication if not already present
        p_url=list(urlparse(host))
        if p_url[0]=="": 
            host='http://'+host

        cmd = self.wappalyzerpath + [host] + self.wappalyzerargs
        if self.verbose: print("Running: "+str(cmd))

        try:
            p = subprocess.run(args=cmd, timeout=self.TIMEOUT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if self.verbose:
                print(p.stdout)

            if p.returncode == 0:
                self.results.append(json.loads(p.stdout))
                return json.loads(p.stdout)
            else:
                return RuntimeError("Wappalyzer failed:\n{}{}".format(p.stdout.decode(), p.stderr.decode()))

        except subprocess.TimeoutExpired:
            return RuntimeError('Analyzing {} too long, process killed'.format(host))

def parse_arguments():
    parser = argparse.ArgumentParser(description='Run Wappalyzer asynchronously on a list of URLs and generate a Excel file containing all results.', formatter_class=argparse.ArgumentDefaultsHelpFormatter, prog="python3 -m masswappalyzer")
    parser.add_argument('-i', '--inputfile', metavar='Input file', help='Input file, the file must contain 1 host URL per line.', required=True)
    parser.add_argument('-o', '--outputfile', metavar="Output Excel file", help='Output excel file containning all Wappalyzer informations', default='WappalyzerResults.xlsx')
    parser.add_argument('-w', '--wappalyzerpath', metavar='Wappalyzer path', help='Indicate the path to the Wappalyzer executable. Use docker by default.', default='docker run --rm wappalyzer/cli')
    parser.add_argument('-c', '--wappalyzerargs', metavar='Wappalyzer arguments', help='Indicate the arguments of the Wappalyzer command as string', default='--pretty --probe --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36"')
    parser.add_argument('-a', '--asynch_workers', metavar="Number", help='Number of websites to analyze at the same time', default=5, type=int)
    parser.add_argument('-v', '--verbose', help='Print what Wappalyzer prints', action='store_true')
    return(parser.parse_args())
    
class MassWappalyzer(object):
    def __init__(self, urls, outputfile, wappalyzerpath, wappalyzerargs, asynch_workers, verbose, **kwargs):
        print('Mass Wappalyzer {}'.format(VERSION))
        
        self.urls=urls
        self.outputfile=outputfile
        self.wappalyzerpath=wappalyzerpath
        self.asynch_workers=asynch_workers
        self.verbose=verbose

        self.analyzer = WapalyzerWrapper(
            wappalyzerpath=wappalyzerpath,
            verbose=verbose, 
            wappalyzerargs=wappalyzerargs)

    def run(self):

        try:

            raw_results = perform(
                self.analyzer.analyze, 
                self.urls, 
                asynch=True, 
                workers=self.asynch_workers, 
                progress=True)

        except KeyboardInterrupt:
            
            print("Interrupting")
            raw_results = self.analyzer.results

        finally:
            # Find the template Website keys and init a new class dynamically
            # Keys: urls, applications meta
            all_keys=set()
            for item in raw_results:
                if isinstance(item, dict):
                    for app in item['applications']:
                        all_keys.add(clean(app['name']))
            
            print("All applications seen: ")
            print(all_keys)

            # Website object: namedtuple dynamically created with all possible applications as column fields
            all_keys.add("Urls")
            Website = namedtuple('Website', all_keys)
            Website.__new__.__defaults__ = ("",) * len(Website._fields) # set default values to empty string if not specified

            excel_structure = []
            # Append each Website as dict
            for item in raw_results:
                if isinstance(item, dict):
                    website_dict=dict()
                    website_dict.update({'Urls': ', '.join([ url for url in item['urls'] ]) })
                    for app in item['applications']:
                        # Litte dict comprehsion in order to correctly and dynamically display 
                        #   values of application structure in a human readable manner
                        website_dict.update(
                            {
                                clean(app['name']):'\n'.join([
                                    '{}: {}'.format(
                                        k.title(), 
                                        v if not isinstance(v, dict) else 
                                            ', '.join([ '{} - {}'.format(k1,v1) for k1,v1 in v.items() ])) 
                                            for k,v in app.items() if k not in ['name', 'icon']
                                    ])
                            }
                        )
                    # Use custom name tuple with  default values to empty string
                    website = Website(**website_dict)
                    excel_structure.append(website._asdict())
                elif isinstance(item, RuntimeError):
                    print(str(item))

            print("Creating Excel file {}".format(self.outputfile))

            excel_file = get_xlsx_file(excel_structure)
            shutil.copyfile(excel_file.name, self.outputfile)
            os.remove(excel_file.name)

            print('Done')

def main():

    args = parse_arguments()

    urls = file_to_list(args.inputfile)

    mass_w = MassWappalyzer(urls, **vars(args))

    mass_w.run()

if __name__=="__main__":
    main()
