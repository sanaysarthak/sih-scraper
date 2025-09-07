<a id="readme-top"></a>

<br />
  <h1 align="center">SIH 2025 Problem Statement Scraper 🕵️‍♂️📊</h1>

<p align="center">
   Extract complete problem statement details from <strong><em>Smart India Hackathon 2025</em></strong>.
</p>

<p align="center">
  A Python-based web scraper that collects all SIH 2025 problem statements and exports them to CSV, JSON, or Excel.
</p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#overview">Overview</a>
    </li>
    <li>
      <a href="#run-locally">Run Locally</a>
    </li>
    <li>
      <a href="#how-to-use">How to Use</a>
    </li>
    <li>
      <a href="#tools-used">Tools Used</a>
    </li>
  </ol>
</details>



<!--OVERVIEW --> 
<a id="overview"></a>
## 📖 Overview :-

The "**SIH 2025 Problem Statement Scraper**" is a Python utility that scrapes the official [SIH website](https://www.sih.gov.in/sih2025PS) to extract all problem statements in depth.  

Key features include:
- Extracts complete details: **PS ID, Title, Description, Background, Expected Solution, Organization, Department, Category, Theme, Links, Contact Info**.
- Supports **CSV, JSON, and Excel (XLSX)** export formats.
- Deduplicates entries and handles page structure changes with regex-based fallback.
- Lightweight and dependency-minimal.
- Command-line interface for flexible usage.



<!--SETUP -->
<a id="run-locally"></a>
## 💻 Run Locally :-

#### Installation
1. Clone or download this repository to your local machine.
  ```sh
  git clone https://github.com/sanaysarthak/sih-scraper.git
  ```
2. Navigate to the project directory.
  ```sh
   cd sih-scraper
  ```
3. Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```



<!-- HOW TO USE -->
<a id="how-to-use"></a>
## 🕹️ How to Use :-

#### Step 1: Run the Scraper
```sh
python sih2025_scraper.py --out-base sih2025_ps --formats csv json xlsx
```

#### Step 2: Choose Export Formats
- ```--formats csv``` *(Export only CSV)*
- ```--formats json``` *(Export only JSON)*
- ```--formats xlsx``` *(Export only Excel)*
- ```--formats csv json xlsx``` *(Export all)*

#### Step 3: Output
The files will be generated in the current directory as:
- ```sih2025_ps.csv```
- ```sih2025_ps.json```
- ```sih2025_ps.xlsx```



<!--TOOLS-USED -->
<a id="tools-used"></a>
## 🧰 Tools Used :-

This project uses the following tools and libraries:

- [Python3](https://www.python.org/) → *Core language*
- [Requests](https://pypi.org/project/requests/) → *For fetching HTML*
- [BeautifulSoup4](https://pypi.org/project/beautifulsoup4/) → *For parsing HTML*
- [pandas](https://pandas.pydata.org/) → *For handling tabular data and export*
- [openpyxl](https://openpyxl.readthedocs.io/) → *For Excel export*
- [lxml](https://lxml.de/) → *Fast HTML parsing backend*
