# Mass Wappalyzer

Run Wappalyzer asynchronously on a list of URLs and generate a Excel file containing all results.   

The Excel file will have one column per technology seen (accros all your URLs), additionnaly, a "Urls" column will aways be present.  

### Install

Install **Wappalyzer CLI**   
    - [Docker](https://hub.docker.com/r/wappalyzer/cli/) (used by default)  
    - [NPM](https://www.npmjs.com/package/wappalyzer)  

Install **Python module**  

    python3 -m pip install git+https://github.com/tristanlatr/MassWappalyzer.git


### Usage

    python3 -m masswappalyzer -i sample/top-100-most-visited-websites-in-the-US-as-of-2020.txt -o sample/top-100-most-visited-websites-in-the-US-as-of-2020.xlsx -a 20

```
Mass Wappalyzer 1.0
Loading...: 100%|█████████████████| 100/100 [08:26<00:00,  5.06s/it]
All applications seen: 
{'YouTube', 'ApacheTomcat', 'GoogleWebServer', 'Parsely', 'Nodejs', 'Ensighten', ...}
Creating Excel file sample/top-100-most-visited-websites-in-the-US-as-of-2020.xlsx
Done
```

### Excel file

![Excel file](/sample/top-100-most-visited-websites-in-the-US-as-of-2020.png "Excel file")

### Full help

```
usage: masswappalyzer [-h] -i Input file [-o Output Excel file]
                         [-w Wappalyzer path] [-c Wappalyzer arguments]
                         [-a Number] [-v]

Run Wappalyzer asynchronously on a list of URLs and generate a Excel file
containing all results.

optional arguments:
  -h, --help            show this help message and exit
  -i Input file, --inputfile Input file
                        Input file, the file must contain 1 host URL per line.
                        (default: None)
  -o Output Excel file, --outputfile Output Excel file
                        Output excel file containning all Wappalyzer
                        informations (default: WappalyzerResults.xlsx)
  -w Wappalyzer path, --wappalyzerpath Wappalyzer path
                        Indicate the path to the Wappalyzer executable. Use
                        docker by default. (default: docker run --rm
                        wappalyzer/cli)
  -c Wappalyzer arguments, --wappalyzerargs Wappalyzer arguments
                        Indicate the arguments of the Wappalyzer command as
                        string (default: --pretty --probe --user-
                        agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6)
                        AppleWebKit/537.36 (KHTML, like Gecko)
                        Chrome/85.0.4183.83 Safari/537.36")
  -a Number, --asynch_workers Number
                        Number of websites to analyze at the same time
                        (default: 5)
  -v, --verbose         Print what Wappalyzer prints (default: False)
```
