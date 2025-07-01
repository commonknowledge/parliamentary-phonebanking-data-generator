import pandas as pd
import os

print("Creating ranked contact sheet for anti-proscription campaign...")

# Read the existing contact sheet
try:
    contact_df = pd.read_csv('output/contact_sheet.csv')
    print(f"Loaded {len(contact_df)} MPs from contact sheet")
except Exception as e:
    print(f"Error loading contact sheet: {e}")
    exit(1)

# Filter out MPs we don't want to contact
print("Applying filters...")

# Remove Sinn Féin MPs (they don't take their seats)
original_count = len(contact_df)
contact_df = contact_df[contact_df['Party'] != 'Sinn Féin']
sinn_fein_removed = original_count - len(contact_df)
print(f"Removed {sinn_fein_removed} Sinn Féin MPs")

# Remove Secretaries of State and Prime Minister
# Check for various titles that indicate senior government positions
senior_positions = [
    'Secretary of State',
    'Prime Minister', 
    'Chancellor',
    'Deputy Prime Minister'
]

def is_senior_government_official(position):
    if pd.isna(position) or position == '':
        return False
    position_str = str(position).strip()
    return any(senior_pos in position_str for senior_pos in senior_positions)

before_senior_filter = len(contact_df)
contact_df = contact_df[~contact_df['Government position'].apply(is_senior_government_official)]
senior_removed = before_senior_filter - len(contact_df)
print(f"Removed {senior_removed} senior government officials (Secretaries of State, PM, etc.)")

print(f"Remaining MPs after filtering: {len(contact_df)}")

# Create ranking system
def get_priority_rank(row):
    """
    Returns priority ranking:
    1 = Third parties (highest priority)
    2 = Labour backbenchers  
    3 = Liberal Democrat backbenchers
    4 = Conservative backbenchers
    5 = Government ministers (lowest priority)
    6 = DUP and Reform UK (lowest priority)
    """
    party = row['Party']
    has_gov_position = pd.notna(row['Government position']) and str(row['Government position']).strip() != ''
    
    # Government ministers go to bottom regardless of party
    if has_gov_position:
        return 5
    
    # Third parties get highest priority
    major_parties = ['Labour', 'Labour (Co-op)', 'Conservative', 'Liberal Democrat', 'Democratic Unionist Party', 'Reform UK']

    if party not in major_parties:
        return 1
    
    # Labour backbenchers
    if party in ['Labour', 'Labour (Co-op)']:
        return 2
    
    # Liberal Democrat backbenchers  
    if party == 'Liberal Democrat':
        return 3
    
    # Conservative backbenchers
    if party in ['Conservative']:
        return 4
    
    # DUP and Reform UK go to bottom regardless of party
    if party in ['Democratic Unionist Party', 'Reform UK']:
        return 6
    
    # Fallback
    return 3

# Apply ranking
print("Applying priority ranking...")
contact_df['priority_rank'] = contact_df.apply(get_priority_rank, axis=1)

# Sort by priority rank, then by party, then by last name
contact_df_sorted = contact_df.sort_values([
    'priority_rank', 
    'Party', 
    'Last name'
])

# Remove the priority_rank column from final output
ranked_df = contact_df_sorted.drop('priority_rank', axis=1)

# Create summary of rankings
print("\n📊 Ranking Summary:")
rank_counts = contact_df_sorted['priority_rank'].value_counts().sort_index()
rank_labels = {
    1: "Third parties (highest priority)",
    2: "Labour backbenchers", 
    3: "Liberal Democrat backbenchers",
    4: "Conservative backbenchers",
    5: "Government ministers (lowest priority)",
    6: "DUP and Reform UK (lowest priority)"
}

for rank, count in rank_counts.items():
    print(f"  {rank}. {rank_labels.get(rank, 'Unknown')}: {count} MPs")

# Save ranked contact sheet
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "ranked_contact_sheet.csv")

ranked_df.to_csv(output_file, index=False)

print(f"\n✅ Ranked contact sheet created: {output_file}")
print(f"📊 Total MPs in ranked list: {len(ranked_df)}")

# Show sample of top priorities
print(f"\n🎯 Top 10 priority contacts:")
sample_df = ranked_df.head(10)[['Full name', 'Party', 'Government position']].copy()
sample_df['Government position'] = sample_df['Government position'].fillna('(Backbencher)')
print(sample_df.to_string(index=False))

print(f"\n📈 Party breakdown in final list:")
party_counts = ranked_df['Party'].value_counts()
for party, count in party_counts.items():
    print(f"  {party}: {count} MPs") 