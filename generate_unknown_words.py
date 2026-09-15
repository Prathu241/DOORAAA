import os
import asyncio
import subprocess
import random

WORDS = [
    "hello", "hi", "hey", "computer", "alexa", "siri", "echo", "jarvis", "okay", "google",
    "turn", "on", "off", "the", "lights", "weather", "time", "what", "is", "play",
    "pause", "stop", "music", "volume", "up", "down", "mute", "unmute", "next", "previous",
    "door", "open", "close", "lock", "unlock", "garage", "kitchen", "living", "room", "bedroom",
    "yes", "no", "cancel", "confirm", "start", "stop", "go", "back", "home", "away",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "zero",
    "apple", "banana", "orange", "grape", "water", "coffee", "tea", "milk", "juice", "pizza",
    "dog", "cat", "bird", "fish", "car", "truck", "bike", "bus", "train", "plane",
    "red", "blue", "green", "yellow", "black", "white", "purple", "orange", "brown", "gray",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "today", "tomorrow", "yesterday",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
    "november", "december", "morning", "afternoon", "evening", "night", "day", "week", "month", "year",
    "how", "who", "when", "where", "why", "which", "whose", "whom", "will", "would",
    "can", "could", "should", "shall", "may", "might", "must", "do", "does", "did",
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "a", "an", "the", "and", "but", "or", "so", "because", "although", "though", "while", "if"
]

VOICES = [
    "en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural", "en-US-DavisNeural",
    "en-GB-SoniaNeural", "en-GB-RyanNeural", "en-AU-NatashaNeural", "en-AU-WilliamNeural",
    "en-CA-ClaraNeural", "en-CA-LiamNeural", "en-IN-NeerjaNeural", "en-IN-PrabhatNeural",
    "en-ZA-LeahNeural", "en-ZA-LukeNeural"
]

OUTPUT_DIR = "dataset/unknown_wav"

async def generate_word(word, voice, out_path):
    cmd = ["edge-tts", "--voice", voice, "--text", word, "--write-media", out_path]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.communicate()

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating synthetic unknown negative words in {OUTPUT_DIR}...")
    
    tasks = []
    
    # We will generate about 1400 files (100 words x 14 voices)
    selected_words = random.sample(WORDS, 100)
    
    for voice in VOICES:
        for word in selected_words:
            out_name = f"unknown_{voice}_{word}.mp3"
            out_path = os.path.join(OUTPUT_DIR, out_name)
            tasks.append(generate_word(word, voice, out_path))
            
    print(f"Created {len(tasks)} TTS generation tasks.")
    
    # Run in batches of 20 to avoid overwhelming the system/API
    batch_size = 20
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        await asyncio.gather(*batch)
        print(f"Progress: {min(i+batch_size, len(tasks))}/{len(tasks)}...")
        
    print("Done generating MP3s! Now converting to WAV (16kHz mono)...")
    
    mp3_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".mp3")]
    for i, mp3 in enumerate(mp3_files):
        mp3_path = os.path.join(OUTPUT_DIR, mp3)
        wav_path = os.path.join(OUTPUT_DIR, mp3.replace(".mp3", ".wav"))
        subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "16000", "-ac", "1", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(mp3_path)
        if (i+1) % 100 == 0:
            print(f"Converted {i+1}/{len(mp3_files)}...")
            
    print(f"\nSuccessfully populated {OUTPUT_DIR} with {len(mp3_files)} new unknown words!")

if __name__ == "__main__":
    asyncio.run(main())
