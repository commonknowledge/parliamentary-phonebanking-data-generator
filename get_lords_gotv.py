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
    contact_df = pd.read_csv('output/contact_lords.csv')
    print(f"Loaded {len(contact_df)} MPs from contact sheet")
except Exception as e:
    print(f"Error loading contact sheet: {e}")
    exit(1)

# Exclude MPs with empty 'Phone' column
for index, row in contact_df.iterrows():
    if row['Phone'] == '' or pd.isna(row['Phone']):
        contact_df.drop(index, inplace=True)
        print(f"Removed {row['Full name']} because they have no phone number")

# Read known supporters to exclude
exclude_list = []
try:
    with open('data/exclude_lords.txt', 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                exclude_list.append(line)
    print(f"Loaded {len(exclude_list)} don't bothers to exclude")
except Exception as e:
    print(f"Warning: Could not load known exclude file: {e}")

# Read GOTV priority contacts
gotv_list = []
try:
    with open('data/gotv_lords.txt', 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                gotv_list.append(line)
    print(f"Loaded {len(gotv_list)} GOTV priority contacts")
except Exception as e:
    print(f"Warning: Could not load GOTV priority file: {e}")

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
if exclude_list:
    before_supporters_filter = len(contact_df)
    supporters_to_remove = []
    
    # Get all MP names for matching
    mp_names = contact_df['Full name'].tolist()
    
    # Find matches for each known supporter
    for supporter in exclude_list:
        match, score = fuzzy_match_name(supporter, mp_names, threshold=0.8)
        if match:
            supporters_to_remove.append(match)
            print(f"  Fuzzy matched '{supporter}' -> '{match}' (score: {score:.2f})")
    
    # Remove the matched supporters
    contact_df = contact_df[~contact_df['Full name'].isin(supporters_to_remove)]
    supporters_removed = before_supporters_filter - len(contact_df)
    print(f"Removed {supporters_removed} known supporters from Socialist Campaign Group")

# Remove fash parties
exclude_parties = ['Democratic Unionist Party', 'Reform UK', 'Traditional Unionist Voice', 'Ulster Unionist Party', 'Lord Speaker']
before_fash_filter = len(contact_df)
contact_df = contact_df[~contact_df['Party'].isin(exclude_parties)]
fash_removed = before_fash_filter - len(contact_df) 
print(f"Removed {fash_removed} DUP, Reform UK and Traditional Unionist Voice MPs")

print(f"Remaining MPs after filtering: {len(contact_df)}")

# Identify GOTV priority contacts using fuzzy matching
print("Identifying GOTV priority contacts...")
contact_df['is_gotv_priority'] = False

if gotv_list:
    gotv_matches_found = []
    mp_names = contact_df['Full name'].tolist()
    
    for gotv_name in gotv_list:
        match, score = fuzzy_match_name(gotv_name, mp_names, threshold=0.6)  # Lower threshold for more flexible matching
        if match:
            # Mark this contact as GOTV priority
            contact_df.loc[contact_df['Full name'] == match, 'is_gotv_priority'] = True
            gotv_matches_found.append((gotv_name, match, score))
            print(f"  GOTV match: '{gotv_name}' -> '{match}' (score: {score:.2f})")
    
    print(f"Found {len(gotv_matches_found)} GOTV priority contacts in the list")

# Create ranking system
def get_priority_rank(row):
    """
    Returns priority ranking:
    0 = GOTV priority contacts (highest priority)
    1 = Third parties
    2 = Labour backbenchers  
    3 = Liberal Democrat backbenchers
    5 = Government ministers (lowest priority)
    4 = Conservative backbenchers
    6 = DUP, Reform UK and Traditional Unionist Voice (lowest priority)
    """
    party = row['Party']
    has_gov_position = pd.notna(row['Government position']) and str(row['Government position']).strip() != ''
    is_gotv = row.get('is_gotv_priority', False)
    
    # GOTV contacts get absolute highest priority
    if is_gotv:
        return 0
    
    # Government ministers go to bottom regardless of party
    if has_gov_position and not is_gotv:
        return -1
    
    # Third parties get high priority
    # major_parties = ['Crossbench', 'Non-affiliated', 'Bishops', 'Labour', 'Labour (Co-op)', 'Conservative', 'Liberal Democrat', 'Democratic Unionist Party', 'Reform UK', 'Traditional Unionist Voice']

    if party in ['Green Party']:
        return 1

    # Liberal Democrat backbenchers  
    if party in ['Liberal Democrat', 'Crossbench', 'Non-affiliated']:
        return 2
    
    # Labour backbenchers
    if party in ['Labour', 'Labour (Co-op)']:
        return 2
    
    # Conservative backbenchers
    if party in ['Bishops']:
        return 4
    
    if party in ['Conservative']:
        return -1
    
    # Fallback
    return 3

# Apply ranking
print("Applying priority ranking...")
contact_df['priority_rank'] = contact_df.apply(get_priority_rank, axis=1)

# Remove any -1 rankings (Conservative backbenchers)
contact_df = contact_df[contact_df['priority_rank'] != -1]

# Sort by priority rank, then by party, then by last name
contact_df_sorted = contact_df.sort_values([
    'priority_rank', 
    'Last name'
])

# Remove the priority_rank and is_gotv_priority columns from final output
ranked_df = contact_df_sorted.drop(['priority_rank', 'is_gotv_priority'], axis=1)

# Create summary of rankings
print("\n📊 Ranking Summary:")
rank_counts = contact_df_sorted['priority_rank'].value_counts().sort_index()
rank_labels = {
    0: "GOTV priority contacts (highest priority)",
    1: "Third parties",
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
output_file = os.path.join(output_dir, "ranked_contact_lords_gotv.csv")

ranked_df.to_csv(output_file, index=False)

print(f"\n✅ Ranked contact sheet created: {output_file}")
print(f"📊 Total lords in ranked list: {len(ranked_df)}")

# Show sample of top priorities
print(f"\n🎯 Top 10 priority contacts:")
sample_df = ranked_df.head(10)[['Full name', 'Party', 'Government position']].copy()
sample_df['Government position'] = sample_df['Government position'].fillna('(Backbencher)')
print(sample_df.to_string(index=False))

print(f"\n📈 Party breakdown in final list:")
party_counts = ranked_df['Party'].value_counts()
for party, count in party_counts.items():
    print(f"  {party}: {count} lords") 