import json
import pandas as pd
import duckdb
from pathlib import Path
import glob

def load_podcast_data(base_path="/Users/srvo/Development/archive/podcast_analysis"):
    """Load and combine podcast metadata and transcripts"""
    try:
        # Load metadata files
        with open(f"{base_path}/analysis/episodes_metadata.json", 'r') as f:
            episodes_metadata = json.load(f)
        
        with open(f"{base_path}/analysis/summary.json", 'r') as f:
            summary = json.load(f)
            
        # Create DataFrame from metadata
        df_metadata = pd.DataFrame(episodes_metadata)
        
        # Load transcripts
        transcripts = {}
        transcript_files = glob.glob(f"{base_path}/episodes/*.txt")
        
        for file_path in transcript_files:
            episode_id = Path(file_path).stem  # Get filename without extension
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    transcripts[episode_id] = f.read()
            except Exception as e:
                print(f"Error reading transcript {file_path}: {str(e)}")
                transcripts[episode_id] = None
        
        # Add transcripts to DataFrame
        df_metadata['transcript'] = df_metadata['link'].apply(
            lambda x: transcripts.get(x.split('/')[-1], None)
        )
        
        # Convert audio_length to numeric
        df_metadata['audio_length'] = pd.to_numeric(df_metadata['audio_length'], errors='coerce')
        
        # Add duration in minutes
        df_metadata['duration_minutes'] = df_metadata['audio_length'].fillna(0) / (1024 * 1024 * 8 / 60)  # Assuming MP3 bitrate of 128kbps
        
        # Connect to DuckDB
        con = duckdb.connect('podcast_data.duckdb')
        
        # Create table
        con.execute("""
            CREATE TABLE IF NOT EXISTS podcast_episodes (
                title VARCHAR,
                link VARCHAR PRIMARY KEY,
                published TIMESTAMP,
                description VARCHAR,
                audio_url VARCHAR,
                audio_type VARCHAR,
                audio_length BIGINT,
                duration_minutes DOUBLE,
                transcript VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert data
        con.execute("DELETE FROM podcast_episodes")  # Clear existing data
        con.execute("""
            INSERT INTO podcast_episodes (
                title, link, published, description, 
                audio_url, audio_type, audio_length,
                duration_minutes, transcript
            )
            SELECT 
                title, link, 
                STRPTIME(published, '%a, %d %b %Y %H:%M:%S GMT'),
                description, audio_url, audio_type, 
                CAST(audio_length AS BIGINT),
                duration_minutes,
                transcript
            FROM df_metadata
        """)
        
        # Print summary statistics
        print("\nPodcast Database Statistics:")
        stats = con.execute("""
            SELECT 
                COUNT(*) as total_episodes,
                COUNT(DISTINCT DATE_TRUNC('month', published)) as months_covered,
                MIN(published) as earliest_episode,
                MAX(published) as latest_episode,
                AVG(duration_minutes) as avg_duration_min,
                COUNT(CASE WHEN transcript IS NOT NULL THEN 1 END) as episodes_with_transcript
            FROM podcast_episodes
        """).fetchdf()
        print(stats)
        
        # Show sample episodes
        print("\nRecent Episodes Sample:")
        recent = con.execute("""
            SELECT 
                title,
                published,
                duration_minutes,
                LEFT(description, 100) as description_preview
            FROM podcast_episodes
            ORDER BY published DESC
            LIMIT 5
        """).fetchdf()
        print(recent)
        
        # Close connection
        con.close()
        
        return True
        
    except Exception as e:
        print(f"Error processing podcast data: {str(e)}")
        print("Full error details:", e.__class__.__name__)
        return False

def analyze_transcript_lengths(db_path='podcast_data.duckdb'):
    """Analyze word counts of podcast transcripts"""
    try:
        con = duckdb.connect(db_path)
        
        # Create word count analysis
        word_counts = con.execute("""
            WITH word_counts AS (
                SELECT 
                    title,
                    published,
                    duration_minutes,
                    -- Split transcript into words and count
                    REGEXP_SPLIT_TO_ARRAY(
                        LOWER(REGEXP_REPLACE(transcript, '[^a-zA-Z0-9\s]', ' ')), 
                        '\s+'
                    ) as words,
                    LENGTH(transcript) as char_count
                FROM podcast_episodes
                WHERE transcript IS NOT NULL
            )
            SELECT 
                title,
                published,
                duration_minutes,
                ARRAY_LENGTH(words) as word_count,
                char_count,
                ROUND(ARRAY_LENGTH(words) / duration_minutes, 1) as words_per_minute,
                ROUND(char_count / ARRAY_LENGTH(words), 1) as avg_word_length
            FROM word_counts
            ORDER BY published DESC
        """).fetchdf()
        
        print("\nTranscript Analysis:")
        print(f"Total Episodes with Transcripts: {len(word_counts)}")
        
        if not word_counts.empty:
            print("\nWord Count Statistics:")
            print(f"Average Words per Episode: {word_counts['word_count'].mean():.0f}")
            print(f"Average Words per Minute: {word_counts['words_per_minute'].mean():.1f}")
            print(f"Average Word Length: {word_counts['avg_word_length'].mean():.1f} characters")
            
            print("\nTop 5 Longest Episodes by Word Count:")
            print(word_counts.nlargest(5, 'word_count')[['title', 'published', 'word_count', 'duration_minutes']])
            
            print("\nTop 5 Most Dense Episodes (Words per Minute):")
            print(word_counts.nlargest(5, 'words_per_minute')[['title', 'published', 'words_per_minute', 'duration_minutes']])
        
        return word_counts
        
    except Exception as e:
        print(f"Error analyzing transcripts: {str(e)}")
        return pd.DataFrame()
    finally:
        con.close()

if __name__ == "__main__":
    # Load data if needed
    load_podcast_data()
    
    # Analyze transcripts
    word_counts = analyze_transcript_lengths()
    
    # Optionally save to CSV
    # word_counts.to_csv('transcript_analysis.csv', index=False) 