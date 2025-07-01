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
        
        # Split name into first and last
        name_parts = mp_data['full_name'].split()
        if len(name_parts) >= 2:
            # Remove titles and get actual names
            filtered_parts = [part for part in name_parts if not part.lower() in ['mr', 'mrs', 'ms', 'dr', 'sir', 'dame', 'lord', 'lady', 'hon', 'rt']]
            if len(filtered_parts) >= 2:
                mp_data['first_name'] = filtered_parts[0]
                mp_data['last_name'] = ' '.join(filtered_parts[1:])
            else:
                mp_data['first_name'] = name_parts[0] if name_parts else ''
                mp_data['last_name'] = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        else:
            mp_data['first_name'] = mp_data['full_name']
            mp_data['last_name'] = ''
        
        # Initialize phone numbers
        mp_data['parliamentary_phone'] = ''
        mp_data['constituency_phone'] = ''
        
        # Get addresses and extract phone numbers
        addresses = member.find('Addresses')
        if addresses is not None:
            for address in addresses.findall('Address'):
                address_type = address.find('Type')
                if address_type is not None:
                    type_text = address_type.text
                    phone_elem = address.find('Phone')
                    if phone_elem is not None and phone_elem.text:
                        phone_number = phone_elem.text.strip()
                        if phone_number:  # Only add if not empty
                            if type_text == 'Parliamentary office':
                                mp_data['parliamentary_phone'] = phone_number
                            elif type_text == 'Constituency office':
                                mp_data['constituency_phone'] = phone_number
        
        contact_data.append(mp_data)
        
except Exception as e:
    print(f"Error parsing XML: {e}")

print(f"Extracted {len(contact_data)} MP contact records from XML")

# Convert to DataFrame
contact_df = pd.DataFrame(contact_data)

# Load email/party data
print("Loading email and party data...")
try:
    email_df = pd.read_csv('data/mp_email_party_constituency.csv')
    print(f"Loaded {len(email_df)} email records from CSV")
except Exception as e:
    print(f"Error loading email CSV: {e}")
    email_df = pd.DataFrame()

# Load government positions data
print("Loading government positions data...")
try:
    # Load the CSV files
    person_df = pd.read_csv('data/government-positions/person.csv')
    post_df = pd.read_csv('data/government-positions/post.csv')
    appointment_df = pd.read_csv('data/government-positions/appointment.csv')
    
    # Join to get current government positions
    # Filter for current appointments (where end_date is null or empty)
    current_appointments = appointment_df[
        (appointment_df['end_date'].isna()) | 
        (appointment_df['end_date'] == '') |
        (appointment_df['end_date'].str.strip() == '')
    ]
    
    # Join with person and post data
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
    
    print(f"Found {len(current_appointments)} current government appointments")
    print(f"Successfully joined {len(gov_positions)} government positions with names")
    
except Exception as e:
    print(f"Error loading government positions: {e}")
    gov_positions = pd.DataFrame()

# Merge contact details with email data
print("Merging contact details with email data...")
if not email_df.empty and not contact_df.empty:
    # Merge on full name
    merged_df = contact_df.merge(
        email_df, 
        left_on='full_name', 
        right_on='Name (Display As)', 
        how='left'
    )
    print(f"Merged {len(merged_df)} records successfully")
else:
    merged_df = contact_df.copy()
    print("Using contact data only (no email data available)")

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
        titles = ['mr', 'mrs', 'ms', 'dr', 'sir', 'dame', 'lord', 'lady', 'hon', 'rt']
        words = name.split()
        words = [w for w in words if w not in titles]
        return ' '.join(words)
    
    # Create normalized names for matching
    merged_df['name_normalized'] = merged_df['full_name'].apply(normalize_name)
    gov_positions['name_normalized'] = gov_positions['name_person'].apply(normalize_name)
    
    # Merge government positions
    position_matches = merged_df.merge(
        gov_positions[['name_normalized', 'name_post']], 
        on='name_normalized', 
        how='left'
    )
    
    # Update government position column
    merged_df['government_position'] = position_matches['name_post'].fillna('')
    
    # Clean up
    merged_df = merged_df.drop('name_normalized', axis=1)
    
    # Count matches
    matches = (merged_df['government_position'] != '').sum()
    print(f"Matched {matches} MPs with government positions")
else:
    print("No government position matching performed")

# Create final contact sheet with required columns
print("Creating final contact sheet...")
final_columns = {
    'first_name': 'First name',
    'last_name': 'Last name', 
    'full_name': 'Full name',
    'Party': 'Party',
    'government_position': 'Government position',
    'parliamentary_phone': 'Parliamentary phone number',
    'constituency_phone': 'Constituency phone number',
    'Email': 'Email address'
}

# Create the final DataFrame with only the columns we need
contact_sheet = pd.DataFrame()
for old_col, new_col in final_columns.items():
    if old_col in merged_df.columns:
        contact_sheet[new_col] = merged_df[old_col]
    else:
        contact_sheet[new_col] = ''

# Export to CSV
output_file = os.path.join(output_dir, "contact_sheet.csv")
contact_sheet.to_csv(output_file, index=False)

print(f"\n✅ Contact sheet successfully created: {output_file}")
print(f"📊 Total records: {len(contact_sheet)}")

# Print summary statistics
if not contact_sheet.empty:
    email_count = (contact_sheet['Email address'] != '').sum()
    position_count = (contact_sheet['Government position'] != '').sum()
    parl_phone_count = (contact_sheet['Parliamentary phone number'] != '').sum()
    const_phone_count = (contact_sheet['Constituency phone number'] != '').sum()
    
    print(f"📧 Email addresses: {email_count}")
    print(f"🏛️  Government positions: {position_count}")
    print(f"📞 Parliamentary phone numbers: {parl_phone_count}")
    print(f"🏘️  Constituency phone numbers: {const_phone_count}") 