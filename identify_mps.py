import datetime
import pandas as pd
import xml.etree.ElementTree as ET
import os
import re

# Create output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# List of MPs and their parties
list_of_mps = """
# Labour
Burgeon
Corbyn
Lewis
Abbot
Sultana
Kim Johnson
Nadia Whittome

# Lib Dems
Lisa Smart

# SNP
Pete Wishart (Perth and Kinross-shire)

# Greens
Ellie Chowns

# Conservatives
Julian Lewis

# Indies
Shockat
Imran Hussain
"""