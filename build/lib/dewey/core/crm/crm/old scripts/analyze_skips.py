import pandas as pd

# Read the skipped contacts file
df = pd.read_csv('/Users/srvo/lc/performance/output/contact_updates_skipped.csv')

# Group by reason and count
print("\nSkipped contacts by reason:")
print(df.groupby('reason').size())

# Show the skipped contacts
print("\nDetails of skipped contacts:")
for _, row in df.iterrows():
    print(f"\nEmail: {row['email']}")
    print(f"Current name: {row['current_name']}")
    print(f"Reason: {row['reason']}") 