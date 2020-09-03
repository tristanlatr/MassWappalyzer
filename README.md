# Mass Wappalyzer

Run Wappalyzer asynchronously on a list of URLs and generate a excel file containing all results.   

The Excel file will have one column per technology seen (accros all your URLs), additionnaly, a "Urls" column will aways be present.  

### Install

Install **Wappalyzer CLI**   
    - [Docker](https://hub.docker.com/r/wappalyzer/cli/) (used by default)
    - [NPM](https://www.npmjs.com/package/wappalyzer)  

Install **Python module**  

    python3 -m pip install git+https://github.com/tristanlatr/MassWappalyzer.git

### Usage

```
Wappalyzer Wrapper version 0.2
usage: wappalyzer_wrapper.py [-h] -i Input file [-o Output Excel file]
                             [-w Wappalyzer path] [-c Wappalyzer arguments]
                             [-a Number] [-v]

Run Wappalyzer asynchronously on a list of URLs and generate a excel file with
all Wappalyzer informations

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
                        agent="Mozilla/5.0")
  -a Number, --asynch_workers Number
                        Number of websites to analyze at the same time
                        (default: 5)
  -v, --verbose         Print what Wappalyzer prints (default: False)

```
