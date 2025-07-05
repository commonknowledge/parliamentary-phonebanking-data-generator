import pandas as pd
import os
from difflib import SequenceMatcher

# Load division-lords.csv into DataFrame
df_divisions = pd.read_csv('data/division-lords.csv')
# Load phonebanking-lords.csv into DataFrame
df_phonebanking = pd.read_csv('data/phonebanking-lords.csv')
# merge by name on "Member"
merged_df = pd.merge(df_phonebanking, df_divisions, left_on='Full name', right_on='Member', how='left')
# save to csv
merged_df.to_csv('output/lords_merged_report.csv', index=False)