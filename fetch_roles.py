import datetime
import pdpy
import os
import pandas as pd

# Create output directory if it doesn't exist
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# List of current MPs

# Fetch MPs data
print("Fetching role data...")
roles = pdpy.fetch_mps_government_roles(from_date='2024-07-05')

# Make the data readable
print("Processing data...")
readable_roles = pdpy.readable(roles)

# Export to CSV
output_file = os.path.join(output_dir, "roles_data.csv")
print(f"Exporting to {output_file}...")

# Convert to DataFrame if it isn't already and save to CSV
if isinstance(readable_roles, pd.DataFrame):
    readable_roles.to_csv(output_file, index=False)
else:
    # If it's not a DataFrame, convert it
    df = pd.DataFrame(readable_roles)
    df.to_csv(output_file, index=False)

print(f"MPs data successfully exported to {output_file}")
print(f"Number of records: {len(readable_roles)}") 