import datetime
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
    tree = ET.parse('data/lords_contact_details.xml')
    root = tree.getroot()
    
    # Find all Member elements
    for member in root.findall('.//Member'):
        lords_data = {}
        
        # Get basic MP info
        lords_data['id_parliament'] = float(member.get('Member_Id', ''))
        
        # Get display name
        display_as = member.find('DisplayAs')
        if display_as is not None:
            lords_data['full_name'] = display_as.text.strip() if display_as.text else ''
        else:
            lords_data['full_name'] = ''
        
        # Split name into first and last
        name_parts = lords_data['full_name'].split()
        if len(name_parts) >= 2:
            # Remove titles and get actual names
            filtered_parts = [part for part in name_parts if not part.lower() in ['mr', 'mrs', 'ms', 'dr', 'sir', 'dame', 'lord', 'lady', 'hon', 'rt']]
            if len(filtered_parts) >= 2:
                lords_data['first_name'] = filtered_parts[0]
                lords_data['last_name'] = ' '.join(filtered_parts[1:])
            else:
                lords_data['first_name'] = name_parts[0] if name_parts else ''
                lords_data['last_name'] = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        else:
            lords_data['first_name'] = lords_data['full_name']
            lords_data['last_name'] = ''

        # Get party
        party_elem = member.find('Party')
        if party_elem is not None:
            lords_data['Party'] = party_elem.text.strip()
        else:
            lords_data['Party'] = ''
        
        # Initialize phone numbers
        lords_data['parliamentary_phone'] = ''
        lords_data['constituency_phone'] = ''
        lords_data['phone_number_1'] = ''
        
        # Get addresses and extract phone numbers
        addresses = member.find('Addresses')
        if addresses is not None:
            for address in addresses.findall('Address'):
                address_type = address.find('Type')
                if address_type is not None:
                    type_text = address_type.text
                    phone_elem = address.find('Phone')
                    email_elem = address.find('Email')
                    if phone_elem is not None and phone_elem.text:
                        phone_number = phone_elem.text.strip()
                        if phone_number:  # Only add if not empty
                            if type_text == 'Parliamentary office':
                                lords_data['parliamentary_phone'] = phone_number
                            elif type_text == 'Constituency office':
                                lords_data['constituency_phone'] = phone_number
                        if email_elem is not None and email_elem.text:
                            email_address = email_elem.text.strip()
                            if type_text == 'Parliamentary office':
                                lords_data['parliamentary_email_address'] = email_address
                            elif type_text == 'Constituency office':
                                lords_data['constituency_email_address'] = email_address

        lords_data['phone_number_1'] = lords_data['parliamentary_phone'] or lords_data['constituency_phone']
        
        contact_data.append(lords_data)
        
except Exception as e:
    print(f"Error parsing XML: {e}")

print(f"Extracted {len(contact_data)} MP contact records from XML")

# Convert to DataFrame
contact_df = pd.DataFrame(contact_data)
contact_df['id_parliament'] = contact_df['id_parliament'].astype(int)

print("contact_df")
print(contact_df[contact_df['id_parliament'] == 4514])

# Load government positions data
print("Loading government positions data...")
try:
    # Load the CSV files
    person_df = pd.read_csv('data/government-positions/person.csv')
    post_df = pd.read_csv('data/government-positions/post.csv')
    appointment_df = pd.read_csv('data/government-positions/appointment.csv')
    
    # Join to get current government positions
    # Filter for appointments starting after July 4th 2024 and with no end date
    current_appointments = appointment_df[
        # pd.to_datetime(appointment_df['start_date']) >= datetime.datetime(2024, 7, 6)
        # empty or null
        (appointment_df['end_date'].isna()) | (appointment_df['end_date'] == '') | (appointment_df['end_date'].str.strip() == '')
        # or end date is before 2025-06-01
        | (pd.to_datetime(appointment_df['end_date']) > datetime.datetime(2025, 6, 1))
    ]
    
    # Join with person and post data
    gov_positions = current_appointments.merge(
        person_df[['id', 'name', 'id_parliament']], 
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

# reform id_parliament to int
gov_positions['id_parliament'] = gov_positions['id_parliament'].astype(int)

merged_df = contact_df

# Add government positions
merged_df['government_position'] = ''

if not gov_positions.empty and not merged_df.empty:
    # Merge government positions
    position_matches = merged_df.merge(
        gov_positions[['name_post', 'id_parliament']], 
        on='id_parliament',
        how='left'
    )
    
    # Update government position column
    merged_df['government_position'] = position_matches['name_post'].fillna('')
    
    # Count matches
    matches = (merged_df['government_position'] != '').sum()
    print(f"Matched {matches} MPs with government positions")
else:
    print("No government position matching performed")

# Create final contact sheet with required columns
print("Creating final contact sheet...")
final_columns = {
    'id_parliament': 'id_parliament',
    'first_name': 'First name',
    'last_name': 'Last name', 
    'full_name': 'Full name',
    'Party': 'Party',
    'government_position': 'Government position',
    'phone_number_1': 'Phone',
    'parliamentary_phone': 'Parliamentary phone number',
    'constituency_phone': 'Constituency phone number',
    'parliamentary_email_address': 'Parliamentary email address',
    'constituency_email_address': 'Constituency email address'
}

# Create the final DataFrame with only the columns we need
contact_sheet = pd.DataFrame()
for old_col, new_col in final_columns.items():
    if old_col in merged_df.columns:
        contact_sheet[new_col] = merged_df[old_col]
    else:
        contact_sheet[new_col] = ''

# Export to CSV
output_file = os.path.join(output_dir, "contact_lords.csv")
contact_sheet.to_csv(output_file, index=False)

print(f"\n✅ Contact sheet successfully created: {output_file}")
print(f"📊 Total records: {len(contact_sheet)}")

# Print summary statistics
if not contact_sheet.empty:
    parl_email_count = (contact_sheet['Parliamentary email address'] != '').sum()
    const_email_count = (contact_sheet['Constituency email address'] != '').sum()
    position_count = (contact_sheet['Government position'] != '').sum()
    parl_phone_count = (contact_sheet['Parliamentary phone number'] != '').sum()
    const_phone_count = (contact_sheet['Constituency phone number'] != '').sum()
    
    print(f"📧 Parliamentary email addresses: {parl_email_count}")
    print(f"📧 Constituency email addresses: {const_email_count}")
    print(f"🏛️  Government positions: {position_count}")
    print(f"📞 Parliamentary phone numbers: {parl_phone_count}")
    print(f"🏘️  Constituency phone numbers: {const_phone_count}") 