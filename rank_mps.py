import pandas as pd
import os
from difflib import SequenceMatcher

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def fuzzy_match_name(target_name, name_list, threshold=0.8):
    """Find the best fuzzy match for a name in a list"""
    best_match = None
    best_score = 0
    
    for name in name_list:
        score = similarity(target_name, name)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = name
    
    return best_match, best_score

print("Creating ranked contact sheet for anti-proscription campaign...")

# Read the existing contact sheet
try:
    contact_df = pd.read_csv('output/contact_mps.csv')
    print(f"Loaded {len(contact_df)} MPs from contact sheet")
except Exception as e:
    print(f"Error loading contact sheet: {e}")
    exit(1)

# Exclude MPs who don't have phone_number_1
before_phone_filter = len(contact_df)
contact_df = contact_df[contact_df['Phone'] != '']
phone_removed = before_phone_filter - len(contact_df)
print(f"Removed {phone_removed} MPs without a phone number")

# Read known supporters to exclude
known_supporters = []
try:
    with open('data/exclude_mps.txt', 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                known_supporters.append(line)
    print(f"Loaded {len(known_supporters)} known supporters to exclude")
except Exception as e:
    print(f"Warning: Could not load known supporters file: {e}")

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

# Remove known supporters using fuzzy matching
if known_supporters:
    before_supporters_filter = len(contact_df)
    supporters_to_remove = []
    
    # Get all MP names for matching
    mp_names = contact_df['Full name'].tolist()
    
    # Find matches for each known supporter
    for supporter in known_supporters:
        match, score = fuzzy_match_name(supporter, mp_names, threshold=0.8)
        if match:
            supporters_to_remove.append(match)
            print(f"  Fuzzy matched '{supporter}' -> '{match}' (score: {score:.2f})")
    
    # Remove the matched supporters
    contact_df = contact_df[~contact_df['Full name'].isin(supporters_to_remove)]
    supporters_removed = before_supporters_filter - len(contact_df)
    print(f"Removed {supporters_removed} known supporters from Socialist Campaign Group")

# Remove fash parties
exclude_parties = ['Democratic Unionist Party', 'Reform UK', 'Traditional Unionist Voice']
before_fash_filter = len(contact_df)
contact_df = contact_df[~contact_df['Party'].isin(exclude_parties)]
fash_removed = before_fash_filter - len(contact_df) 
print(f"Removed {fash_removed} DUP, Reform UK and Traditional Unionist Voice MPs")

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
    6 = DUP, Reform UK and Traditional Unionist Voice (lowest priority)
    """
    party = row['Party']
    has_gov_position = pd.notna(row['Government position']) and str(row['Government position']).strip() != ''
    
    # Government ministers go to bottom regardless of party
    if has_gov_position:
        return 5
    
    # Third parties get highest priority
    major_parties = ['Labour', 'Labour (Co-op)', 'Conservative', 'Liberal Democrat', 'Democratic Unionist Party', 'Reform UK', 'Traditional Unionist Voice']

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
    
    # DUP, Reform UK and Traditional Unionist Voice go to bottom regardless of party
    if party in exclude_parties:
        return 6
    
    # Fallback
    return 3

# Apply ranking
print("Applying priority ranking...")
contact_df['priority_rank'] = contact_df.apply(get_priority_rank, axis=1)

# Sort by priority rank, then by party, then by last name
contact_df_sorted = contact_df.sort_values([
    'priority_rank', 
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
    6: "DUP, Reform UK and Traditional Unionist Voice (lowest priority)"
}

for rank, count in rank_counts.items():
    print(f"  {rank}. {rank_labels.get(rank, 'Unknown')}: {count} MPs")

# Save ranked contact sheet
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "ranked_contact_mps.csv")

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