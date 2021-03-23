# Mass Wappalyzer

Run [Wappalyzer](https://github.com/aliasio/wappalyzer) asynchronously on a list of URLs and generate a Excel file containing all results.   

The generated Excel file will have 2 sheets.  

First sheet contains one column per technology seen and one row per analyzed website, additionnaly, a `"Urls"` and `"Last_Url"` column will aways be present.   

Second sheet contains one column per analyzed website and one row per seen technology.    

CSV and JSON format are also supported.      

### Install

Install **Python module**  

    python3 -m pip install -U git+https://github.com/tristanlatr/MassWappalyzer.git

### Requirements

- **None** if you use the packaged full-python Wappalyzer implementation: [python-Wappalyzer](https://github.com/chorsley/python-Wappalyzer) (faster)  

- **Wappalyzer CLI** if you want to use the official Javascript Wappalyzer CLI (shows more details and configurable with `--wappalyzerargs`)  

  - [Docker](https://hub.docker.com/r/wappalyzer/cli/), pull image with `docker pull wappalyzer/cli`

  - [NPM](https://www.npmjs.com/package/wappalyzer), install with `npm i -g wappalyzer`  

*MassWappalyzer should detect if Wappalyzer CLI is installed and use appropriate implementation*

### Usage

    python3 -m masswappalyzer -i sample/top-100-most-visited-websites-in-the-US-as-of-2020.txt -o sample/top-100-most-visited-websites-in-the-US-as-of-2020.xlsx

Output: 
```
Mass Wappalyzer 1.0
Loading...: 100%|100/100 [08:26<00:00,  5.06s/it]
All applications seen: 
{'YouTube', 'ApacheTomcat', 'GoogleWebServer', 'Parsely', 'Nodejs', 'Ensighten', ...}
Creating Excel file sample/top-100-most-visited-websites-in-the-US-as-of-2020.xlsx
Done
```

### Excel file

![Excel file](https://raw.githubusercontent.com/tristanlatr/MassWappalyzer/master/sample/top-100-most-visited-websites-in-the-US-as-of-2020.png "Excel file")

### Full help

```
usage: python3 -m masswappalyzer [-h] -i Input file [-o Output file]
                                 [-f Format] [-w Wappalyzer path]
                                 [-c Wappalyzer arguments] [-a Number] [-p]
                                 [-v]

Run Wappalyzer asynchronously on a list of URLs and generate a Excel file
containing all results.

optional arguments:
  -h, --help            show this help message and exit
  -i Input file, --inputfile Input file
                        Input file, the file must contain 1 host URL per line.
                        (default: None)
  -o Output file, --outputfile Output file
                        Output file containning all Wappalyzer informations.
                        (default: MassWappalyzerResults)
  -f Format, --outputformat Format
                        Indicate output format. Choices: 'xlsx', 'csv',
                        'json'. (default: xlsx)
  -w Wappalyzer path, --wappalyzerpath Wappalyzer path
                        Indicate the path to the Wappalyzer CLI executable.
                        Auto detect by default. Use "python-Wappalyzer" if
                        Wappalyzer CLI not found. (default: None)
  -c Wappalyzer arguments, --wappalyzerargs Wappalyzer arguments
                        Indicate the arguments of the Wappalyzer CLI command
                        as string. Not applicable if using "python-
                        Wappalyzer". (default: --pretty --probe --user-
                        agent="Mozilla/5.0")
  -a Number, --asynch_workers Number
                        Number of websites to analyze at the same time
                        (default: 5)
  -p, --python          Use full Python Wappalyzer implementation "python-
                        Wappalyzer" even if Wappalyzer CLI is installed with
                        NPM or docker. (default: False)
  -v, --verbose         Print what Wappalyzer prints (default: False)
```
