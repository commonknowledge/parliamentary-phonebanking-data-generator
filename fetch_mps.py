import datetime
import pdpy
from pdpy import filter as pdpy_filter
from pdpy import core as pdpy_core
import os
import pandas as pd

# Create output directory if it doesn't exist
output_dir = "output"
filename = "mps_data.csv"
os.makedirs(output_dir, exist_ok=True)

# List of current MPs

# Fetch MPs data
print("Loading data...")
query = """
        PREFIX : <https://id.parliament.uk/schema/>
        PREFIX d: <https://id.parliament.uk/>
        SELECT DISTINCT

            ?person_id
            ?mnis_id
            ?given_name
            ?family_name
            ?full_title

        WHERE {{

            ?person_id :memberMnisId ?mnis_id ;
                :personGivenName ?given_name ;
                :personFamilyName ?family_name ;
                <http://example.com/F31CBD81AD8343898B49DC65743F0BDF> ?display_name ;
                <http://example.com/D79B0BAC513C4A9A87C9D5AFF1FC632F> ?full_title ;
                :personHasGenderIdentity/:genderIdentityHasGender/:genderName ?gender ;
                :memberHasParliamentaryIncumbency/:seatIncumbencyHasHouseSeat/:houseSeatHasHouse ?house .
            OPTIONAL {{ ?person_id :personOtherNames ?other_names . }}
            OPTIONAL {{ ?person_id :personDateOfBirth ?date_of_birth . }}
            OPTIONAL {{ ?person_id :personDateOfDeath ?date_of_death . }}
        }}
"""

query_result = pdpy_core.sparql_select(query)

commons_memberships = pdpy.fetch_commons_memberships()
matching_memberships = pdpy_filter.filter_dates(
    commons_memberships,
    start_col='seat_incumbency_start_date',
    end_col='seat_incumbency_end_date',
    from_date=datetime.date(2025, 6, 1),
    to_date=datetime.date(2025, 6, 1))
query_result = query_result[query_result['person_id'].isin(matching_memberships['person_id'])]

# Make the data readable
print("Processing data...")
df = pdpy.readable(query_result)

# Export to CSV
output_file = os.path.join(output_dir, filename)
print(f"Exporting to {output_file}...")

# Convert to DataFrame if it isn't already and save to CSV
if isinstance(df, pd.DataFrame):
    df.to_csv(output_file, index=False)
else:
    # If it's not a DataFrame, convert it
    df = pd.DataFrame(df)
    df.to_csv(output_file, index=False)

print(f"MPs data successfully exported to {output_file}")
print(f"Number of records: {len(df)}") 