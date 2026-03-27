from midiutil import MIDIFile
import random

music_data = {
    'GOOG': {'pitch': 72, 'duration': 2.5, 'velocity': 100, 'sector': 'Technology', 'pc1': 0.469, 'pc2': 0.469},
    'XOM': {'pitch': 49, 'duration': 0.6, 'velocity': 62, 'sector': 'Energy', 'pc1': -0.397, 'pc2': -0.397},
    'AAPL': {'pitch': 69, 'duration': 2.3, 'velocity': 95, 'sector': 'Technology', 'pc1': 0.374, 'pc2': 0.374},
    'AMZN': {'pitch': 49, 'duration': 0.7, 'velocity': 63, 'sector': 'Technology', 'pc1': -0.390, 'pc2': -0.390},
    'GLD': {'pitch': 54, 'duration': 1.1, 'velocity': 71, 'sector': 'Finance', 'pc1': -0.190, 'pc2': -0.190},
    'DUK': {'pitch': 65, 'duration': 1.9, 'velocity': 88, 'sector': 'Utility', 'pc1': 0.206, 'pc2': 0.206},
    'SO': {'pitch': 48, 'duration': 0.5, 'velocity': 60, 'sector': 'Utility', 'pc1': -0.461, 'pc2': -0.461},
    'AEP': {'pitch': 54, 'duration': 1.1, 'velocity': 71, 'sector': 'Utility', 'pc1': -0.199, 'pc2': -0.199}
}

def create_quantum_music(music_data, filename="quantum_pca_music.mid"):
    midi = MIDIFile(1)
    tempo = 120
    
    #setup the track
    midi.addTrackName(0, 0, "Quantum PCA Music")
    midi.addTempo(0, 0, tempo)
    midi.addProgramChange(0, 0, 0, 1)  #use piano 
    
    print("Quantum State Analysis (Continuous Values):")
    high_pc1_stocks = [ticker for ticker, data in music_data.items() if data['pc1'] > 0.3]
    medium_pc1_stocks = [ticker for ticker, data in music_data.items() if -0.2 <= data['pc1'] <= 0.3]
    low_pc1_stocks = [ticker for ticker, data in music_data.items() if data['pc1'] < -0.2]
    
    print(f"High PC1 (>0.3): {high_pc1_stocks}")
    print(f"Medium PC1 (-0.2 to 0.3): {medium_pc1_stocks}")
    print(f"Low PC1 (<-0.2): {low_pc1_stocks}")
    
    # Simple sequential composition to avoid timing conflicts
    time = 0
    
    # Pattern 1: Play stocks in order of PC1 (high to low)
    print("\n🎵 Pattern 1: PC1 Gradient")
    stocks_by_pc1 = sorted(music_data.keys(), key=lambda x: music_data[x]['pc1'], reverse=True)
    
    for ticker in stocks_by_pc1:
        data = music_data[ticker]
        midi.addNote(0, 0, data['pitch'], time, data['duration'], data['velocity'])
        print(f"  {ticker}: pitch={data['pitch']}, time={time}, duration={data['duration']}")
        time += data['duration']  # Simple sequential timing
    
    # Pattern 2: Group by sector
    print("🎵 Pattern 2: Sector Groups")
    time += 2.0  # Add rest between patterns
    
    sectors = {}
    for ticker, data in music_data.items():
        sector = data['sector']
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(ticker)
    
    for sector, stocks in sectors.items():
        print(f"  {sector} sector: {stocks}")
        for ticker in stocks:
            data = music_data[ticker]
            midi.addNote(0, 0, data['pitch'], time, data['duration'] * 0.7, data['velocity'])
            time += data['duration'] * 0.5
    
    # Pattern 3: Final chord with all stocks
    print("🎵 Pattern 3: Quantum Chord")
    time += 2.0
    
    # Play all stocks simultaneously as a chord
    for ticker, data in music_data.items():
        midi.addNote(0, 0, data['pitch'], time, 4.0, data['velocity'])
    
    # Save the file
    try:
        with open(filename, "wb") as output_file:
            midi.writeFile(output_file)
        print(f"\n✅ SUCCESS: MIDI file saved as '{filename}'")
        return filename
    except Exception as e:
        print(f"❌ ERROR saving MIDI file: {e}")
        return None

# Generate the quantum music
print("=== GENERATING QUANTUM PCA MUSIC ===")
output_file = create_quantum_music(music_data)

if output_file:
    print(f"\n🎶 QUANTUM MUSIC GENERATED: {output_file}")
    print("📍 File location: Check your current working directory")
    print("\n🎹 Import this MIDI file into GarageBand!")
    print("   Each stock plays with its unique pitch and rhythm based on PCA values")
else:
    print("\n❌ Failed to generate music file")

# Additional debug: Check current directory
import os
print(f"\n📁 Current directory: {os.getcwd()}")
print("📁 Files in current directory:")
for file in os.listdir('.'):
    if file.endswith('.mid') or file.endswith('.midi'):
        print(f"   🎵 {file}")