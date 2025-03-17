import duckdb
import pandas as pd
from pathlib import Path
import glob
from difflib import SequenceMatcher
import re

def clean_title(title):
    """Clean title for matching"""
    return re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())

def similarity_score(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, clean_title(a), clean_title(b)).ratio()

def match_transcripts(db_path='podcast_data.duckdb', 
                     transcript_dir="/Users/srvo/Development/archive/podcast_analysis/episodes"):
    try:
        # Connect to database
        con = duckdb.connect(db_path)
        
        # Get episodes from database
        episodes = con.execute("""
            SELECT 
                title,
                link,
                published,
                transcript
            FROM podcast_episodes
            ORDER BY published DESC
        """).fetchdf()
        
        print(f"Found {len(episodes)} episodes in database")
        
        # Get transcript files
        transcript_files = glob.glob(f"{transcript_dir}/*.txt")
        print(f"Found {len(transcript_files)} transcript files")
        
        # Track matches
        matches = []
        unmatched_files = []
        
        # For each transcript file
        for file_path in transcript_files:
            file_name = Path(file_path).stem
            best_match = None
            best_score = 0
            
            # Find best matching episode
            for _, episode in episodes.iterrows():
                score = similarity_score(file_name, episode['title'])
                if score > best_score and score > 0.6:  # Threshold for matching
                    best_score = score
                    best_match = episode
            
            if best_match is not None:
                matches.append({
                    'file': file_path,
                    'episode_title': best_match['title'],
                    'score': best_score
                })
            else:
                unmatched_files.append(file_path)
        
        print(f"\nFound {len(matches)} potential matches")
        print(f"Found {len(unmatched_files)} unmatched files")
        
        # Show sample matches
        print("\nSample matches:")
        for match in matches[:5]:
            print(f"File: {Path(match['file']).name}")
            print(f"Matched to: {match['episode_title']}")
            print(f"Confidence: {match['score']:.2f}")
            print()
        
        # Show unmatched files
        if unmatched_files:
            print("\nUnmatched files:")
            for file in unmatched_files[:5]:
                print(Path(file).name)
        
        # Ask for confirmation
        should_update = input("\nWould you like to update the database with these matches? (y/n): ")
        if should_update.lower() == 'y':
            updates = 0
            for match in matches:
                try:
                    with open(match['file'], 'r', encoding='utf-8') as f:
                        transcript = f.read()
                        
                    con.execute("""
                        UPDATE podcast_episodes 
                        SET transcript = ?
                        WHERE title = ?
                    """, [transcript, match['episode_title']])
                    updates += 1
                except Exception as e:
                    print(f"Error updating {match['episode_title']}: {str(e)}")
            
            print(f"\nSuccessfully updated {updates} episodes with transcripts")
        
        return matches, unmatched_files
        
    except Exception as e:
        print(f"Error matching transcripts: {str(e)}")
        print("Full error details:", e.__class__.__name__)
        return [], []
    finally:
        con.close()

if __name__ == "__main__":
    matches, unmatched = match_transcripts() 