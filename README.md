# Hostname Extraction Tool
The Hostname Extraction Tool is a data transformation and filtering tool built with Django and Pandas. Its main purpose is to extract alternative and valid hostnames through filtering the output of plugins. The tool is specifically designed to work with Nessus data.

The tool allows users to upload a CSV file containing Nessus data, and uses Pandas to extract and filter the data. The extracted and filtered data is then loaded into a MySQL database for further analysis. The tool includes built-in data validation and error checking to ensure the accuracy and reliability of the extracted data.

It is designed to handle large datasets, having been tested on datasets with over 50,000 rows. The tool provides a web interface that allows users to upload CSV files and view the extracted data.

# Getting Started
To use the Hostname Extraction Tool, follow these steps:

Clone the repository: git clone https://github.com/your_username/your_project.git.
Install the required packages: pip install -r requirements.txt.
Run the migrations: python manage.py migrate.
Start the development server: python manage.py runserver.
Open your web browser and go to http://localhost:8000/.
Upload a CSV file containing the Nessus data you want to extract and clean.
Wait for the tool to extract and filter the data, then check the MySQL database to see the results.

Note that in the cleandata.py file, there is a line that specifies the MySQL database that the extracted and filtered data will be loaded into. You will need to change this line to specify your own MySQL database.
