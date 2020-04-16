# stocks

A web scraping script who purpose is to quickly provide key stock price data from Yahoo Finance in a simple format.



# Running Script

```
C:\Temp>dofetch -h
usage: fetch.py [-h] [-s] [-b] [-r] [-f FILE]

Retrieve stock prices from Yahoo Finance website

optional arguments:
  -h, --help            show this help message and exit
  -s, --symbols         Output symbols to be processed and exit
  -b, --brief           Run and output brief of data retrieved
  -r, --report          Run and output report of data retrieved
  -f FILE, --file FILE  Input file name for symbols
```

# Installation

Linux instructions are to build Python from source for Ubuntu 18.04 LTS.

## Python

### Linux

**Update Linux**

```bash
sudo apt-get update
sudo apt-get dist-upgrade -y
```



**Add/update Linux packages** required to build Python:

```bash
sudo apt-get install build-essential checkinstall
sudo apt-get install zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev wget
```



**Download current build of Python** (current 3.8.2) to directory /opt

```bash
cd /opt
sudo wget https://www.python.org/ftp/python/3.8.2/Python-3.8.2.tgz
```



**Extract source files**

```bash
sudo tar xzf Python-3.8.2.tgz
cd Ptyhon-3.8.2
```



**Configure build scripts**

```bash
./configure --enable-optimizations
```



**Build Python** using *make*.  

```
sudo make -j 8
```

To speed up the build, use *nproc* to find the number of CPU cores and substitute this value with the *-i* option to set the number of concurrent build jobs

Look in output for 'Python build finished successfully!'



**Install Python** 

```bash
sudo make altinstall
```

## Windows

Download and install Python from [Python Downloads](https://www.python.org/downloads/)





