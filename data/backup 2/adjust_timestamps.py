import os
import pandas as pd
from datetime import datetime, timedelta

# Function to adjust timestamp by subtracting 2 hours
def adjust_timestamp(timestamp_str):
    # Parse the timestamp
    try:
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        try:
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            # Return original if unable to parse
            return timestamp_str
    
    # Subtract 2 hours
    adjusted_dt = dt - timedelta(hours=2)
    
    # Return in the same format
    if '.' in timestamp_str:
        return adjusted_dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    else:
        return adjusted_dt.strftime('%Y-%m-%d %H:%M:%S')

# Get all CSV files in the current directory
csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
print(f"Found {len(csv_files)} CSV files to process")

# Process each CSV file
for csv_file in csv_files:
    print(f"Processing {csv_file}...")
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file, sep=',')
        
        # Check if the file has a timestamp column in column A
        if df.columns[0].lower() == 'timestamp':
            # Create a backup of the original file
            backup_file = f"{csv_file}.bak"
            if not os.path.exists(backup_file):
                df.to_csv(backup_file, index=False)
                print(f"Created backup: {backup_file}")
            
            # Adjust the timestamps
            original_count = len(df)
            df.iloc[:, 0] = df.iloc[:, 0].apply(adjust_timestamp)
            
            # Save the modified data
            df.to_csv(csv_file, index=False)
            print(f"Adjusted {original_count} timestamps in {csv_file}")
        else:
            print(f"Skipping {csv_file} - first column is not 'timestamp' (found '{df.columns[0]}')")
    
    except Exception as e:
        print(f"Error processing {csv_file}: {str(e)}")

print("Timestamp adjustment complete!") 