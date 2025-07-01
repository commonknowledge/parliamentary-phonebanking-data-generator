import pandas as pd
import xml.etree.ElementTree as ET
import os
import re

# Create output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

print("Starting contact sheet creation...")

# First, parse the MP contact details XML
print("Parsing MP contact details XML...")
contact_data = []

try:
    tree = ET.parse('data/mp_contact_details.xml')
    root = tree.getroot()
    
    # Find all Member elements
    for member in root.findall('.//Member'):
        mp_data = {}
        
        # Get basic MP info
        mp_data['member_id'] = member.get('Member_Id', '')
        
        # Get display name
        display_as = member.find('DisplayAs')
        if display_as is not None:
            mp_data['full_name'] = display_as.text.strip() if display_as.text else ''
        else:
            mp_data['full_name'] = ''
        
        # Extract first and last names from full name
        if mp_data['full_name']:
            name_parts = mp_data['full_name'].split()
            if len(name_parts) >= 2:
                mp_data['first_name'] = name_parts[0]
                mp_data['last_name'] = ' '.join(name_parts[1:])
            else:
                mp_data['first_name'] = mp_data['full_name']
                mp_data['last_name'] = ''
        else:
            mp_data['first_name'] = ''
            mp_data['last_name'] = ''
        
        # Get contact details
        mp_data['parliamentary_phone'] = ''
        mp_data['constituency_phone'] = ''
        
        # Extract phone numbers
        for address in member.findall('.//Address'):
            for phone in address.findall('.//Phone'):
                phone_text = phone.text.strip() if phone.text else ''
                if phone_text:
                    address_type = address.get('Type', '').lower()
                    if 'parliamentary' in address_type or 'parliament' in address_type:
                        mp_data['parliamentary_phone'] = phone_text
                    elif 'constituency' in address_type:
                        mp_data['constituency_phone'] = phone_text
        
        contact_data.append(mp_data)
        
    contact_df = pd.DataFrame(contact_data)
    print(f"Parsed {len(contact_df)} MP contact records")

except Exception as e:
    print(f"Error parsing XML: {e}")
    contact_df = pd.DataFrame()

# Read the email/party/constituency CSV
print("Reading email and party data...")
try:
    email_df = pd.read_csv('data/mp_email_party_constituency.csv')
    print(f"Loaded {len(email_df)} email records")
    print(f"Email CSV columns: {email_df.columns.tolist()}")
except Exception as e:
    print(f"Error reading email CSV: {e}")
    email_df = pd.DataFrame()

# Read government positions data
print("Reading government positions data...")
try:
    # Read the appointment data (contains person_id, post_id, start_date, end_date)
    appointment_df = pd.read_csv('data/government-positions/appointment.csv')
    
    # Read person data (contains person info)
    person_df = pd.read_csv('data/government-positions/person.csv')
    
    # Read post data (contains position titles)
    post_df = pd.read_csv('data/government-positions/post.csv')
    
    print(f"Loaded {len(appointment_df)} appointments, {len(person_df)} people, {len(post_df)} posts")
    print(f"Person CSV columns: {person_df.columns.tolist()}")
    print(f"Post CSV columns: {post_df.columns.tolist()}")
    print(f"Appointment CSV columns: {appointment_df.columns.tolist()}")
    
    # Filter for current appointments (where end_date is null or empty)
    current_appointments = appointment_df[
        appointment_df['end_date'].isna() | 
        (appointment_df['end_date'] == '') |
        appointment_df['end_date'].isnull()
    ]
    
    print(f"Found {len(current_appointments)} current appointments")
    
    # Join appointments with person and post data to get names and position titles
    gov_positions = current_appointments.merge(
        person_df[['id', 'name']], 
        left_on='person_id', 
        right_on='id', 
        how='left'
    ).merge(
        post_df[['id', 'name']], 
        left_on='post_id', 
        right_on='id', 
        how='left',
        suffixes=('_person', '_post')
    )
    
    # Rename columns for clarity
    gov_positions = gov_positions.rename(columns={
        'name_person': 'government_person_name',
        'name_post': 'government_position'
    })
    
    print(f"Created {len(gov_positions)} government position records")
    
except Exception as e:
    print(f"Error reading government positions: {e}")
    gov_positions = pd.DataFrame()

# Now merge all the data
print("Merging all data sources...")

# Start with contact data
merged_df = contact_df.copy()

# Merge with email data based on name matching
if not email_df.empty and not merged_df.empty:
    email_df_clean = email_df.copy()
    email_df_clean['Name (Display As)'] = email_df_clean['Name (Display As)'].astype(str).str.strip()
    merged_df['full_name_clean'] = merged_df['full_name'].astype(str).str.strip()
    
    merged_df = merged_df.merge(
        email_df_clean[['Name (Display As)', 'Email', 'Party', 'Constituency']],
        left_on='full_name_clean',
        right_on='Name (Display As)',
        how='left'
    )
    print(f"After email merge: {len(merged_df)} records, {merged_df['Email'].notna().sum()} with emails")

# Add government positions
merged_df['government_position'] = ''

if not gov_positions.empty and not merged_df.empty:
    # Create a function to match names more flexibly
    def normalize_name(name):
        if pd.isna(name):
            return ''
        # Remove titles, normalize spacing, convert to lowercase
        name = str(name).strip().lower()
        # Remove common titles
        titles = ['mr', 'mrs', 'ms', 'dr', 'sir', 'dame', 'lord', 'lady', 'hon', 'rt hon']
        words = name.split()
        words = [w for w in words if w not in titles]
        return ' '.join(words)
    
    # Create normalized names for matching
    merged_df['name_normalized'] = merged_df['full_name'].apply(normalize_name)
    gov_positions['name_normalized'] = gov_positions['government_person_name'].apply(normalize_name)
    
    # Remove any rows where government_position is null
    gov_positions_clean = gov_positions[gov_positions['government_position'].notna()].copy()
    
    if not gov_positions_clean.empty:
        # Match on normalized names
        gov_match = merged_df.merge(
            gov_positions_clean[['name_normalized', 'government_position']].drop_duplicates('name_normalized'),
            on='name_normalized',
            how='left'
        )
        
        # Update government positions where matches found
        if 'government_position_y' in gov_match.columns:
            merged_df['government_position'] = gov_match['government_position_y'].fillna('')
        elif 'government_position' in gov_match.columns:
            merged_df['government_position'] = gov_match['government_position'].fillna('')
        
        matches = merged_df['government_position'].ne('').sum()
        print(f"Matched {matches} MPs with government positions")
    else:
        print("No valid government positions found for matching")
else:
    print("No government position matching performed")

# Create the final contact sheet with requested columns
final_columns = [
    'first_name',
    'last_name', 
    'full_name',
    'Party',
    'government_position',
    'parliamentary_phone',
    'constituency_phone',
    'Email'
]

# Rename columns to match requested names
column_mapping = {
    'first_name': 'First name',
    'last_name': 'Last name',
    'full_name': 'Full name',
    'Party': 'Party',
    'government_position': 'Government position',
    'parliamentary_phone': 'Parliamentary phone number',
    'constituency_phone': 'Constituency phone number',
    'Email': 'Email address'
}

# Create final dataframe with only the requested columns
contact_sheet = merged_df[final_columns].copy()
contact_sheet = contact_sheet.rename(columns=column_mapping)

# Fill empty values with empty strings for cleaner output
contact_sheet = contact_sheet.fillna('')

# Export to CSV
output_file = os.path.join(output_dir, "contact_sheet.csv")
contact_sheet.to_csv(output_file, index=False)

print(f"\nContact sheet created successfully!")
print(f"Output file: {output_file}")
print(f"Total records: {len(contact_sheet)}")
print(f"Records with emails: {(contact_sheet['Email address'] != '').sum()}")
print(f"Records with parliamentary phones: {(contact_sheet['Parliamentary phone number'] != '').sum()}")
print(f"Records with constituency phones: {(contact_sheet['Constituency phone number'] != '').sum()}")
print(f"Records with government positions: {(contact_sheet['Government position'] != '').sum()}")

# Show sample of the data
print(f"\nSample records:")
print(contact_sheet.head(10).to_string(index=False)) 