import errno
from datetime import date
import pandas as pd
import re
import numpy as np
import glob
import os
import sys
import pymysql
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Date
from sqlalchemy.sql import bindparam


class ValidDomain:
    def __init__(self, domain):
        self.domain = domain
        self.valid = False

    def is_valid(self):
        """
        - checks for valid domain name using regex
        :return: boolean
        """
        pattern = r"(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)"
        match = re.match(pattern, self.domain)
        self.valid = match is not None
        if '.local' in self.domain:
            return False
        else:
            return self.valid


class Clean:
    def __init__(self, data):
        """
        - takes pandas dataframe and changes it to the desired format, ready for extracting information
        :param data: pandas dataframe
        """
        self.df = pd.DataFrame(data, columns=['Host', 'Name', 'Plugin Output'])
        self.df['Name'] = self.df['Name'].str.lower()
        self.df['Plugin Output'] = self.df['Plugin Output'].str.lower()

    def get_df(self):
        """
        :return: cleaned dataframe
        """
        return self.df


class Search:
    def __init__(self, df):
        self.df = df
        self.name_dict = {}
        self.aggregated_df = pd.DataFrame()

    def netbios(self):
        """
        - Extract hostnames through netbios search
        :return: dictionary key(hostname) : value(extracted name)
        """
        # sorts for netbios computer names
        netbios_df = self.df[(self.df['Name'].str.contains("netbios")) & (self.df['Plugin Output'].str.contains("computer name"))].copy()

        # regex to find computer names
        regex = r"[A-Za-z0-9]+-[A-Za-z0-9]+=(computername)|[A-Za-z0-9]+=(computername)|[A-Za-z0-9]+-=(computername)"

        # extract computer names using the regex
        def extract_computer_name(x):
            no_space_x = x.replace(" ", "")
            match = re.search(regex, no_space_x)
            if match:
                return match.group().replace("=computername", '')
            else:
                return f"No match found in: {x}"  # return the problematic string

        computer_names = netbios_df['Plugin Output'].apply(extract_computer_name)

        # create a list of tuples from the extracted computer names and the host names
        self.name_dict.update(dict(zip(netbios_df['Host'], computer_names)))

        # add a new column called "Extracted Hostnames" and add all of the computer names into the correct row
        self.aggregated_df = netbios_df[['Host', 'Name']]  # only need host and name column
        self.aggregated_df['Extracted_Hostname'] = ''  # add a new column called extracted hostname

        for key in self.name_dict:  # loop into the dictionary to put extracted hostnames into correct row
            self.aggregated_df.loc[self.aggregated_df.Host == key, 'Extracted_Hostname'] = self.name_dict[key]

        return self.name_dict

    def dns(self):
        """
        - Extract hostnames through additional DNS hostname search
        :return: dictionary key(hostname) : value(extracted name)
        """
        temporary_dict = {}  # make new dictionary for dns

        # find dns hostname rows
        dns_df = self.df[self.df['Name'] == "additional dns hostnames"][['Host', 'Name', 'Plugin Output']]

        # remove spaces from plugin output, remove first line, replace all the dashes (-)with spaces and split into list
        dns_df['Plugin Output'] = dns_df['Plugin Output'].str.replace(" ", "").str.replace(
            "thefollowinghostnamespointtotheremotehost:", "").str.replace("\n-", " ").str.split().apply(
            lambda x: x[0] if x else None)  # if hostname already exists then disregard, if doesn't, then add to dict

        temporary_dict.update(dns_df.set_index('Host').to_dict()['Plugin Output'])  # update the temp dict (only dns)
        self.name_dict.update(dns_df.set_index('Host').to_dict()['Plugin Output'])  # update the name dict (overall)

        dns_df = dns_df[['Host', 'Name']]
        for key in temporary_dict:  # loop into the dictionary to put extracted hostnames into correct row
            dns_df.loc[dns_df.Host == key, 'Extracted_Hostname'] = temporary_dict[key]

        self.aggregated_df = pd.concat([self.aggregated_df, dns_df])  # concatenate the dns table to the aggregate table

        return self.name_dict

    def ssl(self):
        """
        - Extract hostnames through SSL self-signed certificate search
        :return: dictionary key(hostname) : value(extracted name)
        """
        temporary_dict = {}  # make a new dictionary only for ssl

        df2 = self.df[(self.df['Name'].str.contains("ssl self-signed certificate"))].copy()

        # clean data for only necessary rows, if we have already extracted a name from the original IP address then
        # disregard the data
        for key in self.name_dict:
            df2.loc[df2.Host == key, 'Plugin Output'] = np.nan
        ssl_df = df2[df2['Plugin Output'].notna()].copy()

        # remove spaces from plugin output data and split data into list
        ssl_df['Plugin Output'] = ssl_df['Plugin Output'].str.replace(" ", "").str.split("[/:]")

        def process_row(row):
            """
            - Extracts the hostname then checks if it is a valid domain name by using ValidDomain class
            :param row: list - plugin output data
            :return: the processed row
            """
            s = (row['Plugin Output'])[2::]
            for elem in s:
                if "cn=" in elem:
                    name = elem.replace("\n", "").replace("cn=", "")
                    valid_domain = ValidDomain(name)
                    if valid_domain.is_valid() and row["Host"] not in self.name_dict.keys():
                        temporary_dict[row["Host"]] = name
                        self.name_dict[row["Host"]] = name
            return

        ssl_df.apply(process_row, axis=1)

        ssl_df = ssl_df[['Host', 'Name']]
        for key in temporary_dict:
            ssl_df.loc[ssl_df.Host == key, 'Extracted_Hostname'] = temporary_dict[key]

        self.aggregated_df = pd.concat([self.aggregated_df, ssl_df])

        return self.name_dict

    def aggregate_results(self):
        # call all of the search methods in order
        self.netbios()
        self.dns()
        self.ssl()

        self.aggregated_df = self.aggregated_df[self.aggregated_df['Extracted_Hostname'].notna()]  # drop any empty rows

        return self.aggregated_df


def extract(filename):
    """
    Reads a filename into a pandas dataframe and extracts the hostname

    :param filename: name of the file
    :return: extracted dataframe
    """

    data = pd.read_csv(filename)  # read the csv file
    clean = Clean(data)  # call clean function to clean the data, ready to extract
    cleaned_df = clean.get_df()  # desired dataframe to extract names from
    search_data = Search(cleaned_df)  # put the cleaned data into search class
    result_df = search_data.aggregate_results()  # call .aggregate_results() method on search_data

    return result_df


class InvalidFileError(Exception):
    pass

def isreadable(filename):
    """
    This function attempts the read the file and if the file is in the incorrect format / cannot be read then
    it will print out the reason.

    :param filename: name of file to read and check
    :return: null
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            f.read()
    except IOError as x:
        if x.errno == errno.ENOENT:
            raise InvalidFileError(os.path.basename(filename), '- does not exist')
        elif x.errno == errno.EACCES:
            raise InvalidFileError(os.path.basename(filename), '- cannot be read')
        else:
            raise InvalidFileError(os.path.basename(filename), '- some other error')
            

            

def clean_data(input_file_path, output_file_path):
    # this has to be replaced with your mysql database info
    engine = create_engine('mysql+pymysql://username:password@localhost/extractedcomputernames')

    new_dataframes = {}
    isreadable(input_file_path)
    new_dataframes[input_file_path] = extract(input_file_path)
    
    metadata = MetaData()

    # Define the schema for the 'all_extracted_names' table
    all_extracted_names_table = Table(
    'all_extracted_names', metadata,
    Column('Host', String(255), nullable=True),
    Column('Name', String(255), nullable=True),
    Column('Extracted_Hostname', String(255), nullable=True),
    Column('Extraction_Date', Date, nullable=False),
    Column('Filename', String(255), nullable=False))
    
    with engine.connect() as conn:
        
        # Check if the table exists
        table_exists_query = text("SHOW TABLES LIKE 'all_extracted_names';")
        table_exists = conn.execute(table_exists_query).fetchone()

        # Create the table if it doesn't exist
        # Create the table if it doesn't exist
        if not table_exists:
            all_extracted_names_table.create(bind=conn)

        
        for name, df in new_dataframes.items():
            # new_filename = "[Extracted] " + os.path.basename(name)
            df['Extraction_Date'] = date.today()
            df['Filename'] = os.path.basename(name)
            
            df.to_csv(output_file_path)  # output extracted file
            
            # Create a temporary table
            temp_table_name = 'temp_table'
            df.to_sql(temp_table_name, con=conn, if_exists='replace', index=False)
        
            # Insert unique rows into the main table
            insert_unique_rows_query = text(f"""
                INSERT INTO all_extracted_names
                SELECT * FROM {temp_table_name}
                WHERE NOT EXISTS (
                    SELECT * FROM all_extracted_names AS main
                    WHERE main.Host = {temp_table_name}.host
                        AND main.Name = {temp_table_name}.name
                        AND main.Extracted_Hostname = {temp_table_name}.extracted_hostname
                        AND DATE(main.Extraction_Date) = DATE({temp_table_name}.extraction_date)
                        AND main.Filename = {temp_table_name}.filename
                    );""")


            conn.execute(insert_unique_rows_query)
            
            # Drop the temporary table
            drop_table_stmt = text('DROP TABLE temp_table')
            conn.execute(drop_table_stmt)
            
