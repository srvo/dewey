#!/usr/bin/env python3
import argparse
import logging
from video_transcriber import VideoTranscriber

logging.basicConfig(level=logging.INFO)


def main():
    parser = argparse.ArgumentParser(description='Video Transcriber CLI')
    parser.add_argument('audio_file', help='Path to the audio file to transcribe')
    args = parser.parse_args()
    
    transcriber = VideoTranscriber()
    transcription = transcriber.transcribe(args.audio_file)
    if transcription:
        print('Transcription:')
        print(transcription)
    else:
        logging.error('Failed to transcribe audio.')


if __name__ == '__main__':
    main() 